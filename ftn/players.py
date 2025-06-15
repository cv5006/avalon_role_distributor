import os
import json

class MessageLoader:
    """메시지 파일 로더 (JSON 형식)"""
    
    def __init__(self, message_file_path="role_messages.json"):
        self.message_file_path = message_file_path
        self.messages = {}
        self.load_messages()
    
    def load_messages(self):
        """role_messages.json 파일에서 메시지 로드"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, self.message_file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            self.messages = json.load(f)
    
    def get_message(self, role_name):
        """역할에 해당하는 메시지 반환"""
        if role_name not in self.messages:
            raise ValueError(f"'{role_name}' 역할에 대한 메시지를 찾을 수 없습니다.")
        return self.messages[role_name]

class ImageManager:
    """이미지 관리 클래스"""
    
    def __init__(self):
        self.good_img_counter = 1
        self.evil_img_counter = 1
    
    def get_role_image(self, role_name):
        """역할에 따른 이미지 경로 반환"""
        if role_name == 'merlin':
            return './media/merlin.png'
        elif role_name == 'percival':
            return './media/percival.png'
        elif role_name == 'assassin':
            return './media/assassin.png'
        elif role_name == 'morgana':
            return './media/morgana.png'
        elif role_name == 'oberon':
            return './media/oberon.png'
        elif role_name == 'mordred':
            return './media/mordred.png'
        elif role_name == 'loyal_servant':
            # 선인 이미지 순환 (1-5)
            img_num = self.good_img_counter
            self.good_img_counter = (self.good_img_counter % 5) + 1
            return f'./media/good_guy_{img_num}.png'
        else:  # minion_of_mordred 등 기타 악인
            # 악인 이미지 순환 (1-3)
            img_num = self.evil_img_counter
            self.evil_img_counter = (self.evil_img_counter % 3) + 1
            return f'./media/bad_guy_{img_num}.png'

def get_visible_players(player, all_players, message_loader):
    """
    플레이어가 볼 수 있는 다른 플레이어들 반환
    
    Args:
        player: 현재 플레이어
        all_players: 모든 플레이어 리스트
        message_loader: 메시지 로더
    
    Returns:
        볼 수 있는 플레이어들의 리스트
    """
    if not player.roles:
        return []
    
    # 첫 번째 역할의 가시성 규칙 사용
    primary_role = player.roles[0]
    
    # JSON에서 가시성 규칙 가져오기
    role_data = message_loader.get_message(primary_role)
    can_see = role_data.get('can_see', [])
    cannot_see = role_data.get('cannot_see', [])
    
    visible_players = []
    
    for other_player in all_players:
        if other_player.name == player.name:
            continue
            
        is_visible = False
        for other_role_name in other_player.roles:
            # can_see 규칙 확인
            if other_role_name in can_see:
                is_visible = True
            
            # cannot_see 규칙 확인 (우선순위가 더 높음)
            if other_role_name in cannot_see:
                is_visible = False
                break
        
        if is_visible and other_player not in visible_players:
            visible_players.append(other_player)
    
    return visible_players

def generate_player_messages(assigned_players):
    """
    배정된 플레이어들의 메시지와 이미지 정보를 생성합니다.
    
    Args:
        assigned_players: roles.py에서 역할이 배정된 RolePlayer 객체들의 리스트
    
    Returns:
        {player_name: {messages: [...], images: [...], roles, faction}} 형태의 딕셔너리
    """
    message_loader = MessageLoader()
    image_manager = ImageManager()
    
    result = {}
    
    for player in assigned_players:
        if not player.roles:
            result[player.name] = {
                "messages": [{"bold": "❓ 역할이 배정되지 않았습니다.", "desc": "역할 배정에 문제가 있습니다."}],
                "images": ["./media/unknown.png"],
                "roles": [],
                "faction": "unknown"
            }
            continue
        
        # 모든 역할에 대해 메시지와 이미지 생성
        messages = []
        images = []
        faction = "unknown"
        
        # 가시성 정보 한 번만 계산 (모든 역할에 동일 적용)
        visible_players = get_visible_players(player, assigned_players, message_loader)
        visible_names = [p.name for p in visible_players]
        final_visible_players = ", ".join(visible_names) if visible_names else "없음"
        
        for role_name in player.roles:
            # JSON 파일에서 메시지 로드
            message_template = message_loader.get_message(role_name)
            
            bold = message_template.get("bold", f"❓ {role_name}")
            desc = message_template.get("desc", f"당신은 {role_name}입니다.")
            
            # final_visible_players 및 target_players 치환
            if "{final_visible_players}" in desc:
                desc = desc.format(final_visible_players=final_visible_players)
            elif "{target_players}" in desc:
                desc = desc.format(target_players=final_visible_players)
            
            messages.append({
                "bold": bold,
                "desc": desc
            })
            
            images.append(image_manager.get_role_image(role_name))
            
            # 첫 번째 역할의 faction 사용
            if faction == "unknown":
                faction = message_template.get("faction", "unknown")
        
        result[player.name] = {
            "messages": messages,
            "images": images,
            "roles": player.roles,
            "faction": faction
        }
    
    return result

# 사용 예시
if __name__ == "__main__":
    from roles import RolePlayer, assign_by_role_packages
    
    print("=== 플레이어 메시지 생성 테스트 ===")
    
    # roles.py로 역할 배정
    players = [RolePlayer('Alice'), RolePlayer('Bob'), RolePlayer('Charlie'), RolePlayer('Kim'), RolePlayer('Lee')]
    role_packages = [
        ['loyal_servant'],
        ['merlin'],
        ['assassin','morgana'],
        ['mordred'],
        ['minion_of_mordred']
    ]
    
    try:
        assigned_players = assign_by_role_packages(players, role_packages)
        
        # 메시지 생성
        messages = generate_player_messages(assigned_players)
        
        for player_name, info in messages.items():
            print(f"\n{player_name}:")
            print(f"  역할: {info['roles']}")
            print(f"  진영: {info['faction']}")
            
            for i, (message, image) in enumerate(zip(info['messages'], info['images'])):
                print(f"  역할 {i+1}: {message['bold']}")
                print(f"    설명: {message['desc']}")
                print(f"    이미지: {image}")
            
    except ValueError as e:
        print(f"에러: {e}")
    except FileNotFoundError as e:
        print(f"메시지 파일을 찾을 수 없습니다: {e}")