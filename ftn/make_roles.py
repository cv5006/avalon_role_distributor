import secrets

class Role:
    def __init__(self, name, faction, can_see=None, cannot_see=None):
        self.name = name
        self.faction = faction
        self.can_see = can_see or []          # 이 역할이 볼 수 있는 역할명
        self.cannot_see = cannot_see or []    # 이 역할이 못 보는 역할명

ALL_ROLES = [
    # 선역
    Role(
        name='merlin', faction='good',
        can_see=['assassin', 'morgana', 'mordred', 'minion_of_mordred'],
        cannot_see=['oberon']
    ),
    Role(
        name='percival', faction='good',
        can_see=['merlin', 'morgana'],
    ),
    Role(name='loyal_servant', faction='good'),

    # 악역
    Role(
        name='assassin', faction='evil',
        can_see=['morgana', 'mordred', 'minion_of_mordred'],
        cannot_see=['oberon']
    ),
    Role(
        name='morgana', faction='evil',
        can_see=['assassin', 'mordred', 'minion_of_mordred'],
        cannot_see=['oberon']
    ),
    Role(
        name='mordred', faction='evil',
        can_see=['assassin', 'morgana', 'minion_of_mordred'],
        cannot_see=['oberon']
    ),
    Role(
        name='minion_of_mordred', faction='evil',
        can_see=['assassin', 'morgana', 'mordred'],
        cannot_see=['oberon']
    ),
    Role(
        name='oberon', faction='evil',
        can_see=[],
        cannot_see=['assassin', 'morgana', 'mordred', 'minion_of_mordred']  # 서로 다 못 봄
    ),
]

# 역할명으로 Role 객체를 찾는 헬퍼 함수
def find_role_by_name(role_name):
    for role in ALL_ROLES:
        if role.name == role_name:
            return role
    return None

FORBIDDEN_COMBINATIONS = [
    ('mordred', 'oberon'), # 멀린도 모르고.. 악인들 끼리도 모르고 .. 고립 악인 됨. 
    ('oberon', 'mordred'), # 악인 정보를 몰라, 멀린 추리 어려움. 
    ('morgana','oberon'),  # 모르가나는 퍼시벌을 속여야하는데, 악인 정보를 몰라서 멀린 추리도 힘듬. 속이는 작업 어렵 
]

class Player:
    def __init__(self, name):
        self.name = name
        self.roles = []

    def __repr__(self):
        return f"Player({self.name}, roles={self.roles})"

def assign_roles(players, role_assignments):
    """
    플레이어들에게 역할을 배정합니다.
    
    Args:
        players: Player 객체들의 리스트
        role_assignments: {player_name: [role_name1, role_name2, ...]} 형태의 딕셔너리
    
    Returns:
        역할이 배정된 Player 객체들의 리스트
    """
    for player in players:
        role_names = role_assignments.get(player.name, [])
        for role_name in role_names:
            role_obj = find_role_by_name(role_name)
            if role_obj:
                player.roles.append(role_obj)
            else:
                print(f"경고: '{role_name}' 역할을 찾을 수 없습니다.")
    
    return players

def assign_by_role_packages(players, role_packages):
    if len(players) != len(role_packages):
        raise ValueError("플레이어 수와 역할 조합 수가 다릅니다.")

    # 시큐어 셔플
    secure_random = secrets.SystemRandom()
    secure_random.shuffle(role_packages)

    role_assignments = {
        player.name: package for player, package in zip(players, role_packages)
    }

    return assign_roles(players, role_assignments)


players = [Player('A'), Player('B'), Player('C')]
role_packages = [
    ['loyal_servant'],
    ['merlin'],
    ['morgana', 'assassin'],
]

assigned = assign_by_role_packages(players, role_packages)

for p in assigned:
    print(f"{p.name} ⟶ {[r.name for r in p.roles]}")
