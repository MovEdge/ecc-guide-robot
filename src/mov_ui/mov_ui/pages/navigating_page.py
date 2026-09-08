import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QPushButton

from mov_ui.styles import (
    SCREEN_W, SCREEN_H, LEAF_DARK, PRIMARY_SOFT_RGBA, LEAF_SOFT_RGBA, make_blob,
)
from mov_ui.i18n import i18n, localize_place_name

_ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
# mascot.png(정면/뒷모습 시트)는 알파값이 전부 255라 실제로는 투명 배경이
# 아니었다 — 잘라 쓰면 흰 네모가 그대로 남는 문제가 있어서, idle/arrived
# 화면에서 이미 쓰고 있는 진짜 투명 PNG인 mascot_face.png를 그대로 재사용.
_MASCOT_PATH = os.path.join(_ASSET_DIR, 'mascot_face.png')
_MASCOT_SIZE = 72


class RouteTrack(QWidget):
    """출발지 ──── 도착지 진행 트랙.

    예전엔 출발/도착 자리에 색깔 원(●) 두 개만 고정으로 떠 있었는데,
    사용자 요청으로 도착지 표시는 작은 점 하나만 남기고 출발지 쪽 원은
    없애는 대신 마스코트가 set_percent()로 받은 진행률만큼 트랙을 따라
    왼쪽→오른쪽으로 움직인다. 화면이 showFullScreen 키오스크라 크기가
    안 바뀌긴 하지만, 그래도 폭에 의존해 위치를 계산해야 해서 절대좌표
    (move)로 배치하고 resizeEvent에서 다시 계산한다.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(_MASCOT_SIZE + 16)
        self._percent = 0.0

        self.line = QLabel(self)
        self.line.setObjectName('RouteLine')

        self.end_marker = QFrame(self)
        self.end_marker.setFixedSize(20, 20)
        self.end_marker.setStyleSheet(f'background-color: {LEAF_DARK}; border-radius: 10px;')

        self.mascot = QLabel(self)
        self.mascot.setStyleSheet('background: transparent;')
        if os.path.exists(_MASCOT_PATH):
            pixmap = QPixmap(_MASCOT_PATH)
            self.mascot.setPixmap(pixmap.scaledToHeight(_MASCOT_SIZE, Qt.SmoothTransformation))
            self.mascot.setFixedSize(self.mascot.pixmap().size())
        else:
            self.mascot.setText('🍃')
            self.mascot.setObjectName('IconLabel')
            self.mascot.setFixedSize(_MASCOT_SIZE, _MASCOT_SIZE)
            self.mascot.setAlignment(Qt.AlignCenter)
        self.mascot.raise_()

        self._layout_children()

    def resizeEvent(self, event):
        self._layout_children()
        super().resizeEvent(event)

    def set_percent(self, percent):
        self._percent = max(0.0, min(100.0, percent))
        self._layout_children()

    def _layout_children(self):
        w = self.width()
        mid_y = self.height() // 2

        self.line.setGeometry(0, mid_y - 3, w, 6)

        marker_r = self.end_marker.width() // 2
        self.end_marker.move(w - self.end_marker.width(), mid_y - marker_r)

        travel = max(0, w - self.mascot.width())
        x = int(travel * (self._percent / 100.0))
        self.mascot.move(x, mid_y - self.mascot.height() // 2)


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
        self.destination_label.setWordWrap(True)
        layout.addWidget(self.destination_label)

        layout.addSpacing(24)

        # ── 경로 일러스트: 마스코트 🍃 ~~~~ ● 도착 ──
        # 예전엔 출발/도착 둘 다 색깔 원으로 표시했는데, 진행률에 따라
        # 마스코트가 직접 트랙을 따라 이동하는 쪽으로 교체 (RouteTrack 참고).
        self.route_track = RouteTrack()
        layout.addWidget(self.route_track)

        layout.addSpacing(20)

        self.remaining_label = QLabel('')
        self.remaining_label.setObjectName('RemainingLabel')
        self.remaining_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.remaining_label)

        layout.addStretch(1)

        cancel_button = QPushButton(i18n.t('navigating.cancel'))
        cancel_button.setProperty('type', 'danger')
        cancel_button.setFixedHeight(98)
        cancel_button.clicked.connect(on_cancel_clicked)
        layout.addWidget(cancel_button)

        i18n.register(lambda: (
            eyebrow.setText(i18n.t('navigating.eyebrow')),
            cancel_button.setText(i18n.t('navigating.cancel')),
        ))

    def set_destination(self, name):
        name = localize_place_name(name)
        self.destination_label.setText(name)
        self.route_track.set_percent(0)

        # "구시아 푸드마켓(GUSIA FOODMARKET)"처럼 긴 이름이 기본 81px에서
        # 화면 밖으로 넘치는 문제 — confirming_page.set_text와 동일한 패턴으로
        # 글자 수에 따라 단계적으로 줄인다.
        length = len(name)
        if length <= 8:
            size = 81
        elif length <= 16:
            size = 56
        else:
            size = 40
        self.destination_label.setStyleSheet(f'font-size: {size}px;')

    def set_remaining(self, remaining_text):
        self.remaining_label.setText(remaining_text)

    def set_progress_percent(self, percent):
        self.route_track.set_percent(percent)
