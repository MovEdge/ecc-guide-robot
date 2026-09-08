import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from mov_ui.styles import SCREEN_W, SCREEN_H, PRIMARY_SOFT_RGBA, LEAF_SOFT_RGBA, make_blob, apply_shadow
from mov_ui.i18n import i18n

_ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
_MASCOT_PATH = os.path.join(_ASSET_DIR, 'mascot_face.png')


class ArrivedPage(QWidget):
    """ARRIVED — 도착 안내, 새 장소 안내/처음으로."""

    def __init__(self, on_new_destination_clicked, on_home_clicked):
        super().__init__()
        self.setObjectName('ArrivedPage')

        blob1 = make_blob(self, 500, LEAF_SOFT_RGBA, alpha=0.30)
        blob1.move((SCREEN_W - 500) // 2, -180)
        blob2 = make_blob(self, 220, PRIMARY_SOFT_RGBA, alpha=0.28)
        blob2.move(140, SCREEN_H - 260)
        blob3 = make_blob(self, 160, PRIMARY_SOFT_RGBA, alpha=0.25)
        blob3.move(SCREEN_W - 220, SCREEN_H - 180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(80, 50, 80, 60)
        layout.setSpacing(14)
        layout.addStretch(1)

        mascot = QLabel()
        mascot.setAlignment(Qt.AlignCenter)
        mascot.setStyleSheet('background: transparent;')
        if os.path.exists(_MASCOT_PATH):
            pixmap = QPixmap(_MASCOT_PATH)
            mascot.setPixmap(
                pixmap.scaledToWidth(220, Qt.SmoothTransformation))
        else:
            mascot.setText('🎉')
            mascot.setObjectName('IconLabel')
        layout.addWidget(mascot, alignment=Qt.AlignCenter)

        self.message_label = QLabel(i18n.t('arrived.title'))
        self.message_label.setObjectName('TitleLabel')
        self.message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.message_label)

        subtitle = QLabel(i18n.t('arrived.subtitle'))
        subtitle.setObjectName('SubtitleLabel')
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addStretch(1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.setSpacing(20)

        home_button = QPushButton(i18n.t('arrived.home'))
        home_button.setProperty('type', 'secondary')
        home_button.setFixedHeight(98)
        home_button.setMinimumWidth(240)
        home_button.clicked.connect(on_home_clicked)
        button_row.addWidget(home_button)

        new_destination_button = QPushButton(i18n.t('arrived.new_destination'))
        new_destination_button.setProperty('type', 'confirm')
        new_destination_button.setFixedHeight(98)
        new_destination_button.setMinimumWidth(240)
        new_destination_button.clicked.connect(on_new_destination_clicked)
        apply_shadow(new_destination_button, blur=26, color=(93, 138, 58, 100), offset=(0, 6))
        button_row.addWidget(new_destination_button)
        button_row.addStretch(1)

        layout.addLayout(button_row)

        # 도착 메시지는 set_message로 덮어써질 수도 있어 기본 문구만 언어 전환 대상으로 등록
        self._using_default_message = True

        def _on_lang_change():
            if self._using_default_message:
                self.message_label.setText(i18n.t('arrived.title'))
            subtitle.setText(i18n.t('arrived.subtitle'))
            home_button.setText(i18n.t('arrived.home'))
            new_destination_button.setText(i18n.t('arrived.new_destination'))

        i18n.register(_on_lang_change)
