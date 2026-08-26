"""
간단한 한국어/영어 다국어 지원.

사용법:
    from mov_ui.i18n import i18n

    label = QLabel(i18n.t('idle.title'))
    i18n.register(lambda: label.setText(i18n.t('idle.title')))

`i18n.set_lang('en')`을 호출하면 등록된 모든 콜백이 실행되어
화면에 떠 있는 모든 텍스트가 즉시 갱신된다.
"""

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

    'confirming.eyebrow': {'ko': '음성 인식 결과', 'en': 'VOICE RECOGNITION RESULT'},
    'confirming.title': {'ko': '이렇게 알아들었어요', 'en': 'Here\u2019s what I heard'},
    'confirming.retry': {'ko': '다시 말하기', 'en': 'Try Again'},
    'confirming.confirm': {'ko': '확인', 'en': 'Confirm'},

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
