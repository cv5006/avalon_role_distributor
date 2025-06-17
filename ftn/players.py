import os
import json
from django.utils.safestring import mark_safe

# 전역 이미지 카운터들
_good_counter = 1
_evil_counter = 1

def load_role_data():
    """역할 데이터 로드"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "role_messages.json")
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_role_image(role_name):
    """역할별 이미지 경로 반환"""
    global _good_counter, _evil_counter
    
    # 특수 역할 이미지
    special_images = {
        'merlin': '/media/merlin.png',
        'percival': '/media/percival.png',
        'assassin': '/media/assassin.png',
        'morgana': '/media/morgana.png',
        'oberon': '/media/oberon.png',
        'mordred': '/media/mordred.png'
    }
    
    if role_name in special_images:
        return special_images[role_name]
    elif role_name == 'loyal_servant':
        img_num = _good_counter
        _good_counter = (_good_counter % 5) + 1
        return f'/media/good_guy_{img_num}.png'
    else:  # minion_of_mordred 등
        img_num = _evil_counter
        _evil_counter = (_evil_counter % 3) + 1
        return f'/media/bad_guy_{img_num}.png'

def get_visible_players(player, all_players, role_data):
    """플레이어가 볼 수 있는 다른 플레이어들 반환"""
    if not player.roles:
        return []
    
    primary_role = player.roles[0]
    can_see = role_data.get(primary_role, {}).get('can_see', [])
    cannot_see = role_data.get(primary_role, {}).get('cannot_see', [])
    
    visible_players = []
    
    for other_player in all_players:
        if other_player.name == player.name:
            continue
        
        # 다른 플레이어의 모든 역할을 확인
        can_see_player = False
        cannot_see_player = False
        
        for other_role in other_player.roles:
            if other_role in can_see:
                can_see_player = True
            if other_role in cannot_see:
                cannot_see_player = True
        
        # 볼 수 있는 역할이 있고, 볼 수 없는 역할이 없을 때만 추가
        if can_see_player and not cannot_see_player:
            visible_players.append(other_player)
    
    return visible_players

def get_invisible_evil_roles_for_player(player, all_players, role_data):
    """특정 플레이어가 볼 수 없는 악인 역할들 반환"""
    if not player.roles:
        return []
    
    primary_role = player.roles[0]
    cannot_see = role_data.get(primary_role, {}).get('cannot_see', [])
    
    # 게임에 실제로 있으면서 이 플레이어가 볼 수 없는 악인들
    all_evil_roles_in_game = set()
    for other_player in all_players:
        for role in other_player.roles:
            if role_data.get(role, {}).get('faction') == 'evil':
                all_evil_roles_in_game.add(role)
    
    # 볼 수 없는 악인들 중 실제 게임에 있는 것들
    invisible_roles = []
    role_name_map = {
        'oberon': '오베론',
        'mordred': '모드레드',
        'morgana': '모르가나', 
        'assassin': '암살자',
        'minion_of_mordred': '모드레드의 수하'
    }
    
    for role in cannot_see:
        if role in all_evil_roles_in_game:
            invisible_roles.append(role_name_map.get(role, role))
    
    return invisible_roles

def get_korean_particle(name):
    """한국어 조사 결정 (은/는)"""
    particle_map = {
        '오베론': '은',
        '모드레드': '는', 
        '모르가나': '는',
        '암살자': '는',
        '모드레드의 수하': '는'
    }
    return particle_map.get(name, '은')

def generate_player_messages(assigned_players):
    """플레이어 메시지 및 이미지 생성"""
    role_data = load_role_data()
    result = {}
    
    for player in assigned_players:
        if not player.roles:
            result[player.name] = {
                "messages": [{"bold": "❓ 역할 없음", "desc": "역할 배정 오류"}],
                "images": ["/media/unknown.png"],
                "roles": [],
                "faction": "unknown"
            }
            continue
        
        messages = []
        images = []
        
        # 가시성 계산
        visible_players = get_visible_players(player, assigned_players, role_data)
        visible_names = [p.name for p in visible_players]
        target_text = ", ".join(visible_names) if visible_names else "없음"
        
        # 현재 플레이어가 볼 수 없는 악인들
        current_faction = role_data.get(player.roles[0], {}).get("faction", "unknown")
        invisible_evil_roles = get_invisible_evil_roles_for_player(player, assigned_players, role_data)
        
        invisible_message = ""
        if invisible_evil_roles:
            if len(invisible_evil_roles) == 1:
                particle = get_korean_particle(invisible_evil_roles[0])
                invisible_message = f"\n({invisible_evil_roles[0]}{particle} 보이지 않습니다.)"
            else:
                # 여러 개일 때는 마지막 이름의 조사 사용
                last_particle = get_korean_particle(invisible_evil_roles[-1])
                invisible_message = f"\n({', '.join(invisible_evil_roles)}{last_particle} 보이지 않습니다.)"
        
        for role_name in player.roles:
            role_info = role_data.get(role_name, {})
            
            bold = role_info.get("bold", f"❓ {role_name}")
            desc = role_info.get("desc", f"당신은 {role_name}입니다.")
            
            # 플레이어 목록 치환
            # if "{final_visible_players}" in desc:
            #     desc = desc.format(final_visible_players=target_text)
            # elif "{target_players}" in desc:
            #     desc = desc.format(target_players=target_text)
            
            # 볼 수 없는 악인 정보 추가 (target_players가 있는 역할에만)
            if "{target_players}" in role_info.get("desc", "") and invisible_message:
                desc += invisible_message
            
            # 최종 desc에 mark_safe 적용
            desc = mark_safe(desc)
            
            # CSS의 white-space: pre-line으로 줄바꿈 처리하므로 \n 그대로 유지
            # desc = desc.replace('\n', '<br>') # 주석 처리
            
            # 능력 보유 여부
            has_ability = len(role_data.get(role_name, {}).get('can_see', [])) > 0
            
            messages.append({"bold": bold, "desc": desc, "visible": target_text,  "ability": has_ability})
            images.append(get_role_image(role_name))
        
        # 첫 번째 역할의 진영 사용
        faction = role_data.get(player.roles[0], {}).get("faction", "unknown")
        
        result[player.name] = {
            "messages": messages,
            "images": images,
            "roles": player.roles,
            "faction": faction
        }
    
    return result