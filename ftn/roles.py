import secrets


class Role:
    def __init__(self, name, faction, can_see=None, cannot_see=None):
        self.name = name
        self.faction = faction
        self.can_see = can_see or []          # 이 역할이 볼 수 있는 역할명
        self.cannot_see = cannot_see or []    # 이 역할이 못 보는 역할명


def num_of_evil_roles(player_count):
    """
    플레이어 수에 따라 악인 수를 반환합니다.
    
    Args:player_count: 플레이어 수 (5-10명)
    Returns: 악인 수
    """
    if player_count < 5 or player_count > 10:
        raise ValueError("플레이어 수는 5명에서 10명 사이여야 합니다.")
    
    # 악인 수 결정
    if player_count <= 6:
        evil_count = 2
    elif player_count <= 9:
        evil_count = 3
    else:
        evil_count = 4

    return evil_count

FORBIDDEN_COMBINATIONS = [
    ('mordred', 'oberon'), # 멀린도 모르고.. 악인들 끼리도 모르고 .. 고립 악인 됨. 
    ('oberon', 'mordred'), # 악인 정보를 몰라, 멀린 추리 어려움. 
    ('morgana','oberon'),  # 모르가나는 퍼시벌을 속여야하는데, 악인 정보를 몰라서 멀린 추리도 힘듬. 속이는 작업 어렵 
]

class RolePlayer:
    def __init__(self, name):
        self.name = name
        self.roles = []

    def __repr__(self):
        return f"RolePlayer({self.name}, roles={self.roles})"

def validate_role_packages(role_packages):
    """역할 패키지 조합 유효성 검사"""
    all_roles = []
    for package in role_packages:
        all_roles.extend(package)
    
    # 역할 분류
    good_roles = {'merlin', 'percival', 'loyal_servant'}
    evil_roles = {'assassin', 'morgana', 'mordred', 'oberon', 'minion_of_mordred'}
    special_good = {'merlin', 'percival'}
    general_good = {'loyal_servant'}
    special_evil = {'assassin', 'morgana', 'mordred', 'oberon'}
    general_evil = {'minion_of_mordred'}
    
    # 각 패키지별 조합 검증
    for i, package in enumerate(role_packages):
        package_set = set(package)
        
        # 1. 선악이 같은 역할이 되는 것 방지
        if package_set & good_roles and package_set & evil_roles:
            good_in_package = ', '.join(package_set & good_roles)
            evil_in_package = ', '.join(package_set & evil_roles)
            raise ValueError(f"플레이어 {i+1}: 선인({good_in_package})과 악인({evil_in_package})을 동시에 가질 수 없습니다. "
                           f"한 플레이어는 하나의 진영에만 속해야 합니다.")
        
        # 2. 멀린과 퍼시벌이 같은 역할이 되는 것 방지
        if 'merlin' in package_set and 'percival' in package_set:
            raise ValueError(f"플레이어 {i+1}: 멀린과 퍼시벌을 동시에 가질 수 없습니다. "
                           f"퍼시벌은 멀린을 찾아야 하는 역할이므로 같은 플레이어가 될 수 없습니다.")
        
        # 3. 일반 선인 + 특수 선인 방지
        if package_set & general_good and package_set & special_good:
            special_in_package = ', '.join(package_set & special_good)
            raise ValueError(f"플레이어 {i+1}: 충성스러운 신하와 특수 선인({special_in_package})을 동시에 가질 수 없습니다. "
                           f"충성스러운 신하는 특별한 능력이 없는 일반 선인이므로 특수 역할과 중복될 수 없습니다.")
        
        # 4. 일반 악인 + 특수 악인 방지
        if package_set & general_evil and package_set & special_evil:
            special_in_package = ', '.join(package_set & special_evil)
            raise ValueError(f"플레이어 {i+1}: 모드레드의 부하와 특수 악인({special_in_package})을 동시에 가질 수 없습니다. "
                           f"모드레드의 부하는 특별한 능력이 없는 일반 악인이므로 특수 역할과 중복될 수 없습니다.")
    
    # 기존 금지된 조합 확인
    for forbidden in FORBIDDEN_COMBINATIONS:
        if forbidden[0] in all_roles and forbidden[1] in all_roles:
            reason = ""
            if forbidden == ('mordred', 'oberon') or forbidden == ('oberon', 'mordred'):
                reason = "모르드레드는 멀린이 볼 수 없고, 오베론은 악인들이 볼 수 없어서 서로 고립되어 게임 밸런스가 깨집니다."
            elif forbidden == ('morgana', 'oberon'):
                reason = "모르가나는 퍼시벌을 속여야 하는데, 오베론과 함께하면 악인 정보를 몰라 역할 수행이 어렵습니다."
            
            raise ValueError(f"금지된 조합: {forbidden[0]} + {forbidden[1]}. {reason}")
    
    # 기본 역할 존재 확인
    if 'merlin' not in all_roles:
        raise ValueError("멀린은 필수 역할입니다. 멀린 없이는 선인이 악인을 식별할 수 없어 게임이 성립되지 않습니다.")
    
    if 'assassin' not in all_roles:
        raise ValueError("암살자는 필수 역할입니다. 암살자 없이는 악인이 멀린을 제거할 수 없어 게임이 성립되지 않습니다.")

    return True

def assign_roles(players, role_assignments):
    """
    플레이어들에게 역할을 배정합니다.
    
    Args:
        players: RolePlayer 객체들의 리스트
        role_assignments: {player_name: [role_name1, role_name2, ...]} 형태의 딕셔너리
    
    Returns:
        역할이 배정된 RolePlayer 객체들의 리스트
    """
    for player in players:
        role_names = role_assignments.get(player.name, [])
        player.roles = role_names  # 단순하게 역할 이름만 저장
    
    return players

def assign_by_role_packages(players, role_packages):
    """
    역할 패키지를 사용해 플레이어들에게 역할을 배정합니다.
    
    Args:
        players: RolePlayer 객체들의 리스트
        role_packages: 역할 패키지 리스트 (예: [['merlin'], ['loyal_servant'], ['assassin']])
    
    Returns:
        역할이 배정된 RolePlayer 객체들의 리스트
    """
    if len(players) != len(role_packages):
        raise ValueError("플레이어 수와 역할 조합 수가 다릅니다.")

    # 조합 유효성 검사
    validate_role_packages(role_packages)

    # 시큐어 셔플
    secure_random = secrets.SystemRandom()
    secure_random.shuffle(role_packages)

    role_assignments = {
        player.name: package for player, package in zip(players, role_packages)
    }

    return assign_roles(players, role_assignments)

if __name__ == "__main__":
    players = [RolePlayer('A'), RolePlayer('B'), RolePlayer('C')]
    role_packages = [
        ['loyal_servant'],
        ['merlin'],
        ['morgana', 'assassin'],
    ]

    try:
        assigned = assign_by_role_packages(players, role_packages)
        for p in assigned:
            print(f"{p.name} ⟶ {p.roles}")
    except ValueError as e:
        print(f"에러: {e}")


