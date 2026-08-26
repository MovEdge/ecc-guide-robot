from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton

from mov_ui.styles import SCREEN_W, SCREEN_H, PRIMARY_SOFT_RGBA, LEAF_SOFT_RGBA, make_blob, apply_shadow
from mov_ui.i18n import i18n


class NavigatingPage(QWidget):
    """NAVIGATING — 목적지명/진행상태/남은거리/취소버튼.

    Nav2 진행 상태 토픽은 아직 INTERFACES.md에 정의 안 됨 —
    가운데 경로 표시는 지금은 장식용 정적 일러스트이고,
    on_cancel_clicked도 자리만 잡아둔 콜백.
    진행상태/남은거리 텍스트는 nav_node가 보내주는 실제 데이터라 여기선 번역하지 않음.
    """

    def __init__(self, on_cancel_clicked):
        super().__init__()
        self.setObjectName('NavigatingPage')

        blob1 = make_blob(self, 460, PRIMARY_SOFT_RGBA, alpha=0.22)
        blob1.move(SCREEN_W - 300, -160)
        blob2 = make_blob(self, 260, LEAF_SOFT_RGBA, alpha=0.28)
        blob2.move(-100, SCREEN_H - 220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(140, 70, 140, 60)
        layout.setSpacing(14)
        layout.addStretch(1)

        eyebrow = QLabel(i18n.t('navigating.eyebrow'))
        eyebrow.setObjectName('Eyebrow')
        eyebrow.setAlignment(Qt.AlignCenter)
        layout.addWidget(eyebrow)

        self.destination_label = QLabel('')
        self.destination_label.setObjectName('TitleLabel')
        self.destination_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.destination_label)

        layout.addSpacing(24)

        # ── 경로 일러스트: 출발 🤖 ---- 🚩 도착 ──
        route_row = QHBoxLayout()
        route_row.setSpacing(0)
        start_icon = QLabel('🤖')
        start_icon.setObjectName('RouteEmoji')
        route_row.addWidget(start_icon)

        line = QLabel()
        line.setObjectName('RouteLine')
        line.setFixedHeight(6)
        route_row.addWidget(line, 1)

        end_icon = QLabel('🚩')
        end_icon.setObjectName('RouteEmoji')
        route_row.addWidget(end_icon)
        layout.addLayout(route_row)

        layout.addSpacing(20)

        badge_row = QHBoxLayout()
        badge_row.addStretch(1)
        self.progress_label = QLabel('')
        self.progress_label.setObjectName('ProgressBadge')
        badge_row.addWidget(self.progress_label)
        badge_row.addStretch(1)
        layout.addLayout(badge_row)

        self.remaining_label = QLabel('')
        self.remaining_label.setObjectName('RemainingLabel')
        self.remaining_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.remaining_label)

        layout.addStretch(1)

        cancel_button = QPushButton(i18n.t('navigating.cancel'))
        cancel_button.setProperty('type', 'danger')
        cancel_button.setFixedHeight(72)
        cancel_button.clicked.connect(on_cancel_clicked)
        layout.addWidget(cancel_button)

        i18n.register(lambda: (
            eyebrow.setText(i18n.t('navigating.eyebrow')),
            cancel_button.setText(i18n.t('navigating.cancel')),
        ))

    def set_destination(self, name):
        self.destination_label.setText(name)

    def set_progress(self, progress_text):
        self.progress_label.setText(progress_text)

    def set_remaining(self, remaining_text):
        self.remaining_label.setText(remaining_text)
