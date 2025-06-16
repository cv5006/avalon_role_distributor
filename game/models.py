# game/models.py
from django.db import models
from django.utils.safestring import mark_safe
from django.contrib.auth.hashers import make_password
import uuid

from ftn.roles import RolePlayer, assign_by_role_packages
from ftn.players import generate_player_messages


class GameSession(models.Model):
    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    host_nickname = models.CharField(max_length=50, null=True, blank=True)
    enable_dummy = models.BooleanField(default=False)

    role_groups  = models.JSONField()
    
    is_active = models.BooleanField(default=True)
    is_started = models.BooleanField(default=False)

    def distribute_roles(self):
        player_list = [player.nickname for player in list(self.players.all())]

        # dummy option
        if self.enable_dummy:
            NUM_TOTAL_PLAYERS = 5
            dummies = [f'dummy_{i}' for i in range(NUM_TOTAL_PLAYERS-len(player_list))]
            if len(player_list) < 5:
                player_list += dummies
            
            for i, dummy in enumerate(dummies):
                Player.objects.create(
                    game_session=self,
                    nickname=dummy,
                    pin=make_password(f'{i}')
                )

        # role distribution
        role_players = [RolePlayer(p) for p in player_list]
        role_packages = [['loyal_servant'], ['merlin']] + self.role_groups
        assigned_players = assign_by_role_packages(role_players, role_packages)

        # assign role messages
        messages = generate_player_messages(assigned_players)
        for player_name, info in messages.items():
            print(f"\n{player_name}:")
            print(f"  역할: {info['roles']}")
            
            for i, (message, image) in enumerate(zip(info['messages'], info['images'])):
                print(f"  역할 {i+1}: {message['bold']}")
                print(f"    설명: {message['desc']}")
                print(f"    이미지: {image}")

        # for assignee, description in distrb.items():
        #     try:
        #         player = Player.objects.get(game_session=self, nickname=assignee)
        #         player.role = description['role']
        #         player.role_intro = description['intro']
        #         player.role_detail = description['detail']
        #         player.role_image = description['image']
        #         player.save()
        #     except Exception as e:
        #         pass
    

    def __str__(self):
        return f"Game Session: {self.session_id}"


class Player(models.Model):
    game_session = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name='players')
    nickname = models.CharField(max_length=50, unique=False)
    pin = models.CharField(max_length=128)
    session_key = models.CharField(max_length=40, null=True, blank=True)

    role = models.CharField(max_length=128, blank=True)
    role_intro  = models.TextField()
    role_detail = models.TextField()
    role_image  = models.TextField()

    @property
    def safe_role_detail(self):
        return mark_safe(self.role_detail)

    class Meta:
        unique_together = ('game_session', 'nickname') # 한 세션 내에서 닉네임 중복 방지

    def __str__(self):
        return f"{self.nickname} in {self.game_session.session_id}"