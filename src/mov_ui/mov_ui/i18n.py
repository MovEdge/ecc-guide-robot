"""
간단한 한국어/영어 다국어 지원.

사용법:
    from mov_ui.i18n import i18n

    label = QLabel(i18n.t('idle.title'))
    i18n.register(lambda: label.setText(i18n.t('idle.title')))

`i18n.set_lang('en')`을 호출하면 등록된 모든 콜백이 실행되어
화면에 떠 있는 모든 텍스트가 즉시 갱신된다.
"""

import re

from PyQt5.QtCore import QObject, pyqtSignal

TEXTS = {
    'app.name': {'ko': 'ECC 안내 로봇', 'en': 'ECC GUIDE ROBOT'},

    'idle.title': {'ko': '목적지를 말씀해주세요', 'en': 'Where would you\nlike to go?'},
    'idle.subtitle': {
        'ko': '버튼을 누르고 편하게 말씀해 주시면\n제가 길을 안내해 드릴게요',
        'en': 'Press the button and tell me\nwhere you\u2019d like to go',
    },
    'idle.speak_button': {'ko': '말하기', 'en': 'Speak'},

    'listening.title': {'ko': '듣고 있어요...', 'en': 'Listening...'},
    'listening.subtitle': {
        'ko': '말씀이 끝나면 잠시만 기다려 주세요',
        'en': 'Please wait a moment after you finish',
    },
    'listening.cancel': {'ko': '취소', 'en': 'Cancel'},

    'confirming.eyebrow': {'ko': '음성 인식 결과', 'en': 'VOICE RECOGNITION RESULT'},
    'confirming.title': {'ko': '이렇게 알아들었어요', 'en': 'Here\u2019s what I heard'},
    'confirming.retry': {'ko': '다시 말하기', 'en': 'Try Again'},
    'confirming.confirm': {'ko': '확인', 'en': 'Confirm'},

    'choosing.eyebrow': {'ko': '여러 곳이 있어요', 'en': 'MULTIPLE OPTIONS'},
    'choosing.title': {
        'ko': '어느 {category}로 갈까요?',
        'en': 'Which {category} should I take you to?',
    },
    'choosing.cancel': {'ko': '취소', 'en': 'Cancel'},

    'navigating.eyebrow': {'ko': '안내 중', 'en': 'NAVIGATING'},
    'navigating.cancel': {'ko': '취소', 'en': 'Cancel'},

    'arrived.title': {'ko': '도착했습니다', 'en': 'You\u2019ve Arrived'},
    'arrived.subtitle': {'ko': '즐거운 시간 되세요!', 'en': 'Have a great time!'},
    'arrived.new_destination': {'ko': '새 장소 안내', 'en': 'New Destination'},
    'arrived.home': {'ko': '처음으로', 'en': 'Home'},

    'error.title': {'ko': '문제가 발생했어요', 'en': 'Something Went Wrong'},
    'error.retry': {'ko': '재시도', 'en': 'Retry'},
}


class I18n(QObject):
    language_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._lang = 'ko'
        self._callbacks = []

    @property
    def lang(self):
        return self._lang

    def t(self, key):
        entry = TEXTS.get(key)
        if entry is None:
            return key
        return entry.get(self._lang, entry.get('ko', key))

    def set_lang(self, lang):
        if lang == self._lang:
            return
        self._lang = lang
        for cb in self._callbacks:
            cb()
        self.language_changed.emit(lang)

    def toggle(self):
        self.set_lang('en' if self._lang == 'ko' else 'ko')

    def register(self, callback):
        """언어가 바뀔 때마다 호출될 콜백(보통 setText 람다)을 등록."""
        self._callbacks.append(callback)


i18n = I18n()

# ── 장소명/카테고리 표시 로컬라이즈 ──
#
# landmarks.csv의 name/category는 전부 한국어다. STT 결과 텍스트(CONFIRMING
# 화면)는 Whisper가 실제 발화 언어를 그대로 인식하니 따로 손댈 게 없지만,
# dest_resolver가 DB에서 그대로 돌려주는 place_name/category는 영어 UI에서도
# 한국어 그대로 나온다 — 이 두 함수는 "화면에 보여줄 때만" 영어로 바꾼다
# (매칭/TTS 등 다른 곳에 쓰이는 원본 문자열은 절대 건드리지 않음).

# 이름 끝에 이미 영어 표기가 괄호로 붙어있는 경우만 그걸 쓴다
# (예: "구시아 푸드마켓(GUSIA FOODMARKET)" → "GUSIA FOODMARKET"). 괄호 안이
# 한글이면(예: "스타벅스(썬큰가든)"의 "썬큰가든") 영어 표기가 아니라는 뜻이라
# 건드리지 않는다 — 없는 영어 이름을 지어내는 것보다 한국어 그대로 보여주는
# 게 안전(사용자 요청: "번역가능한건 번역하고 대명사는 들리는대로 영어로" —
# 랜드마크 DB엔 자동 번역/음역 데이터가 없어서, 지금은 이미 영어 표기가
# 붙어있는 이름만 그 표기를 쓰는 선에서 지원).
_EN_NAME_SUFFIX_RE = re.compile(r'\(([A-Za-z0-9][A-Za-z0-9 &.\'-]*)\)\s*$')

# 카테고리는 종류가 적어(landmarks.csv 기준 화장실/카페 등 소수) 직접 번역
# 매핑. 여기 없는 카테고리는 원래 한국어 문자열을 그대로 보여준다(오역보다
# 안전한 fallback).
_CATEGORY_EN = {
    '화장실': 'Restroom',
    '엘리베이터': 'Elevator',
    '카페': 'Cafe',
    '식당': 'Restaurant',
    '홀': 'Hall',
    '포토부스': 'Photo Booth',
    '서점': 'Bookstore',
    '상점': 'Shop',
    '출구': 'Exit',
    '은행': 'Bank',
    '약국': 'Pharmacy',
    '영화관': 'Cinema',
    '헬스장': 'Gym',
    '편의점': 'Convenience Store',
    '인쇄소': 'Print Shop',
    '안경원': 'Optical Shop',
}


def localize_place_name(name: str) -> str:
    """장소명을 현재 UI 언어에 맞게 표시용으로 변환 (원본 문자열은 안 건드림).

    영어 모드에선 괄호 안 영어 표기만 뽑아 쓰고, 한국어 모드에선 그 영어
    표기를 아예 잘라내서 보여준다 — 안 자르면 "구시아 푸드마켓(GUSIA
    FOODMARKET)"처럼 한국어 화면/음성에 영어 표기가 그대로 섞여 나온다.
    """
    if not name:
        return name
    match = _EN_NAME_SUFFIX_RE.search(name)
    if i18n.lang == 'en':
        return match.group(1) if match else name
    return name[:match.start()].rstrip() if match else name


def localize_category(category: str) -> str:
    """카테고리명을 현재 UI 언어에 맞게 표시용으로 변환 (원본 문자열은 안 건드림)."""
    if i18n.lang != 'en' or not category:
        return category
    return _CATEGORY_EN.get(category, category)
