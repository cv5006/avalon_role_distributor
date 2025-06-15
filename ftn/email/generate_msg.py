import random
import os 
import sys
from typing import Dict, List
from copy import deepcopy


current_file_path = os.path.abspath(__file__)
parent_dir = os.path.dirname(current_file_path)
grandparent_dir = os.path.dirname(parent_dir)
sys.path.append(grandparent_dir)

def distributor(player_ids, is_percival, is_morgana):
    player_no = len(player_ids)
    percival_player_no = int(is_percival)
    morgana_player_no = int(is_morgana)

    if player_no < 5 or player_no > 10:
        raise ValueError("player_no must be between 5 and 10")
    
    if player_no <= 6:
        bad_player_no = 2
    elif player_no <= 9:
        bad_player_no = 3
    else:
        bad_player_no = 4

    good_player_no = player_no - bad_player_no
    shuffled = list(player_ids) if hasattr(player_ids, 'tolist') else player_ids[:]
    random.shuffle(shuffled)
    slices = {
        "good": (0, good_player_no),
        "merlin": (0, 1),
        "percival": (1, 1 + percival_player_no),
        "bad": (good_player_no, len(shuffled)+1),
        "assassin": (good_player_no, good_player_no + 1),
        "morgana": (good_player_no + 1, good_player_no + 1 + morgana_player_no),
    }

    # ✅ 이 시점에 set으로 반환
    result = {role: shuffled[start:end] for role, (start, end) in slices.items()}
    return result

messages = {
    "good": {
        "bold": "🕊️ 당신은 선인입니다.",
        "desc": "정의와 진실의 편에 서서,\n함께 협력해 악의 세력을 물리치세요!"
    },
    "merlin": {
        "bold": "🧙‍♂️ 당신은 멀린입니다.",
        "desc": "악인을 알고 있는 지혜로운 예언자입니다.\n"
                "선인들을 인도하되, 정체는 숨기세요. 암살자가 당신을 노리고 있습니다!\n"
                "악인은 {bad_players} 입니다."
    },
    "percival-with-morgana": {
        "bold": "🛡️ 당신은 퍼시발입니다.",
        "desc": "멀린을 지키는 충직한 수호자입니다.\n"
                "하지만 조심하세요! 모르가나가 멀린인 척 속이고 있습니다.\n"
                "멀린은 {merlin_candidates} 중 한 명이며,\n그중 다른 한 명은 악인 모르가나입니다."
    },
    "percival-no-morgana": {
        "bold": "🛡️ 당신은 퍼시발입니다.",
        "desc": "멀린을 지키는 충직한 수호자입니다.\n"
                "멀린은 {merlin} 입니다."
    },
    "bad": {
        "bold": "😈 당신은 악인입니다.",
        "desc": "선인들을 속이고 작전을 펼쳐 아발론을 무너뜨리세요!\n"
                "당신과 함께하는 악인은 {bad_players} 입니다."
    },
    "assassin": {
        "bold": "🗡️ 당신은 암살자입니다.",
        "desc": "게임의 마지막 순간, 멀린을 암살할 기회가 당신에게 주어집니다.\n"
                "정체를 감추고 작전을 펼치며, 선인을 속이세요.\n"
                "당신과 함께하는 악인은 {bad_players} 입니다."
    },
    "morgana": {
        "bold": "🦹‍♀️ 당신은 모르가나입니다.",
        "desc": "멀린인 척 퍼시발을 속이고, 혼란을 유도하세요!\n"
                "교묘하게 작전을 펼쳐 악의 승리를 이끄세요.\n"
                "당신과 함께하는 악인은 {bad_players} 입니다."
    }
}

def generate_player_info(roles, user_info_df):
    user_info = user_info_df.set_index("player_ids").to_dict(orient="index")
    
    id_to_name = user_info_df.set_index('player_ids')['name'].to_dict()
    
    # 역할 확인 
    merlin = set(roles.get("merlin", []))
    percival = set(roles.get("percival", []))
    morgana = set(roles.get("morgana", []))
    bad = set(roles.get("bad", []))
    good = set(roles.get("good", []))
    
    # 이미지 번호 랜덤 부여 위함
    bad_image_no = list(range(1,4))
    good_image_no = list(range(1,6))
    random.shuffle(bad_image_no)
    random.shuffle(good_image_no)

    for player in user_info.keys():

        if player in merlin:
            role = "merlin"
            bad_names = ", ".join(id_to_name[p] for p in sorted(bad))
            bold = messages[role]["bold"]
            desc = messages[role]["desc"].format(bad_players=bad_names)
            img = './media/merlin.png'

        elif player in percival:
            role = "percival"
            if morgana:
                candidates = sorted(merlin | morgana)
                candidate_names = ", ".join(id_to_name[p] for p in candidates)
                desc = messages["percival-with-morgana"]["desc"].format(merlin_candidates=candidate_names)
                bold = messages["percival-with-morgana"]["bold"]
            else:
                merlin_player = next(iter(merlin))
                desc = messages["percival-no-morgana"]["desc"].format(merlin=id_to_name[merlin_player])
                bold = messages["percival-no-morgana"]["bold"]
            img = './media/percival.png'

        elif player in morgana:
            role = "morgana"
            others = sorted(bad - {player})
            other_names = ", ".join(id_to_name[p] for p in others)
            bold = messages[role]["bold"]
            desc = messages[role]["desc"].format(bad_players=other_names)
            img = './media/morgana.png'

        elif player in bad:
            role = "bad"
            others = sorted(bad - {player})
            other_names = ", ".join(id_to_name[p] for p in others)
            bold = messages[role]["bold"]
            desc = messages[role]["desc"].format(bad_players=other_names)
            bad_picked = bad_image_no.pop()
            img = f'./media/bad_guy_{bad_picked}.png'

        elif player in good:
            role = "good"
            bold = messages[role]["bold"]
            desc = messages[role]["desc"]
            good_picked = good_image_no.pop()
            img = f'./media/good_guy_{good_picked}.png'

        user_info[player]["role"] = role
        user_info[player]["bold"] = bold
        user_info[player]["desc"] = desc
        user_info[player]["img"] = img

    return user_info


def distribution_post_process(raw:Dict[str, List]) -> Dict[str, dict]:
    filtered = deepcopy(raw)

    # filtering out special roles
    filtered['good'] = list(set(filtered['good']) - set(filtered['merlin']))
    filtered['good'] = list(set(filtered['good']) - set(filtered['percival']))
    filtered['bad']  = list(set(filtered['bad'])  - set(filtered['assassin']))
    filtered['bad']  = list(set(filtered['bad'])  - set(filtered['morgana']))

    # img selection
    NUM_NORMAL_ROLE_IMGS = {'good': 5, 'bad': 3}
    normal_role_imgs = dict()
    for normal_role in ['good', 'bad']:
        img_list = [f'{normal_role}_guy_{i}' for i in range(1, NUM_NORMAL_ROLE_IMGS[normal_role]+1)]
        random.shuffle(img_list)
        normal_role_imgs[normal_role] = img_list[:len(filtered[normal_role])]

    # restructed dict for player
    res = dict()
    roles_knowing_bad_guys = ['merlin', 'assassin', 'morgana', 'bad']

    for role, assignees in filtered.items():
        if role == 'percival':
            role_msg = messages['percival-with-morgana' if filtered['morgana'] else 'percival-no-morgana']
        else:
            role_msg = messages[role]

        for player in assignees:
            role_intro  = role_msg['bold']
            role_detail = role_msg['desc']
            
            role_img_name = normal_role_imgs[role].pop() if role in ['bad', 'good'] else role
            role_img = f'/media/{role_img_name}.png'

            if role in roles_knowing_bad_guys:
                others = list(set(raw['bad']) - {player})
                random.shuffle(others)
                role_detail = role_detail.format(bad_players='<strong>' + ', '.join(others) + '</strong>')
            elif role == 'percival':
                if filtered['morgana']:
                    candidates = list(filtered['merlin'] + filtered['morgana'])
                    random.shuffle(candidates)
                    role_detail = role_detail.format(merlin_candidates='<strong>' + ', '.join(candidates) + '</strong>')
                else:
                    role_detail = role_detail.format(merlin='<strong>' + filtered['merlin'][0] + '</strong>')

            res[player] = {
                'role':   role,
                'intro':  role_intro,
                'detail': role_detail,
                'image':  role_img
            }

    return res