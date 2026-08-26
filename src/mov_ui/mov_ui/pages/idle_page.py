import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)

from mov_ui.styles import (
    SCREEN_W, SCREEN_H, PRIMARY_SOFT_RGBA, LEAF_SOFT_RGBA,
    apply_shadow, make_blob,
)
from mov_ui.i18n import i18n

_ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
_MASCOT_PATH = os.path.join(_ASSET_DIR, 'mascot_face.png')


class IdlePage(QWidget):
    """IDLE — 대기 화면. 좌측 마스코트 + 우측 안내문/버튼의 2단 레이아웃."""

    def __init__(self, on_speak_clicked):
        super().__init__()
        self.setObjectName('IdlePage')

        # ── 장식용 블롭 (배경 입체감) ──
        blob1 = make_blob(self, 520, PRIMARY_SOFT_RGBA, alpha=0.30)
        blob1.move(-160, -140)
        blob2 = make_blob(self, 320, LEAF_SOFT_RGBA, alpha=0.30)
        blob2.move(SCREEN_W - 220, SCREEN_H - 220)

        root = QHBoxLayout(self)
        root.setContentsMargins(80, 60, 80, 60)
        root.setSpacing(40)

        # ── 좌측: 마스코트 ──
        left = QVBoxLayout()
        left.addStretch(1)
        mascot = QLabel()
        mascot.setAlignment(Qt.AlignCenter)
        mascot.setStyleSheet('background: transparent;')
        if os.path.exists(_MASCOT_PATH):
            pixmap = QPixmap(_MASCOT_PATH)
            mascot.setPixmap(
                pixmap.scaledToWidth(380, Qt.SmoothTransformation))
        else:
            mascot.setText('🍃')
            mascot.setObjectName('IconLabel')
        left.addWidget(mascot, alignment=Qt.AlignCenter)
        left.addStretch(1)
        root.addLayout(left, 45)

        # ── 우측: 안내문 + 버튼 ──
        right = QVBoxLayout()
        right.setSpacing(18)
        right.addStretch(1)

        eyebrow = QLabel(i18n.t('app.name'))
        eyebrow.setObjectName('Eyebrow')
        right.addWidget(eyebrow)

        title = QLabel(i18n.t('idle.title'))
        title.setObjectName('TitleLabel')
        title.setWordWrap(True)
        right.addWidget(title)

        subtitle = QLabel(i18n.t('idle.subtitle'))
        subtitle.setObjectName('SubtitleLabel')
        right.addWidget(subtitle)

        right.addSpacing(20)

        speak_button = QPushButton(f"🎤   {i18n.t('idle.speak_button')}")
        speak_button.setFixedSize(360, 92)
        speak_button.clicked.connect(on_speak_clicked)
        apply_shadow(speak_button, blur=30, color=(96, 104, 178, 110), offset=(0, 8))
        right.addWidget(speak_button)

        right.addStretch(2)
        root.addLayout(right, 55)

        i18n.register(lambda: (
            eyebrow.setText(i18n.t('app.name')),
            title.setText(i18n.t('idle.title')),
            subtitle.setText(i18n.t('idle.subtitle')),
            speak_button.setText(f"🎤   {i18n.t('idle.speak_button')}"),
        ))
