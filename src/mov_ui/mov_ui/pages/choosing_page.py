from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea

from mov_ui.styles import SCREEN_W, SCREEN_H, PRIMARY_SOFT_RGBA, LEAF_SOFT_RGBA, make_blob
from mov_ui.i18n import i18n, localize_category, localize_place_name


class ChoosingPage(QWidget):
    """
    CHOOSING — 카테고리 후보가 여럿이라 사용자가 직접 골라야 하는 화면.

    (예: "카페 가고 싶어" → DB에 카페가 3곳 → 로봇이 임의로 하나를 고르지 않고
    전부 버튼으로 보여주고 탭하게 함. 후보 목록은 dest_resolver가 정해서 보내줌.)
    """

    def __init__(self, on_choice_clicked, on_cancel_clicked):
        super().__init__()
        self.setObjectName('ChoosingPage')
        self._on_choice_clicked = on_choice_clicked

        blob1 = make_blob(self, 420, PRIMARY_SOFT_RGBA, alpha=0.25)
        blob1.move(-140, 60)
        blob2 = make_blob(self, 300, LEAF_SOFT_RGBA, alpha=0.28)
        blob2.move(SCREEN_W - 200, SCREEN_H - 240)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(140, 60, 140, 50)
        layout.setSpacing(16)

        eyebrow = QLabel(i18n.t('choosing.eyebrow'))
        eyebrow.setObjectName('Eyebrow')
        eyebrow.setAlignment(Qt.AlignCenter)
        layout.addWidget(eyebrow)

        self.title_label = QLabel('')
        self.title_label.setObjectName('TitleLabel')
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet('font-size: 56px;')
        layout.addWidget(self.title_label)

        layout.addSpacing(8)

        self._list_layout = QVBoxLayout()
        self._list_layout.setSpacing(14)

        list_container = QWidget()
        list_container.setStyleSheet('background: transparent;')
        list_container.setLayout(self._list_layout)

        # 후보 개수가 화면에 다 안 들어갈 수 있어 스크롤로 감싼다
        # (지금 최대 사례는 화장실 5개지만, 카테고리 데이터가 늘어나도 안전하게).
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet('background: transparent; border: none;')
        scroll.setWidget(list_container)
        layout.addWidget(scroll, 1)

        cancel_button = QPushButton(i18n.t('choosing.cancel'))
        cancel_button.setProperty('type', 'secondary')
        cancel_button.setFixedHeight(90)
        cancel_button.clicked.connect(on_cancel_clicked)
        layout.addWidget(cancel_button)

        self._category = ''

        i18n.register(lambda: (
            eyebrow.setText(i18n.t('choosing.eyebrow')),
            cancel_button.setText(i18n.t('choosing.cancel')),
            self._update_title(),
        ))

    def _update_title(self):
        category = localize_category(self._category)
        self.title_label.setText(i18n.t('choosing.title').format(category=category))

    def set_choices(self, category: str, place_names: list):
        self._category = category
        self._update_title()

        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for name in place_names:
            # 표시 텍스트만 로컬라이즈하고, 탭했을 때 되돌려주는 값(n)은
            # dest_resolver가 DB에서 그대로 매칭할 원본 이름을 써야 하므로
            # 건드리지 않는다.
            button = QPushButton(localize_place_name(name))
            button.setProperty('type', 'secondary')
            button.setFixedHeight(90)
            # 클로저가 마지막 name을 공유하지 않도록 기본 인자로 캡처.
            button.clicked.connect(lambda _checked, n=name: self._on_choice_clicked(n))
            self._list_layout.addWidget(button)
