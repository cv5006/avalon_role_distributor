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

        # 플레이어 수에 따른 필요한 악인 수 계산
        total_players = len(player_list)
        required_evil_count = num_of_evil_roles(total_players)
        
        # 역할 데이터 로드 및 진영별 자동 분류
        def load_role_data():
            role_messages_path = os.path.join(os.path.dirname(__file__), '..', 'ftn', 'role_messages.json')
            with open(role_messages_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        role_data = load_role_data()
        good_roles = {name for name, info in role_data.items() if info['faction'] == 'good'}
        evil_roles = {name for name, info in role_data.items() if info['faction'] == 'evil'}
        
        # print(f"🔄 자동 감지된 선인 역할: {good_roles}")
        # print(f"🔄 자동 감지된 악인 역할: {evil_roles}")
        
        # 기본 역할 패키지 구성
        good_packages = [['merlin']]  # 기본 필수 선인 역할 (멀린만)
        evil_packages = []
        
        # self.role_groups에서 선인/악인 역할 분류
        for pkg in self.role_groups:
            is_good_package = any(role in good_roles for role in pkg)
            is_evil_package = any(role in evil_roles for role in pkg)
            
            if is_good_package and not is_evil_package:
                good_packages.append(pkg)
            elif is_evil_package and not is_good_package:
                evil_packages.append(pkg)
        
        # 악인 역할이 하나도 없으면 암살자 추가 (최소한의 기본 처리)
        if len(evil_packages) == 0:
            evil_packages.append(['assassin'])

        # 부족한 악인 역할을 모드레드의 수하로 채움
        current_evil_count = len(evil_packages)
        if current_evil_count < required_evil_count:
            needed_minions = required_evil_count - current_evil_count
            for _ in range(needed_minions):
                evil_packages.append(['minion_of_mordred'])

        # 필요한 선인 수 계산 및 부족한 선인을 충성스러운 신하로 채움
        required_good_count = total_players - required_evil_count
        current_good_count = len(good_packages)
        if current_good_count < required_good_count:
            needed_servants = required_good_count - current_good_count
            for _ in range(needed_servants):
                good_packages.append(['loyal_servant'])

        # 최종 역할 패키지 구성
        role_packages = good_packages + evil_packages
        

        # role distribution
        role_players = [RolePlayer(p) for p in player_list]
        assigned_players = assign_by_role_packages(role_players, role_packages)

        # assign role messages
        messages = generate_player_messages(assigned_players)
        for player_name, info in messages.items():
            print(f"\n{player_name}:")
            print(f"  역할: {info['roles']}")
            print(f"  진영: {info['faction']}")
            
            for i, (message, image) in enumerate(zip(info['messages'], info['images'])):
                print(f"  역할 {i+1}: {message['bold']}")
                print(f"    설명: {message['desc']}")
                print(f"    이미지: {image}")

        # Player 모델에 역할 정보 저장
        for player_name, info in messages.items():
            try:
                player = Player.objects.get(game_session=self, nickname=player_name)
                
                # JSON 필드들에 저장
                player.roles = info['roles']
                player.role_messages = info['messages']
                player.role_images = info['images']
                player.faction = info['faction']
                
                player.save()
                print(f"✅ {player_name}의 역할 정보가 저장되었습니다.")
                
            except Player.DoesNotExist:
                print(f"❌ {player_name} 플레이어를 찾을 수 없습니다.")
            except Exception as e:
                print(f"❌ {player_name} 역할 저장 중 오류: {e}")
    

    def __str__(self):
        return f"Game Session: {self.session_id}"


class Player(models.Model):
    game_session = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name='players')
    nickname = models.CharField(max_length=50, unique=False)
    pin = models.CharField(max_length=128)
    session_key = models.CharField(max_length=40, null=True, blank=True)

    # 여러 역할 지원을 위해 JSON 형태로 저장
    roles = models.JSONField(default=list)  # ['merlin', 'assassin'] 형태
    role_messages = models.JSONField(default=list)  # [{'bold': '...', 'desc': '...'}, ...] 형태
    role_images = models.JSONField(default=list)  # ['./media/merlin.png', './media/assassin.png'] 형태
    faction = models.CharField(max_length=50, blank=True, default='unknown')

    @property
    def safe_role_detail(self):
        """첫 번째 역할의 설명을 안전하게 반환"""
        if self.role_messages and len(self.role_messages) > 0:
            return mark_safe(self.role_messages[0].get('desc', ''))
        return ''
    
    @property
    def safe_role_messages(self):
        """여러 역할의 메시지를 안전하게 반환"""
        safe_messages = []
        for message in self.role_messages:
            safe_messages.append({
                'bold': message.get('bold', ''),
                'desc': mark_safe(message.get('desc', ''))
            })
        return safe_messages
    
    @property
    def role_count(self):
        """플레이어가 가진 역할 개수 반환"""
        return len(self.roles) if self.roles else 0
    
    @property
    def primary_role(self):
        """첫 번째(주) 역할 반환"""
        return self.roles[0] if self.roles else None
    
    @property
    def secondary_role(self):
        """두 번째 역할 반환 (있는 경우)"""
        return self.roles[1] if len(self.roles) > 1 else None
    
    @property
    def has_multiple_roles(self):
        """여러 역할을 가지고 있는지 확인"""
        return len(self.roles) > 1 if self.roles else False
    
    @property
    def roles_display(self):
        """역할들을 표시용 문자열로 반환"""
        if not self.roles:
            return "역할 없음"
        return " + ".join(self.roles)

    class Meta:
        unique_together = ('game_session', 'nickname') # 한 세션 내에서 닉네임 중복 방지

    def __str__(self):
        return f"{self.nickname} in {self.game_session.session_id}"