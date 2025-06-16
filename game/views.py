import json
import hashlib
import os

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from django.http import HttpRequest, HttpResponseRedirect, HttpResponseNotAllowed, JsonResponse
from django.urls import reverse
from urllib.parse import urlencode
from .models import GameSession, Player

# 역할 데이터 로딩 함수
def get_role_data():
    """역할 메시지 데이터를 로드하여 반환"""
    role_messages_path = os.path.join(os.path.dirname(__file__), '..', 'ftn', 'role_messages.json')
    with open(role_messages_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 플레이어 정렬 함수
def sort_players_for_reveal(players, role_data):
    """역할 공개용 플레이어 정렬: 악인 먼저, 그 다음 선인 (각각 우선순위 순)"""
    def get_player_priority(player):
        if not player.roles or not player.faction:
            return (2, 999)  # 알 수 없는 역할은 맨 뒤
        
        # 첫 번째 역할의 우선순위 사용
        primary_role = player.roles[0]
        priority = role_data.get(primary_role, {}).get('priority', 999)
        
        # 진영별 정렬: 0=악인 먼저, 1=선인 나중에
        faction_order = 0 if player.faction == 'evil' else 1
        
        return (faction_order, priority)
    
    return sorted(players, key=get_player_priority)


def home(request:HttpRequest):
    if request.method == 'POST':
        enable_percival = request.POST.get('enable_percival') == 'true'
        enable_dummy = request.POST.get('enable_dummy') == 'true'
        
        role_groups = json.loads(request.POST.get("active_roles", "[]"))
        if enable_percival:
            role_groups.append(['percival'])

        game_session = GameSession.objects.create(
            role_groups=role_groups,
            enable_dummy=enable_dummy,
        )

        game_session.is_active = True
        game_session.save()

        return redirect('join', session_id=game_session.session_id)
    
    return render(request, 'game/home.html')


def join(request:HttpRequest, session_id):
    game_session = get_object_or_404(GameSession, session_id=session_id)

    if not game_session.is_active:
        # join 뷰에서는 POST 데이터에서 닉네임 추출 시도
        player_nickname = request.POST.get('nickname') if request.method == 'POST' else None
        role_data = get_role_data()
        sorted_players = sort_players_for_reveal(game_session.players.all(), role_data)
        return render(request, 'game/ended.html', {
            'message': '🎭 이 아발론 세션은 이미 막을 내렸습니다. 새로운 모험을 시작해보세요!',
            'game_session': game_session,
            'players_in_session': sorted_players,
            'player_nickname': player_nickname,
            'role_data': role_data,
        })
    
    if request.method == 'POST':
        nickname = request.POST.get('nickname')
        pin = request.POST.get('pin')

        if not nickname or not pin:
            return render(request, 'game/join.html', {
                'game_session': game_session,
                'message_text': '닉네임과 비밀번호를 모두 입력해주세요.',
                'message_level': 'error',
            })

        try:
            player = Player.objects.get(game_session=game_session, nickname=nickname)
            if not check_password(pin, player.pin):
                return render(request, 'game/join.html', {
                    'game_session': game_session,
                    'message_text': '비밀번호가 틀렸습니다.',
                    'message_level': 'error',
                })
        except Player.DoesNotExist:
            if game_session.is_started:
                return render(request, 'game/join.html', {
                    'game_session': game_session,
                    'message_text': '🏰 원탁의 기사들이 이미 퀘스트를 시작했어요! 다음 모험을 기다려주세요.',
                    'message_level': 'error',
                })
            
            hashed_pin = make_password(pin)
            Player.objects.create(
                game_session=game_session,
                nickname=nickname,
                pin=hashed_pin
            )

             # 호스트가 비어 있다면 첫 참가자로 지정
            if not game_session.host_nickname:
                game_session.host_nickname = nickname
                game_session.save()

        # redirect 방식 적용 (PRG)
        query = urlencode({'nickname': nickname, 'pin': pin})
        return HttpResponseRedirect(f"{reverse('lobby', args=[session_id])}?{query}")

    return render(request, 'game/join.html', {'game_session': game_session})


def lobby(request:HttpRequest, session_id):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

    game_session = get_object_or_404(GameSession, session_id=session_id)

    # 종료된 세션일 경우 입장 불가
    if not game_session.is_active:
        # lobby 뷰에서는 GET 파라미터에서 닉네임 추출 시도
        player_nickname = request.GET.get('nickname')
        role_data = get_role_data()
        sorted_players = sort_players_for_reveal(game_session.players.all(), role_data)
        return render(request, 'game/ended.html', {
            'message': '🏰 원탁의 기사들이 이미 해산했습니다. 로비 입장이 불가능해요.',
            'game_session': game_session,
            'players_in_session': sorted_players,
            'player_nickname': player_nickname,
            'role_data': role_data,
        })

    nickname = request.GET.get('nickname')
    pin = request.GET.get('pin')

    if not nickname or not pin:
        return redirect('join', session_id=session_id)

    try:
        player = Player.objects.get(game_session=game_session, nickname=nickname)
        if not check_password(pin, player.pin):
            return redirect('join', session_id=session_id)
        
    except Player.DoesNotExist:
        return render(request, 'game/kicked.html', {
            'message': '🚪 이 아발론 세션에서 추방되었거나 초대받지 않은 사용자입니다.',
            'game_session': game_session,
        })

    # 에러 메시지가 있으면 함께 전달
    error_message = request.GET.get('error_message')
    
    return render(request, 'game/lobby.html', {
        'game_session': game_session,
        'player_nickname': nickname,
        'player_pin': pin,
        'players_in_session': game_session.players.all(),
        'session_link': request.build_absolute_uri(reverse('join', args=[session_id])),
        'host_nickname': game_session.host_nickname,
        'error_message': error_message,
    })


def start_game(request:HttpRequest, session_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    game_session = get_object_or_404(GameSession, session_id=session_id)
    nickname = request.POST.get('nickname') # 게임 시작 요청자 (호스트여야 함)
    pin = request.POST.get('pin')

    if nickname != game_session.host_nickname:
        return JsonResponse({'status': 'error', 'message': '게임 시작 권한이 없습니다.'}, status=403)

    try:
        host_player = Player.objects.get(game_session=game_session, nickname=nickname)
        if not check_password(pin, host_player.pin):
            return JsonResponse({'status': 'error', 'message': '인증 실패.'}, status=401)
    except Player.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '호스트 정보를 찾을 수 없습니다.'}, status=404)

    # 플레이어 수 체크 (5명 미만이면 로비로 돌아가면서 메시지 표시)
    # 단, 개발자 옵션(enable_dummy)이 활성화된 경우는 더미 플레이어가 추가되므로 체크하지 않음
    current_players = game_session.players.all()
    if not game_session.enable_dummy and len(current_players) < 5:
        query = urlencode({
            'nickname': nickname, 
            'pin': pin,
            'error_message': '5명 이상이어야 게임을 시작할 수 있습니다!'
        })
        return HttpResponseRedirect(f"{reverse('lobby', args=[session_id])}?{query}")

    # 역할 분배
    game_session.distribute_roles()

    game_session.is_started = True
    game_session.save()

    query = urlencode({'nickname': nickname, 'pin': pin})
    return HttpResponseRedirect(f"{reverse('role', args=[session_id])}?{query}")


def role(request:HttpRequest, session_id):
    game_session = get_object_or_404(GameSession, session_id=session_id)
    
    if not game_session.is_active:
        # role 뷰에서는 GET 파라미터에서 닉네임 추출 시도
        player_nickname = request.GET.get('nickname')
        role_data = get_role_data()
        sorted_players = sort_players_for_reveal(game_session.players.all(), role_data)
        return render(request, 'game/ended.html', {
            'message': '호스트에 의해 게임이 종료되었습니다. 고생하셨습니다!',
            'game_session': game_session,
            'players_in_session': sorted_players,
            'player_nickname': player_nickname,
            'role_data': role_data,
        })

    if not game_session.is_started:
        return redirect('lobby', session_id=session_id)

    player_nickname = request.GET.get('nickname')
    player_pin = request.GET.get('pin')

    if not player_nickname or not player_pin:
        return redirect('join', session_id=session_id)

    try:
        player = Player.objects.get(game_session=game_session, nickname=player_nickname)
        if not check_password(player_pin, player.pin):
            return redirect('join', session_id=session_id)
    except Player.DoesNotExist:
        return render(request, 'game/kicked.html', {
            'message': '🛡️ 원탁에 자리가 없거나 참가 자격이 확인되지 않는 기사입니다.',
            'game_session': game_session,
        })


    # 역할 데이터 로드
    role_data = get_role_data()
    
    # 역할 리스트를 우선순위에 따라 정렬 (JSON의 priority 필드 사용)
    def sort_roles_by_priority(roles, role_data):
        def get_priority(role):
            return role_data.get(role, {}).get('priority', 999)  # 없으면 맨 뒤로
        
        return sorted(roles, key=get_priority)
    
    # 실제 역할 구성 분석
    def analyze_role_composition(players, role_data):
        good_composition = {}
        evil_composition = {}
        
        for p in players:
            if not p.roles or not p.faction:  # 역할이나 진영이 없으면 스킵
                continue
                
            if p.faction == 'good':
                if p.has_multiple_roles:
                    # 다중 역할의 경우 우선순위에 따라 정렬 후 이모지 + 이름 결합
                    sorted_roles = sort_roles_by_priority(p.roles, role_data)
                    role_parts = []
                    for role in sorted_roles:
                        role_info = role_data.get(role, {})
                        emoji = role_info.get('emoji', '')
                        name = role_info.get('name', role)
                        role_parts.append(f"{emoji} {name}")
                    role_key = ' + '.join(role_parts)
                    good_composition[role_key] = good_composition.get(role_key, 0) + 1
                else:
                    role_info = role_data.get(p.primary_role, {})
                    emoji = role_info.get('emoji', '')
                    name = role_info.get('name', p.primary_role or '미정')
                    role_key = f"{emoji} {name}"
                    good_composition[role_key] = good_composition.get(role_key, 0) + 1
            elif p.faction == 'evil':
                if p.has_multiple_roles:
                    # 다중 역할의 경우 우선순위에 따라 정렬 후 이모지 + 이름 결합
                    sorted_roles = sort_roles_by_priority(p.roles, role_data)
                    role_parts = []
                    for role in sorted_roles:
                        role_info = role_data.get(role, {})
                        emoji = role_info.get('emoji', '')
                        name = role_info.get('name', role)
                        role_parts.append(f"{emoji} {name}")
                    role_key = ' + '.join(role_parts)
                    evil_composition[role_key] = evil_composition.get(role_key, 0) + 1
                else:
                    role_info = role_data.get(p.primary_role, {})
                    emoji = role_info.get('emoji', '')
                    name = role_info.get('name', p.primary_role or '미정')
                    role_key = f"{emoji} {name}"
                    evil_composition[role_key] = evil_composition.get(role_key, 0) + 1
        
        # 구성 결과를 우선순위에 따라 정렬
        def sort_composition(composition):
            # 각 역할 조합에 대해 우선순위 점수 계산
            def get_priority_score(role_key):
                # 첫 번째 역할의 우선순위를 기준으로 정렬
                first_role_display = role_key.split(' + ')[0]  # "🧙‍♂️ 멀린" 형태
                
                # 첫 번째 역할의 priority 값 찾기
                for role_id, role_info in role_data.items():
                    if first_role_display == f"{role_info.get('emoji', '')} {role_info.get('name', '')}":
                        return role_info.get('priority', 999)
                return 999  # 매칭되지 않으면 맨 뒤로
            
            # 우선순위에 따라 정렬
            sorted_items = sorted(composition.items(), key=lambda x: get_priority_score(x[0]))
            return dict(sorted_items)
        
        return sort_composition(good_composition), sort_composition(evil_composition)
    
    players_list = game_session.players.all()
    good_comp, evil_comp = analyze_role_composition(players_list, role_data)
    
    # 총 개수 계산
    good_total = sum(good_comp.values()) if good_comp else 0
    evil_total = sum(evil_comp.values()) if evil_comp else 0
    
    # 현재 플레이어의 역할 이모지 계산
    player_role_emoji = ""
    if player.primary_role and player.primary_role in role_data:
        player_role_emoji = role_data[player.primary_role].get('emoji', '')
    
    return render(request, 'game/role.html', {
        'game_session': game_session,
        'player_nickname': player_nickname,
        'player_pin': player_pin,
        'players_in_session': players_list,
        'host_nickname': game_session.host_nickname,
        'player': player,
        'good_composition': good_comp,
        'evil_composition': evil_comp,
        'good_total': good_total,
        'evil_total': evil_total,
        'role_data': role_data,
        'player_role_emoji': player_role_emoji,
    })



def end_game(request:HttpRequest, session_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    game_session = get_object_or_404(GameSession, session_id=session_id)

    if not game_session.is_active:
        return JsonResponse({'status': 'error', 'message': '이미 종료된 게임입니다.'}, status=400)


    nickname = request.POST.get('nickname') 
    pin = request.POST.get('pin')

    if nickname != game_session.host_nickname:
        return JsonResponse({'status': 'error', 'message': '게임 종료 권한이 없습니다.'}, status=403)
    
    try:
        host_player = Player.objects.get(game_session=game_session, nickname=nickname)
        if not check_password(pin, host_player.pin):
            return JsonResponse({'status': 'error', 'message': '인증 실패.'}, status=401)
    except Player.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '호스트 정보를 찾을 수 없습니다.'}, status=404)


    game_session.is_active = False  
    game_session.save()

    # 플레이어 정보를 URL 파라미터로 전달
    query = urlencode({'nickname': nickname, 'pin': pin})
    return HttpResponseRedirect(f"{reverse('ended', args=[session_id])}?{query}")


def ended(request:HttpRequest, session_id):
    game_session = get_object_or_404(GameSession, session_id=session_id)
    
    # URL 파라미터에서 플레이어 정보 가져오기
    player_nickname = request.GET.get('nickname')
    player_pin = request.GET.get('pin')
    
    # 플레이어 정보 검증 (선택적)
    if player_nickname and player_pin:
        try:
            player = Player.objects.get(game_session=game_session, nickname=player_nickname)
            if not check_password(player_pin, player.pin):
                player_nickname = None
        except Player.DoesNotExist:
            player_nickname = None
    
    # 역할 데이터 로드
    role_data = get_role_data()
    
    # 정렬된 플레이어 리스트
    sorted_players = sort_players_for_reveal(game_session.players.all(), role_data)
    
    return render(request, 'game/ended.html', {
            'message': f'호스트에 의해 게임이 종료되었습니다. 고생하셨습니다!',
            'game_session': game_session,
            'players_in_session': sorted_players,
            'player_nickname': player_nickname,
            'player_pin': player_pin,
            'role_data': role_data,
        })


def get_state(request:HttpRequest, session_id):
    game_session = get_object_or_404(GameSession, session_id=session_id)

    if not game_session.is_active:
        return JsonResponse({'players': []})

    player_names = list(game_session.players.all().values_list('nickname', flat=True))
    is_started = game_session.is_started

    # 게임 상태 해시 생성
    data_to_hash = {
        'players': player_names,
        'is_started': is_started
    }
    state_hash = hashlib.md5(json.dumps(data_to_hash).encode()).hexdigest()
    client_hash = request.GET.get('hash')

    if client_hash and client_hash == state_hash and not is_started:
        return JsonResponse({}, status=204)  # 변경 없음

    return JsonResponse({
        'players': player_names,
        'host_nickname': game_session.host_nickname,
        'hash': state_hash,
        'is_active': game_session.is_active,
        'is_started': game_session.is_started,
    })


def kick_player(request:HttpRequest, session_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    game_session = get_object_or_404(GameSession, session_id=session_id)
    target_nickname = request.POST.get('target_nickname')
    kicker_nickname = request.POST.get('nickname')
    kicker_pin = request.POST.get('pin')

    if not game_session.is_active:
        role_data = get_role_data()
        sorted_players = sort_players_for_reveal(game_session.players.all(), role_data)
        return render(request, 'game/ended.html', {
            'message': '🎭 이미 막을 내린 아발론 세션입니다.',
            'game_session': game_session,
            'players_in_session': sorted_players,
            'role_data': role_data,
        })

    if game_session.is_started:
        return JsonResponse({'status': 'error', 'message': '게임이 시작되어 참가자를 추방할 수 없습니다.'}, status=400)

    if target_nickname == kicker_nickname:
        return render(request, 'game/kicked.html', {
            'message': '⚔️ 기사는 자신의 검으로 자신을 베어낼 수 없습니다.',
            'game_session': game_session,
        })

    if kicker_nickname != game_session.host_nickname:
        return render(request, 'game/kicked.html', {
            'message': '👑 오직 원탁의 주인만이 다른 기사들의 운명을 결정할 수 있습니다.',
        })

    try:
        target = Player.objects.get(game_session=game_session, nickname=target_nickname)
        target.delete()
    except Player.DoesNotExist:
        pass

    query = urlencode({'nickname': kicker_nickname, 'pin': kicker_pin})
    return redirect(f"{reverse('lobby', args=[session_id])}?{query}")