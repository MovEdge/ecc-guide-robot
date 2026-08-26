from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton

from mov_ui.styles import SCREEN_W, SCREEN_H, DANGER, make_blob, apply_shadow
from mov_ui.i18n import i18n


class ErrorPage(QWidget):
    """ERROR — 에러 메시지, 재시도."""

    def __init__(self, on_retry_clicked):
        super().__init__()
        self.setObjectName('ErrorPage')

        blob = make_blob(self, 260, 'rgba(214, 69, 80, {a})', alpha=0.14)
        blob.move((SCREEN_W - 260) // 2, 90)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(220, 80, 220, 70)
        layout.setSpacing(16)
        layout.addStretch(1)

        icon = QLabel('⚠️')
        icon.setObjectName('IconLabel')
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        title = QLabel(i18n.t('error.title'))
        title.setObjectName('TitleLabel')
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(6)

        self.message_label = QLabel('')
        self.message_label.setObjectName('ErrorCard')
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignCenter)
        apply_shadow(self.message_label, blur=30, color=(214, 69, 80, 60), offset=(0, 8))
        layout.addWidget(self.message_label)

        layout.addStretch(1)

        retry_button = QPushButton(i18n.t('error.retry'))
        retry_button.setFixedHeight(76)
        retry_button.clicked.connect(on_retry_clicked)
        layout.addWidget(retry_button)

        i18n.register(lambda: (
            title.setText(i18n.t('error.title')),
            retry_button.setText(i18n.t('error.retry')),
        ))

    def set_message(self, text):
        self.message_label.setText(text)
