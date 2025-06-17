import secrets


def num_of_evil_roles(player_count):
    """플레이어 수에 따른 악인 수 반환"""
    if player_count < 5 or player_count > 10:
        raise ValueError("플레이어 수는 5명에서 10명 사이여야 합니다.")
    
    if player_count <= 6:
        return 2
    elif player_count <= 9:
        return 3
    else:
        return 4

# 겸직 금지 조합
FORBIDDEN_COMBINATIONS = [
    ('mordred', 'oberon'),
    ('oberon', 'mordred'), 
    ('morgana', 'oberon'),
    ('oberon', 'morgana'),
]

class RolePlayer:
    def __init__(self, name):
        self.name = name
        self.roles = []

    def __repr__(self):
        return f"RolePlayer({self.name}, roles={self.roles})"

def validate_role_packages(role_packages):
    """역할 패키지 검증"""
    all_roles = []
    for package in role_packages:
        all_roles.extend(package)
    
    # 겸직 금지 조합 확인
    for package in role_packages:
        package_set = set(package)
        for forbidden in FORBIDDEN_COMBINATIONS:
            if forbidden[0] in package_set and forbidden[1] in package_set:
                raise ValueError(f"금지된 겸직: {forbidden[0]} + {forbidden[1]}")
    
    # 필수 역할 확인
    if 'merlin' not in all_roles:
        raise ValueError("멀린은 필수 역할입니다.")
    if 'assassin' not in all_roles:
        raise ValueError("암살자는 필수 역할입니다.")

    return True

def assign_by_role_packages(players, role_packages):
    """역할 패키지로 플레이어에게 역할 배정"""
    if len(players) != len(role_packages):
        raise ValueError("플레이어 수와 역할 조합 수가 다릅니다.")

    validate_role_packages(role_packages)

    # 안전한 셔플
    secure_random = secrets.SystemRandom()
    secure_random.shuffle(role_packages)

    # 역할 배정
    for player, package in zip(players, role_packages):
        player.roles = package

    return players
