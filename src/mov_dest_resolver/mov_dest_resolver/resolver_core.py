"""
자연어 발화 -> ECC 랜드마크 매칭.

ROS2에 의존하지 않는 순수 로직만 담는다 (dest_resolver_node.py가 이걸 감싼다).
설계 원칙 (docs/SESSION_LOG.md #5 참고):
  - LLM은 좌표를 직접 내지 않는다. intent(target_type/place_name/category)만
    구조화해서 뽑고, 실제 좌표는 항상 결정론적 코드가 DB에서 그대로 가져온다.
  - place_name/category 둘 다 Gemini structured output의 enum으로 DB에
    실재하는 값만 나오도록 제약하고, 그래도 한 번 더 DB에 있는지 방어적으로
    확인한다(place_name과 동일한 할루시네이션 방지 패턴).
  - target_type="category"(예: "화장실 가고 싶어")는 (2026-08-30 설계 변경)
    로봇이 알아서 최근접을 골라 데려가지 않는다. 같은 카테고리에 후보가
    1개뿐이면 바로 확정하지만, 여러 개면 기본적으로 전부 사용자에게
    보여주고 직접 고르게 한다 — "카페 가고 싶어"에 자동으로 아무 카페나
    데려가는 게 항상 맞는 게 아니기 때문(예: "스타벅스 말고 다른 카페"처럼
    제외/선호가 섞인 발화는 로봇이 임의로 판단하면 틀리기 쉬움).
  - 단, "제일/가장 가까운 X"처럼 사용자가 명시적으로 최근접을 원하면
    (wants_nearest=True) 얘기가 다르다 — 이때는 후보를 나열하지 않고
    (current_x, current_y) 기준 최근접 하나로 바로 확정한다. 위치가 없으면
    (아직 dest_resolver_node가 위치 소스를 안 넘겨줌 — /amcl_pose 등 Nav2
    연동 대기 중) 최근접을 계산할 수 없으니 일반 카테고리 요청과 동일하게
    후보 나열로 안전하게 대체된다. 즉 이 로직은 지금 당장은 항상 나열로
    귀결되지만, 나중에 위치 소스만 연결하면 코드 변경 없이 의도대로 동작함.
  - "쌀국수 먹고 싶어"처럼 메뉴/특징으로 특정 장소 하나를 간접 지칭하는
    발화는 (2026-08-30 추가) named_place로 직접 매칭한다 — landmarks.csv의
    `desc` 컬럼(메뉴/특징, 예: "포포420(쌀국수)")을 프롬프트에 같이 주고,
    place_name 매칭 규칙에 "이름 직접 언급"뿐 아니라 "desc로 유추 가능"도
    포함시켰다. category처럼 여러 후보를 나열하지 않고 바로 확정되는 이유는,
    desc가 사실상 그 장소의 또 다른 식별자(별명) 역할이라 이름을 직접 부른
    것과 같다고 보기 때문 — 단, desc가 비어있거나 모호하면(둘 이상의 장소
    desc에 다 걸리면) 그냥 unsupported로 남는다(오분류보다 안전).
  - "화장실 가고 싶어"/"엘리베이터 어디야"처럼 AUTO_NEAREST_CATEGORIES에 속한
    카테고리는 (2026-09-02 추가) "제일/가장 가까운"이라는 명시적 wants_nearest
    표현이 없어도 위치만 있으면 후보를 나열하지 않고 바로 최근접으로 확정한다.
    다른 category(카페/식당 등)와 달리 화장실/엘리베이터는 어느 걸 가든
    사용자 목적(용변/이동)에 차이가 없어 "스타벅스 말고 다른 카페"류의
    선호/제외가 있을 수 없기 때문 — 사용자는 사실상 항상 "가장 가까운"을
    의도하고 물어본 것으로 간주해도 안전하다. 위치가 없으면(AMCL 미localize)
    기존과 동일하게 안전한 후보 나열로 대체된다. 이때 ResolveResult에
    auto_resolved_category를 채워서, mov_ui가 TTS 안내 문구를 특정 장소명
    (예: "동1 화장실") 대신 카테고리명("화장실")으로 일반화해 말하게 한다 —
    방향+번호가 붙은 이름을 그대로 읽으면 부자연스럽기 때문.
"""

import csv
import json
import os
from dataclasses import dataclass, field

from ament_index_python.packages import get_package_share_directory
from google import genai
from google.genai import types

# mov_slam 패키지의 share 리소스로 설치된 랜드마크 DB를 가리킨다(2026-09-03,
# 호스트 ~/workspace 마운트 절대경로 하드코딩에서 전환). 원본 산출 과정(SLAM
# 작업 디렉토리, 백업/검증 이미지 포함)은 /workspace/slam/slam_frommap에 그대로
# 있고, 맵/좌표DB가 갱신될 때마다 최종본만 mov_slam/landmarks로 승격한다.
DEFAULT_LANDMARKS_CSV = os.path.join(
    get_package_share_directory('mov_slam'), 'landmarks', 'landmarks.csv')

# 실측 결과(2026-08-29): 플래그십 gemini-3.6-flash는 발화 1건당 평균 5.1초로
# 음성 인터랙션엔 너무 느리고, gemini-3.5-flash-lite는 평균 0.94초로 약 5배
# 빠르면서 정확도 손실 없음(작은 고정 목록 분류라 플래그십 추론력이 불필요).
# "latest" 별칭 대신 특정 버전을 고정해 구글 쪽 조용한 모델 교체로 동작이
# 바뀌는 걸 방지함. 필요하면 GEMINI_MODEL 환경변수로 덮어쓸 것.
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash-lite')

# 어느 후보를 가든 사용자 목적에 차이가 없는 카테고리 — "제일/가장 가까운"을
# 명시하지 않아도 항상 최근접으로 바로 안내한다(resolve() 참고). 카페/식당처럼
# 브랜드/메뉴 선호가 있을 수 있는 카테고리는 여기 포함하지 않는다.
AUTO_NEAREST_CATEGORIES = frozenset({'화장실', '엘리베이터'})


@dataclass
class Landmark:
    name: str
    x: float
    y: float
    category: str = ''
    desc: str = ''  # 메뉴/특징 (예: "쌀국수·분짜") — 간접 지칭 매칭에 씀, resolve() 참고


@dataclass
class ResolveResult:
    success: bool
    target_type: str  # "named_place" | "category" | "unsupported"
    place_name: str | None = None
    category: str | None = None
    x: float | None = None
    y: float | None = None
    error_message: str = ''
    # True면 category 후보가 여럿이라 확정 못 함 — success는 False로 두고
    # candidates(장소명 목록)를 대신 채운다. 호출자(dest_resolver_node)는 이
    # 경우 DestResult 실패가 아니라 DestChoices를 발행해서 사용자가 고르게 해야 함.
    needs_choice: bool = False
    candidates: list[str] = field(default_factory=list)
    # success=True이고 이 값이 채워져 있으면, 후보가 여럿이라도 사용자에게
    # 안 물어보고(needs_choice=False) 카테고리 기준으로 자동 확정됐다는 뜻
    # (AUTO_NEAREST_CATEGORIES 참고). mov_ui는 TTS 안내 문구를 place_name
    # 대신 이 카테고리명으로 일반화해 말해야 한다.
    auto_resolved_category: str | None = None


_PROMPT_TEMPLATE = """당신은 ECC(이화캠퍼스콤플렉스) 실내 안내 로봇의 목적지 해석기입니다.
사용자의 발화는 음성인식(STT) 결과라, 발음이 비슷한 다른 단어로 잘못 인식된
부분이 섞여 있을 수 있습니다(예: "커피만 세고 싶어"는 "커피 마시고 싶어"가
잘못 인식됐을 가능성이 높습니다). 그럴듯한 오인식으로 보이면 문맥상 가장
자연스러운 의도로 먼저 보정한 뒤, 아래 "장소 목록"에 있는 곳 중 하나를
가리키는지 판단하세요.

규칙:
1. 발화가 목록에 있는 특정 장소 하나를 가리키면 target_type="named_place"로
   답하고 place_name에 목록의 정확한 이름을 그대로 쓰세요. 아래 두 경우 다
   포함됩니다:
   (a) 이름을 직접 언급(오타/줄임말/의미상 유사 표현 포함)
   (b) 장소 목록에 괄호로 같이 적힌 메뉴/특징만으로 그 장소 하나를 특정
       가능("쌀국수 먹고 싶어" 등). 단, 그 메뉴/특징이 여러 장소에 겹치면
       하나로 특정 못 하니 이 규칙을 적용하지 말고 4번(unsupported)으로.
2. 발화가 특정 장소가 아니라 카테고리(예: 화장실, 엘리베이터, 카페)를 가리키면
   target_type="category"로 답하고, category에 판단한 카테고리명을 쓰세요.
3. "~로 데려다줘"처럼 명시적 요청이든 "~어디야"처럼 정보를 묻는 질문이든 상관없이,
   장소/카테고리를 특정할 수 있으면 위 1, 2번으로 처리하세요. (실제 안내 여부는
   이후 별도로 사용자에게 확인합니다.)
4. 목록에 없는 장소, 목적지와 무관한 발화(잡담/시간 질문/취소 등), 또는 무엇을
   가리키는지 특정할 수 없는 발화는 target_type="unsupported"로 답하세요.
5. place_name/category는 각각 아래 목록에 있는 값만 사용하고, 해당 없으면
   "NONE"이라고 쓰세요.

[장소 목록]
{landmark_list}

[카테고리 목록]
{category_list}

[사용자 발화]
{text}
"""


def load_landmarks(csv_path: str = DEFAULT_LANDMARKS_CSV) -> list[Landmark]:
    """
    landmarks.csv(name,x,y,z,yaw,category,desc)를 읽는다. z/yaw는 쓰지 않는다.

    z는 B4 단일 층 2D 주행에서 의미 없는 클릭 노이즈이고, yaw는 좌표를 찍은
    도구(RViz Publish Point)가 애초에 방향을 발행하지 않아 전부 기본값 0이다.
    category(2026-08-30 추가)/desc(2026-08-30 추가, 메뉴/특징)는 오래된
    CSV엔 없을 수 있어 없으면 빈 문자열로 채운다.
    """
    landmarks = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if not row.get('name'):
                continue
            landmarks.append(Landmark(
                name=row['name'],
                x=float(row['x']),
                y=float(row['y']),
                category=row.get('category') or '',
                desc=row.get('desc') or '',
            ))
    return landmarks


def _unique_categories(landmarks: list[Landmark]) -> list[str]:
    # dict.fromkeys로 첫 등장 순서를 유지하면서 중복 제거 (set은 순서가 안 정해짐).
    return list(dict.fromkeys(lm.category for lm in landmarks if lm.category))


def _build_prompt(text: str, landmarks: list[Landmark]) -> str:
    landmark_list = '\n'.join(
        f'- {lm.name} ({lm.desc})' if lm.desc else f'- {lm.name}'
        for lm in landmarks)
    category_list = '\n'.join(f'- {c}' for c in _unique_categories(landmarks))
    return _PROMPT_TEMPLATE.format(
        landmark_list=landmark_list, category_list=category_list, text=text)


_NONE_SENTINEL = 'NONE'  # Gemini의 response_schema는 enum에 빈 문자열("")을 허용하지 않음


def _build_response_schema(landmarks: list[Landmark]) -> dict:
    names = [lm.name for lm in landmarks] + [_NONE_SENTINEL]
    categories = _unique_categories(landmarks) + [_NONE_SENTINEL]
    return {
        'type': 'object',
        'properties': {
            'target_type': {
                'type': 'string',
                'enum': ['named_place', 'category', 'unsupported'],
            },
            # DB에 실재하는 이름/카테고리만 고를 수 있게 enum으로 제약 —
            # 할루시네이션 방지(둘 다 같은 패턴).
            'place_name': {'type': 'string', 'enum': names},
            'category': {'type': 'string', 'enum': categories},
            # target_type="category"일 때만 의미 있음 — "제일 가까운 X"처럼
            # 명시적 최근접 요청인지. 그 외엔 무시됨.
            'wants_nearest': {'type': 'boolean'},
        },
        'required': ['target_type', 'place_name', 'category', 'wants_nearest'],
    }


def _find_nearest_in_category(
    category: str, current_x: float, current_y: float, landmarks: list[Landmark],
) -> Landmark | None:
    """category와 일치하는 랜드마크 중 (current_x, current_y)에서 가장 가까운 것."""
    candidates = [lm for lm in landmarks if lm.category == category]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda lm: (lm.x - current_x) ** 2 + (lm.y - current_y) ** 2,
    )


def resolve(
    text: str, landmarks: list[Landmark], client: genai.Client,
    current_x: float | None = None, current_y: float | None = None,
) -> ResolveResult:
    """
    발화 텍스트를 LLM으로 분류하고, 좌표까지 결정론적으로 찾아 반환한다.

    named_place면 DB에서 이름으로 바로 조회. category면 같은 카테고리인
    landmark를 전부 찾는다 — 1개뿐이면 바로 확정, 여러 개면 사용자가 명시적으로
    최근접을 원했거나(wants_nearest) 카테고리 자체가 AUTO_NEAREST_CATEGORIES에
    속하면서(화장실/엘리베이터 등 — 어느 후보든 상관없는 경우) 현재 위치
    (current_x/y)도 주어졌을 때 최근접 하나로 확정한다. 그 외(최근접을 안
    원했고 자동확정 대상도 아니거나, 위치가 없음)엔 ResolveResult.needs_choice
    =True + candidates로 후보 목록만 반환한다(최종 선택은 사용자 몫 — 호출자가
    UI에 물어봐야 함). current_x/y는 호출자가 로봇의 현재 위치(예: /amcl_pose)
    에서 가져와 넘겨줘야 하며, 아직 그 연동이 없다면 항상 None으로 호출해도
    안전하다(이 경우 그냥 후보 나열로 대체됨).
    """
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=_build_prompt(text, landmarks),
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type='application/json',
                response_schema=_build_response_schema(landmarks),
            ),
        )
    except Exception as e:
        return ResolveResult(
            success=False, target_type='unsupported',
            error_message=f'LLM 호출 오류: {e}')

    try:
        parsed = json.loads(response.text)
    except (ValueError, TypeError) as e:
        return ResolveResult(
            success=False, target_type='unsupported',
            error_message=f'LLM 응답 파싱 오류: {e}')

    target_type = parsed.get('target_type', 'unsupported')
    raw_place_name = parsed.get('place_name')
    raw_category = parsed.get('category')
    place_name = None if raw_place_name in (None, '', _NONE_SENTINEL) else raw_place_name
    category = None if raw_category in (None, '', _NONE_SENTINEL) else raw_category
    wants_nearest = bool(parsed.get('wants_nearest', False))

    if target_type == 'named_place':
        match = next((lm for lm in landmarks if lm.name == place_name), None)
        if match is None:
            # 스키마 enum으로 이미 막혀 있어야 하지만, 방어적으로 한 번 더 확인.
            return ResolveResult(
                success=False, target_type='unsupported',
                error_message=f'DB에 없는 장소명: {place_name!r}')
        return ResolveResult(
            success=True, target_type='named_place',
            place_name=match.name, x=match.x, y=match.y)

    if target_type == 'category':
        if category is None:
            return ResolveResult(
                success=False, target_type='unsupported',
                error_message='목적지를 특정할 수 없는 발화')

        matches = [lm for lm in landmarks if lm.category == category]
        if not matches:
            # 스키마 enum으로 이미 막혀 있어야 하지만, 방어적으로 한 번 더 확인.
            return ResolveResult(
                success=False, target_type='category', category=category,
                error_message=f'DB에 없는 카테고리: {category!r}')

        auto_nearest = category in AUTO_NEAREST_CATEGORIES
        announce = category if auto_nearest else None

        if len(matches) == 1:
            only = matches[0]
            return ResolveResult(
                success=True, target_type='category', category=category,
                place_name=only.name, x=only.x, y=only.y,
                auto_resolved_category=announce)

        if (wants_nearest or auto_nearest) and current_x is not None and current_y is not None:
            nearest = _find_nearest_in_category(category, current_x, current_y, landmarks)
            return ResolveResult(
                success=True, target_type='category', category=category,
                place_name=nearest.name, x=nearest.x, y=nearest.y,
                auto_resolved_category=announce)

        return ResolveResult(
            success=False, target_type='category', category=category,
            needs_choice=True, candidates=[lm.name for lm in matches],
            error_message=f'"{category}" 후보가 여러 개라 선택 필요')

    return ResolveResult(
        success=False, target_type='unsupported',
        error_message='목적지를 특정할 수 없는 발화')
