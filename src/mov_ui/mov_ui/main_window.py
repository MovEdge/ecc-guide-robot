from PyQt5.QtWidgets import QMainWindow, QStackedWidget, QPushButton

from mov_ui.pages.idle_page import IdlePage
from mov_ui.pages.listening_page import ListeningPage
from mov_ui.pages.confirming_page import ConfirmingPage
from mov_ui.pages.navigating_page import NavigatingPage
from mov_ui.pages.arrived_page import ArrivedPage
from mov_ui.pages.error_page import ErrorPage
from mov_ui.styles import SCREEN_W, SCREEN_H
from mov_ui.i18n import i18n


class MainWindow(QMainWindow):
    """FSM 상태 하나 = QStackedWidget 페이지 하나.

    Waveshare 8DP-CAPLCD(1280x800) 기준 고정 크기.
    실제 상태 전이는 mov_fsm이 아직 없어서 ui_node가 임시로 판단한다.
    나중에 mov_fsm이 상태 토픽을 발행하면 그걸 구독해서 set_state()만
    호출하는 방식으로 옮기면 된다.
    """

    def __init__(self, callbacks):
        super().__init__()
        self.setWindowTitle('ECC Guide Robot')
        self.setFixedSize(SCREEN_W, SCREEN_H)

        self.idle_page = IdlePage(callbacks['on_speak_clicked'])
        self.listening_page = ListeningPage()
        self.confirming_page = ConfirmingPage(
            callbacks['on_confirm_clicked'], callbacks['on_retry_clicked'])
        self.navigating_page = NavigatingPage(callbacks['on_cancel_clicked'])
        self.arrived_page = ArrivedPage(
            callbacks['on_new_destination_clicked'], callbacks['on_home_clicked'])
        self.error_page = ErrorPage(callbacks['on_retry_clicked'])

        self.stack = QStackedWidget()
        self._state_to_index = {}
        for state, page in [
            ('IDLE', self.idle_page),
            ('LISTENING', self.listening_page),
            ('CONFIRMING', self.confirming_page),
            ('NAVIGATING', self.navigating_page),
            ('ARRIVED', self.arrived_page),
            ('ERROR', self.error_page),
        ]:
            self._state_to_index[state] = self.stack.addWidget(page)

        self.setCentralWidget(self.stack)
        self.set_state('IDLE')

        # ── 언어 전환 버튼 (모든 상태 화면 위에 항상 떠 있음) ──
        self.lang_button = QPushButton(self._lang_label(), self)
        self.lang_button.setObjectName('LangToggle')
        self.lang_button.setFixedSize(84, 40)
        self.lang_button.move(SCREEN_W - 84 - 24, 24)
        self.lang_button.clicked.connect(self._on_lang_toggle)
        self.lang_button.raise_()

    def _lang_label(self):
        return 'EN' if i18n.lang == 'ko' else '한국어'

    def _on_lang_toggle(self):
        i18n.toggle()
        self.lang_button.setText(self._lang_label())

    def set_state(self, state):
        self.stack.setCurrentIndex(self._state_to_index[state])
