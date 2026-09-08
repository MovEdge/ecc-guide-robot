"""
ROS2 없이 resolver_core만 단독으로 테스트.

GEMINI_API_KEY가 없으면 실제 API를 호출하는 테스트는 스킵된다 (DB 로딩 테스트는
키 없이도 항상 실행됨).
"""

import os

import pytest
from dotenv import load_dotenv
from google import genai

from mov_dest_resolver.resolver_core import DEFAULT_LANDMARKS_CSV, load_landmarks, resolve

load_dotenv()

HAS_API_KEY = bool(os.environ.get('GEMINI_API_KEY'))


def test_load_landmarks_from_real_csv():
    landmarks = load_landmarks(DEFAULT_LANDMARKS_CSV)
    assert len(landmarks) > 30  # 2026-08-29 기준 36개
    for lm in landmarks:
        assert isinstance(lm.name, str) and lm.name
        assert isinstance(lm.x, float)
        assert isinstance(lm.y, float)


def test_load_landmarks_includes_category():
    landmarks = load_landmarks(DEFAULT_LANDMARKS_CSV)
    categories = {lm.category for lm in landmarks}
    assert '화장실' in categories
    assert '카페' in categories
    assert '' not in categories  # 2026-08-30 기준 36개 전부 채워짐


@pytest.mark.skipif(not HAS_API_KEY, reason='GEMINI_API_KEY 미설정 — 실제 API 호출 테스트 스킵')
@pytest.mark.parametrize('text,expected_target_type', [
    ('스타벅스 어디야', 'named_place'),       # DB엔 "스타벅스(썬큰가든)(STARBUCKS)" — 별칭 없이 의미로 매칭돼야 함
    ('화장실 가고 싶어', 'category'),         # 여러 개(서1/서2/서3/동1/동2)라 특정 불가
    ('오늘 날씨 어때', 'unsupported'),        # 목적지와 무관
    ('쌀국수 먹고 싶어', 'named_place'),      # desc 기반 간접 지칭 — 구시아(포포420)로 특정돼야 함
])
def test_resolve_real_api(text, expected_target_type):
    landmarks = load_landmarks(DEFAULT_LANDMARKS_CSV)
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    result = resolve(text, landmarks, client)
    assert result.target_type == expected_target_type, result


@pytest.mark.skipif(not HAS_API_KEY, reason='GEMINI_API_KEY 미설정 — 실제 API 호출 테스트 스킵')
def test_resolve_tolerates_stt_misrecognition():
    """'커피만 세고 싶어'는 '커피 마시고 싶어'의 STT 오인식 — unsupported가 아니라 카페 후보로 나와야 한다."""
    landmarks = load_landmarks(DEFAULT_LANDMARKS_CSV)
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    result = resolve('커피만 세고 싶어', landmarks, client)
    assert result.target_type == 'category'
    assert result.category == '카페'


@pytest.mark.skipif(not HAS_API_KEY, reason='GEMINI_API_KEY 미설정 — 실제 API 호출 테스트 스킵')
def test_resolve_menu_reference_resolves_to_specific_restaurant():
    """desc(메뉴)로만 특정 가능한 발화는 나열 없이 바로 그 장소로 확정돼야 한다."""
    landmarks = load_landmarks(DEFAULT_LANDMARKS_CSV)
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    result = resolve('쌀국수 먹고 싶어', landmarks, client)
    assert result.success is True
    assert result.needs_choice is False
    assert result.place_name == '구시아 푸드마켓(GUSIA FOODMARKET)'


@pytest.mark.skipif(not HAS_API_KEY, reason='GEMINI_API_KEY 미설정 — 실제 API 호출 테스트 스킵')
def test_resolve_category_with_multiple_matches_asks_user_to_choose():
    """화장실은 5개(서1/서2/서3/동1/동2)라 로봇이 임의로 고르지 않고 후보를 나열해야 한다."""
    landmarks = load_landmarks(DEFAULT_LANDMARKS_CSV)
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    result = resolve('화장실 가고 싶어', landmarks, client)
    assert result.success is False
    assert result.needs_choice is True
    assert result.target_type == 'category'
    assert len(result.candidates) == 5
    assert '서3 화장실(WEST3 RESTROOM)' in result.candidates


@pytest.mark.skipif(not HAS_API_KEY, reason='GEMINI_API_KEY 미설정 — 실제 API 호출 테스트 스킵')
def test_resolve_category_with_single_match_resolves_directly():
    """DB에 후보가 1개뿐인 카테고리는 물어볼 필요 없이 바로 확정돼야 한다."""
    landmarks = load_landmarks(DEFAULT_LANDMARKS_CSV)
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    result = resolve('헬스장 가고 싶어', landmarks, client)  # DB에 1개뿐
    assert result.success is True
    assert result.needs_choice is False
    assert result.place_name == '헬스장 (피트니스 센터)(FITNESS CENTER)'
    # 헬스장은 AUTO_NEAREST_CATEGORIES에 없으니 TTS 일반화 대상이 아니어야 함.
    assert result.auto_resolved_category is None


@pytest.mark.skipif(not HAS_API_KEY, reason='GEMINI_API_KEY 미설정 — 실제 API 호출 테스트 스킵')
def test_resolve_explicit_nearest_with_position_resolves_directly():
    """'제일 가까운'처럼 명시적으로 최근접을 원하고 위치도 있으면 안 물어보고 바로 확정돼야 한다."""
    landmarks = load_landmarks(DEFAULT_LANDMARKS_CSV)
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    # 서3 화장실(62.53, 26.29) 바로 옆 — 다른 화장실은 전부 30m 이상 떨어져 있음.
    result = resolve(
        '제일 가까운 화장실 어디야', landmarks, client,
        current_x=63.0, current_y=26.0)
    assert result.success is True
    assert result.needs_choice is False
    assert result.place_name == '서3 화장실(WEST3 RESTROOM)'
    # 화장실은 AUTO_NEAREST_CATEGORIES 소속이라 TTS 일반화 안내 대상이어야 함.
    assert result.auto_resolved_category == '화장실'


@pytest.mark.skipif(not HAS_API_KEY, reason='GEMINI_API_KEY 미설정 — 실제 API 호출 테스트 스킵')
def test_resolve_explicit_nearest_without_position_falls_back_to_choice():
    """최근접을 원해도 위치가 없으면(지금 dest_resolver_node의 실제 상태) 안전하게 후보를 나열해야 한다."""
    landmarks = load_landmarks(DEFAULT_LANDMARKS_CSV)
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    result = resolve('제일 가까운 화장실 어디야', landmarks, client)  # 위치 없음
    assert result.success is False
    assert result.needs_choice is True
    assert len(result.candidates) == 5


@pytest.mark.skipif(not HAS_API_KEY, reason='GEMINI_API_KEY 미설정 — 실제 API 호출 테스트 스킵')
def test_resolve_auto_nearest_category_with_position_resolves_without_asking():
    """화장실/엘리베이터는 (2026-09-02부터) "제일/가장"이 없어도 위치만 있으면
    후보를 나열하지 않고 바로 최근접으로 확정해야 한다 — 어느 화장실이든
    사용자 목적(용변)엔 차이가 없어서 매번 나열해서 물어볼 필요가 없기 때문."""
    landmarks = load_landmarks(DEFAULT_LANDMARKS_CSV)
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    result = resolve(
        '화장실 가고 싶어', landmarks, client,  # "제일/가장" 없음
        current_x=63.0, current_y=26.0)
    assert result.success is True
    assert result.needs_choice is False
    assert result.place_name == '서3 화장실(WEST3 RESTROOM)'
    assert result.auto_resolved_category == '화장실'


@pytest.mark.skipif(not HAS_API_KEY, reason='GEMINI_API_KEY 미설정 — 실제 API 호출 테스트 스킵')
def test_resolve_non_auto_nearest_category_with_position_still_lists():
    """카페처럼 브랜드/취향 선호가 있을 수 있는 카테고리는 위치가 있고 최근접을
    명시하지 않았으면 여전히 로봇이 임의로 고르지 말고 나열해야 한다(기존 동작
    유지 — AUTO_NEAREST_CATEGORIES에 없는 카테고리는 이번 변경의 영향을 안 받음)."""
    landmarks = load_landmarks(DEFAULT_LANDMARKS_CSV)
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    result = resolve(
        '카페 가고 싶어', landmarks, client,  # "제일/가장" 없음
        current_x=63.0, current_y=26.0)
    assert result.needs_choice is True
    assert len(result.candidates) == 3
