from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsOpacityEffect, QPushButton
)

from mov_ui.styles import SCREEN_W, SCREEN_H, PRIMARY, PRIMARY_SOFT_RGBA, make_blob
from mov_ui.i18n import i18n

_BAR_HEIGHTS = [26, 54, 84, 54, 26]


class ListeningPage(QWidget):
    """LISTENING — 음성인식중. 파형 바가 은은하게 움직여 '듣고 있음'을 표현.

    마이크 이모지(🎙️)는 이 환경에 이모지 폰트가 없어 빈 네모로 렌더링돼서 뺐다
    (파형 바만으로 충분히 "듣고 있음"이 전달됨).
    """

    def __init__(self, on_cancel_clicked):
        super().__init__()
        self.setObjectName('ListeningPage')

        blob = make_blob(self, 620, PRIMARY_SOFT_RGBA, alpha=0.28)
        blob.move((SCREEN_W - 620) // 2, (SCREEN_H - 620) // 2 - 40)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(80, 60, 80, 60)
        layout.setSpacing(20)
        layout.addStretch(1)

        # ── 파형 바 ──
        wave_row = QHBoxLayout()
        wave_row.setSpacing(10)
        wave_row.addStretch(1)
        self._bars = []
        for h in _BAR_HEIGHTS:
            bar = QFrame()
            bar.setFixedSize(14, h)
            bar.setStyleSheet(
                f'background-color: {PRIMARY}; border-radius: 7px;')
            wave_row.addWidget(bar)
            self._bars.append(bar)
        wave_row.addStretch(1)
        layout.addLayout(wave_row)

        layout.addSpacing(12)

        title = QLabel(i18n.t('listening.title'))
        title.setObjectName('TitleLabel')
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(i18n.t('listening.subtitle'))
        subtitle.setObjectName('SubtitleLabel')
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(28)

        cancel_button = QPushButton(i18n.t('listening.cancel'))
        cancel_button.setProperty('type', 'secondary')
        cancel_button.setFixedHeight(90)
        cancel_button.clicked.connect(on_cancel_clicked)
        layout.addWidget(cancel_button)

        layout.addStretch(1)

        i18n.register(lambda: (
            title.setText(i18n.t('listening.title')),
            subtitle.setText(i18n.t('listening.subtitle')),
            cancel_button.setText(i18n.t('listening.cancel')),
        ))

        # ── 파형 바 애니메이션 (각 바마다 살짝 다른 타이밍) ──
        self._bar_anims = []
        for i, bar in enumerate(self._bars):
            effect = QGraphicsOpacityEffect(bar)
            bar.setGraphicsEffect(effect)
            anim = QPropertyAnimation(effect, b'opacity')
            anim.setDuration(600 + i * 80)
            anim.setStartValue(1.0)
            anim.setEndValue(0.3)
            anim.setEasingCurve(QEasingCurve.InOutSine)
            anim.setLoopCount(-1)
            self._bar_anims.append(anim)

    def showEvent(self, event):
        super().showEvent(event)
        for anim in self._bar_anims:
            anim.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        for anim in self._bar_anims:
            anim.stop()
