# game/models.py
from django.db import models
from django.utils.safestring import mark_safe
from django.contrib.auth.hashers import make_password
import uuid
import json
import os

from ftn.roles import RolePlayer, assign_by_role_packages, num_of_evil_roles
from ftn.players import generate_player_messages


class GameSession(models.Model):
    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    host_nickname = models.CharField(max_length=50, null=True, blank=True)
    enable_dummy = models.BooleanField(default=False)
    role_groups = models.JSONField()
    is_active = models.BooleanField(default=True)
    is_started = models.BooleanField(default=False)

    def distribute_roles(self):
        player_list = [player.nickname for player in self.players.all()]

        # 더미 플레이어 추가
        if self.enable_dummy and len(player_list) < 5:
            dummies = [f'dummy_{i}' for i in range(5 - len(player_list))]
            player_list += dummies
            
            for i, dummy in enumerate(dummies):
                Player.objects.create(
                    game_session=self,
                    nickname=dummy,
                    pin=make_password(str(i))
                )

        # 역할 데이터 로드
        role_messages_path = os.path.join(os.path.dirname(__file__), '..', 'ftn', 'role_messages.json')
        with open(role_messages_path, 'r', encoding='utf-8') as f:
            role_data = json.load(f)
        
        good_roles = {name for name, info in role_data.items() if info['faction'] == 'good'}
        evil_roles = {name for name, info in role_data.items() if info['faction'] == 'evil'}
        
        # 기본 역할 패키지 구성
        good_packages = [['merlin']]
        evil_packages = []
        
        for pkg in self.role_groups:
            is_good = any(role in good_roles for role in pkg)
            is_evil = any(role in evil_roles for role in pkg)
            
            if is_good and not is_evil:
                good_packages.append(pkg)
            elif is_evil and not is_good:
                evil_packages.append(pkg)
        
        # 역할 부족분 자동 채우기
        required_evil = num_of_evil_roles(len(player_list))
        required_good = len(player_list) - required_evil
        
        if not evil_packages:
            evil_packages.append(['assassin'])
        
        while len(evil_packages) < required_evil:
            evil_packages.append(['minion_of_mordred'])
        
        while len(good_packages) < required_good:
            good_packages.append(['loyal_servant'])

        # 역할 분배 및 저장
        role_packages = good_packages + evil_packages
        role_players = [RolePlayer(p) for p in player_list]
        assigned_players = assign_by_role_packages(role_players, role_packages)
        messages = generate_player_messages(assigned_players)
        
        for player_name, info in messages.items():
            try:
                player = Player.objects.get(game_session=self, nickname=player_name)
                player.roles = info['roles']
                player.role_messages = info['messages']
                player.role_images = info['images']
                player.faction = info['faction']
                player.save()
            except Player.DoesNotExist:
                pass

    def __str__(self):
        return f"Game Session: {self.session_id}"


class Player(models.Model):
    game_session = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name='players')
    nickname = models.CharField(max_length=50)
    pin = models.CharField(max_length=128)
    
    # 역할 정보
    roles = models.JSONField(default=list)
    role_messages = models.JSONField(default=list)
    role_images = models.JSONField(default=list)
    faction = models.CharField(max_length=50, blank=True, default='unknown')

    @property
    def primary_role(self):
        """첫 번째 역할"""
        return self.roles[0] if self.roles else None
    
    @property
    def has_multiple_roles(self):
        """겸직 여부"""
        return len(self.roles) > 1 if self.roles else False

    class Meta:
        unique_together = ('game_session', 'nickname')

    def __str__(self):
        return f"{self.nickname} in {self.game_session.session_id}"