import json
import os
from django import template

register = template.Library()

# 역할 데이터를 한 번만 로드
def get_role_data():
    current_dir = os.path.dirname(os.path.dirname(__file__))
    role_messages_path = os.path.join(current_dir, '..', 'ftn', 'role_messages.json')
    with open(role_messages_path, 'r', encoding='utf-8') as f:
        return json.load(f)

ROLE_DATA = get_role_data()

@register.filter
def role_emoji(role_name):
    """역할 이름으로 이모지 반환"""
    return ROLE_DATA.get(role_name, {}).get('emoji', '')

@register.filter
def role_name(role_name):
    """역할 이름으로 한국어 이름 반환"""
    return ROLE_DATA.get(role_name, {}).get('name', role_name)

@register.filter
def role_display(role_name):
    """역할 이름으로 이모지 + 이름 반환"""
    role_info = ROLE_DATA.get(role_name, {})
    emoji = role_info.get('emoji', '')
    name = role_info.get('name', role_name)
    return f"{emoji} {name}"

@register.filter
def role_priority(role_name):
    """역할 이름으로 우선순위 반환"""
    return ROLE_DATA.get(role_name, {}).get('priority', 999)

@register.filter
def get_role_at_index(roles, index):
    """특정 인덱스의 역할을 반환"""
    try:
        return roles[index] if roles and index < len(roles) else None
    except (IndexError, TypeError):
        return None 