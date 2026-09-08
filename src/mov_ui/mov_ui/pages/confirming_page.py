from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from mov_ui.styles import SCREEN_W, SCREEN_H, PRIMARY_SOFT_RGBA, LEAF_SOFT_RGBA, make_blob, apply_shadow
from mov_ui.i18n import i18n


class ConfirmingPage(QWidget):
    """CONFIRMING — 인식 결과 확인/다시말하기."""

    def __init__(self, on_confirm_clicked, on_retry_clicked):
        super().__init__()
        self.setObjectName('ConfirmingPage')

        blob1 = make_blob(self, 420, PRIMARY_SOFT_RGBA, alpha=0.25)
        blob1.move(-140, 60)
        blob2 = make_blob(self, 300, LEAF_SOFT_RGBA, alpha=0.28)
        blob2.move(SCREEN_W - 200, SCREEN_H - 240)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(160, 70, 160, 70)
        layout.setSpacing(20)
        layout.addStretch(1)

        eyebrow = QLabel(i18n.t('confirming.eyebrow'))
        eyebrow.setObjectName('Eyebrow')
        eyebrow.setAlignment(Qt.AlignCenter)
        layout.addWidget(eyebrow)

        title = QLabel(i18n.t('confirming.title'))
        title.setObjectName('TitleLabel')
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(10)

        self.result_label = QLabel('')
        self.result_label.setObjectName('ResultCard')
        self.result_label.setWordWrap(True)
        self.result_label.setAlignment(Qt.AlignCenter)
        apply_shadow(self.result_label, blur=36, offset=(0, 10))
        layout.addWidget(self.result_label)

        layout.addStretch(1)

        button_row = QHBoxLayout()
        button_row.setSpacing(20)

        retry_button = QPushButton(i18n.t('confirming.retry'))
        retry_button.setProperty('type', 'secondary')
        retry_button.setFixedHeight(98)
        retry_button.clicked.connect(on_retry_clicked)
        button_row.addWidget(retry_button)

        confirm_button = QPushButton(i18n.t('confirming.confirm'))
        confirm_button.setProperty('type', 'confirm')
        confirm_button.setFixedHeight(98)
        confirm_button.clicked.connect(on_confirm_clicked)
        apply_shadow(confirm_button, blur=26, color=(93, 138, 58, 100), offset=(0, 6))
        button_row.addWidget(confirm_button)

        layout.addLayout(button_row)

        i18n.register(lambda: (
            eyebrow.setText(i18n.t('confirming.eyebrow')),
            title.setText(i18n.t('confirming.title')),
            retry_button.setText(i18n.t('confirming.retry')),
            confirm_button.setText(i18n.t('confirming.confirm')),
        ))

    def set_text(self, text):
        self.result_label.setText(f'"{text}"')

        # 문장이 길수록 줄바꿈이 늘어나 화면(고정 800px 높이) 밖으로
        # 넘칠 수 있어서, 글자 수에 따라 폰트 크기를 단계적으로 줄인다.
        length = len(text)
        if length <= 12:
            size = 65
        elif length <= 24:
            size = 48
        else:
            size = 36
        self.result_label.setStyleSheet(f'font-size: {size}px;')
