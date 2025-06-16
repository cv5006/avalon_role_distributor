import json
import hashlib
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from django.http import HttpResponseRedirect, HttpResponseNotAllowed, JsonResponse
from django.urls import reverse
from urllib.parse import urlencode
from .models import GameSession, Player

# 공통 함수들
def get_role_data():
    """역할 데이터 로드"""
    import os
    role_messages_path = os.path.join(os.path.dirname(__file__), '..', 'ftn', 'role_messages.json')
    with open(role_messages_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def sort_players_for_reveal(players, role_data):
    """역할 공개용 정렬: 악인→선인, 우선순위 순"""
    def get_priority(player):
        if not player.roles or not player.faction:
            return (2, 999)
        primary_role = player.roles[0]
        priority = role_data.get(primary_role, {}).get('priority', 999)
        faction_order = 0 if player.faction == 'evil' else 1
        return (faction_order, priority)
    
    return sorted(players, key=get_priority)

def render_ended_page(request, game_session, message, player_nickname=None):
    """종료 페이지 공통 렌더링"""
    role_data = get_role_data()
    sorted_players = sort_players_for_reveal(game_session.players.all(), role_data)
    return render(request, 'game/ended.html', {
        'message': message,
        'game_session': game_session,
        'players_in_session': sorted_players,
        'player_nickname': player_nickname,
        'role_data': role_data,
    })

def get_player_or_redirect(request, game_session, redirect_to='join'):
    """플레이어 인증 및 검증"""
    nickname = request.GET.get('nickname') or request.POST.get('nickname')
    pin = request.GET.get('pin') or request.POST.get('pin')
    
    if not nickname or not pin:
        return None, redirect(redirect_to, session_id=game_session.session_id)
    
    try:
        player = Player.objects.get(game_session=game_session, nickname=nickname)
        if not check_password(pin, player.pin):
            return None, redirect(redirect_to, session_id=game_session.session_id)
        return player, None
    except Player.DoesNotExist:
        return None, redirect(redirect_to, session_id=game_session.session_id)

# 간소화된 뷰 함수들
def home(request):
    if request.method == 'POST':
        role_groups = json.loads(request.POST.get("active_roles", "[]"))
        if request.POST.get('enable_percival') == 'true':
            role_groups.append(['percival'])

        game_session = GameSession.objects.create(
            role_groups=role_groups,
            enable_dummy=request.POST.get('enable_dummy') == 'true'
        )
        return redirect('join', session_id=game_session.session_id)
    
    return render(request, 'game/home.html')

def join(request, session_id):
    game_session = get_object_or_404(GameSession, session_id=session_id)

    if not game_session.is_active:
        player_nickname = request.POST.get('nickname') if request.method == 'POST' else None
        return render_ended_page(request, game_session, 
            '🎭 이 아발론 세션은 이미 막을 내렸습니다. 새로운 모험을 시작해보세요!', player_nickname)
    
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
                    'message_text': '🏰 원탁의 기사들이 이미 퀘스트를 시작했어요!',
                    'message_level': 'error',
                })
            
            Player.objects.create(
                game_session=game_session,
                nickname=nickname,
                pin=make_password(pin)
            )

            if not game_session.host_nickname:
                game_session.host_nickname = nickname
                game_session.save()

        query = urlencode({'nickname': nickname, 'pin': pin})
        return HttpResponseRedirect(f"{reverse('lobby', args=[session_id])}?{query}")

    return render(request, 'game/join.html', {'game_session': game_session})

def lobby(request, session_id):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

    game_session = get_object_or_404(GameSession, session_id=session_id)

    if not game_session.is_active:
        player_nickname = request.GET.get('nickname')
        return render_ended_page(request, game_session, 
            '🏰 원탁의 기사들이 이미 해산했습니다. 로비 입장이 불가능해요.', player_nickname)

    player, redirect_response = get_player_or_redirect(request, game_session)
    if redirect_response:
        return redirect_response

    return render(request, 'game/lobby.html', {
        'game_session': game_session,
        'player_nickname': player.nickname,
        'player_pin': request.GET.get('pin'),
        'players_in_session': game_session.players.all(),
        'session_link': request.build_absolute_uri(reverse('join', args=[session_id])),
        'host_nickname': game_session.host_nickname,
        'error_message': request.GET.get('error_message'),
    })

def start_game(request, session_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    game_session = get_object_or_404(GameSession, session_id=session_id)
    nickname = request.POST.get('nickname')
    pin = request.POST.get('pin')

    if nickname != game_session.host_nickname:
        return JsonResponse({'status': 'error', 'message': '게임 시작 권한이 없습니다.'}, status=403)

    try:
        host_player = Player.objects.get(game_session=game_session, nickname=nickname)
        if not check_password(pin, host_player.pin):
            return JsonResponse({'status': 'error', 'message': '인증 실패.'}, status=401)
    except Player.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '호스트 정보를 찾을 수 없습니다.'}, status=404)

    if not game_session.enable_dummy and len(game_session.players.all()) < 5:
        query = urlencode({'nickname': nickname, 'pin': pin, 'error_message': '5명 이상이어야 게임을 시작할 수 있습니다!'})
        return HttpResponseRedirect(f"{reverse('lobby', args=[session_id])}?{query}")

    game_session.distribute_roles()
    game_session.is_started = True
    game_session.save()

    query = urlencode({'nickname': nickname, 'pin': pin})
    return HttpResponseRedirect(f"{reverse('role', args=[session_id])}?{query}")

def role(request, session_id):
    game_session = get_object_or_404(GameSession, session_id=session_id)
    
    if not game_session.is_active:
        player_nickname = request.GET.get('nickname')
        return render_ended_page(request, game_session, '호스트에 의해 게임이 종료되었습니다.', player_nickname)

    if not game_session.is_started:
        return redirect('lobby', session_id=session_id)

    player, redirect_response = get_player_or_redirect(request, game_session)
    if redirect_response:
        return redirect_response

    # 간단한 역할 구성 분석
    role_data = get_role_data()
    good_comp, evil_comp = {}, {}
    
    for p in game_session.players.all():
        if not p.roles or not p.faction:
            continue
        
        # 다중 역할 처리
        if len(p.roles) > 1:
            # 여러 역할을 가진 경우 모든 역할을 표시
            role_parts = []
            for role in p.roles:
                emoji = role_data.get(role, {}).get('emoji', '')
                name = role_data.get(role, {}).get('name', role)
                role_parts.append(f"{emoji} {name}")
            role_display = " + ".join(role_parts)
        else:
            # 단일 역할인 경우 기존 방식
            role_display = f"{role_data.get(p.primary_role, {}).get('emoji', '')} {role_data.get(p.primary_role, {}).get('name', '')}"
        
        if p.faction == 'good':
            good_comp[role_display] = good_comp.get(role_display, 0) + 1
        elif p.faction == 'evil':
            evil_comp[role_display] = evil_comp.get(role_display, 0) + 1

    # 우선순위 순으로 정렬
    def sort_by_priority(item):
        role_display, count = item
        # 역할 이름에서 실제 역할 키 찾기
        for role_key, role_info in role_data.items():
            if role_info.get('name', '') in role_display:
                return role_info.get('priority', 999)
        return 999
    
    good_comp = dict(sorted(good_comp.items(), key=sort_by_priority))
    evil_comp = dict(sorted(evil_comp.items(), key=sort_by_priority))

    return render(request, 'game/role.html', {
        'game_session': game_session,
        'player_nickname': player.nickname,
        'player_pin': request.GET.get('pin'),
        'players_in_session': game_session.players.all(),
        'player': player,
        'good_composition': good_comp,
        'evil_composition': evil_comp,
        'good_total': sum(good_comp.values()),
        'evil_total': sum(evil_comp.values()),
        'role_data': role_data,
    })

def end_game(request, session_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    game_session = get_object_or_404(GameSession, session_id=session_id)
    nickname = request.POST.get('nickname')
    pin = request.POST.get('pin')

    if not game_session.is_active:
        return JsonResponse({'status': 'error', 'message': '이미 종료된 게임입니다.'}, status=400)

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

    query = urlencode({'nickname': nickname, 'pin': pin})
    return HttpResponseRedirect(f"{reverse('ended', args=[session_id])}?{query}")

def ended(request, session_id):
    game_session = get_object_or_404(GameSession, session_id=session_id)
    player_nickname = request.GET.get('nickname')
    
    # 간단한 플레이어 검증
    if player_nickname and request.GET.get('pin'):
        try:
            player = Player.objects.get(game_session=game_session, nickname=player_nickname)
            if not check_password(request.GET.get('pin'), player.pin):
                player_nickname = None
        except Player.DoesNotExist:
            player_nickname = None
    
    return render_ended_page(request, game_session, '호스트에 의해 게임이 종료되었습니다. 고생하셨습니다!', player_nickname)

def get_state(request, session_id):
    game_session = get_object_or_404(GameSession, session_id=session_id)

    if not game_session.is_active:
        return JsonResponse({'players': []})

    player_names = list(game_session.players.all().values_list('nickname', flat=True))
    data_to_hash = {'players': player_names, 'is_started': game_session.is_started}
    state_hash = hashlib.md5(json.dumps(data_to_hash).encode()).hexdigest()
    
    if request.GET.get('hash') == state_hash and not game_session.is_started:
        return JsonResponse({}, status=204)

    return JsonResponse({
        'players': player_names,
        'host_nickname': game_session.host_nickname,
        'hash': state_hash,
        'is_active': game_session.is_active,
        'is_started': game_session.is_started,
    })

def kick_player(request, session_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    game_session = get_object_or_404(GameSession, session_id=session_id)
    target_nickname = request.POST.get('target_nickname')
    kicker_nickname = request.POST.get('nickname')

    if not game_session.is_active:
        return render_ended_page(request, game_session, '🎭 이미 막을 내린 아발론 세션입니다.')

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
        Player.objects.get(game_session=game_session, nickname=target_nickname).delete()
    except Player.DoesNotExist:
        pass

    query = urlencode({'nickname': kicker_nickname, 'pin': request.POST.get('pin')})
    return redirect(f"{reverse('lobby', args=[session_id])}?{query}")