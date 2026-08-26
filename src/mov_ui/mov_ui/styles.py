"""
mov_ui 공통 디자인 토큰 / 스타일시트.
Waveshare 8DP-CAPLCD (1280x800, 가로) 기준으로 설계.

색상은 인지대 상징색(#6068B2)과 마스코트 '이아이'의 그린 톤을 기준으로 잡았다.
"""

from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsDropShadowEffect

SCREEN_W = 1280
SCREEN_H = 800

PRIMARY = '#6068B2'
PRIMARY_DARK = '#4B5399'
PRIMARY_LIGHT = '#E5E6F5'
PRIMARY_SOFT_RGBA = 'rgba(96, 104, 178, {a})'

LEAF_DARK = '#5D8A3A'
LEAF_DARKER = '#4C7530'
LEAF_LIGHT = '#AACB5D'
LEAF_BG = '#EEF4E3'
LEAF_SOFT_RGBA = 'rgba(122, 179, 66, {a})'

DANGER = '#D64550'
DANGER_DARK = '#B93540'
DANGER_BG = '#FBE9EA'

BACKGROUND = '#F7F7FA'
CARD_BG = '#FFFFFF'
TEXT_DARK = '#2E2E38'
TEXT_MUTED = '#6B6B76'
BORDER = '#E7E7F0'

PAGE_BG_GRADIENT = (
    f'qlineargradient(x1:0, y1:0, x2:1, y2:1, '
    f'stop:0 {PRIMARY_LIGHT}, stop:0.45 {BACKGROUND}, stop:1 #FFFFFF)'
)

STYLESHEET = f'''
QWidget {{
    background: {PAGE_BG_GRADIENT};
    font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
    color: {TEXT_DARK};
}}

QLabel#TitleLabel {{
    font-size: 54px;
    font-weight: 800;
    color: {TEXT_DARK};
    background: transparent;
}}

QLabel#SubtitleLabel {{
    font-size: 25px;
    color: {TEXT_MUTED};
    background: transparent;
}}

QLabel#Eyebrow {{
    font-size: 20px;
    font-weight: 700;
    color: {PRIMARY};
    background: transparent;
    letter-spacing: 2px;
}}

QLabel#ResultCard {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 24px;
    padding: 36px;
    font-size: 34px;
    font-weight: 600;
    color: {TEXT_DARK};
}}

QLabel#ErrorCard {{
    background-color: {DANGER_BG};
    border: 1px solid {DANGER};
    border-radius: 24px;
    padding: 32px;
    font-size: 27px;
    color: {DANGER_DARK};
}}

QLabel#ProgressBadge {{
    background-color: {PRIMARY};
    color: white;
    border-radius: 18px;
    padding: 10px 26px;
    font-size: 21px;
    font-weight: 700;
}}

QLabel#RemainingLabel {{
    font-size: 25px;
    color: {TEXT_MUTED};
    background: transparent;
}}

QLabel#IconLabel {{
    font-size: 84px;
    background: transparent;
}}

QLabel#RouteEmoji {{
    font-size: 36px;
    background: transparent;
}}

QLabel#RouteLine {{
    background-color: {PRIMARY_LIGHT};
    border-radius: 3px;
}}

QLabel#Blob {{
    border: none;
}}

QFrame#Card {{
    background-color: {CARD_BG};
    border-radius: 28px;
    border: 1px solid {BORDER};
}}

QPushButton#LangToggle {{
    background-color: rgba(46, 46, 56, 0.55);
    color: white;
    border: none;
    border-radius: 18px;
    padding: 8px 18px;
    font-size: 16px;
    font-weight: 700;
}}
QPushButton#LangToggle:hover {{
    background-color: rgba(46, 46, 56, 0.75);
}}

/* 기본(=primary) 버튼: 그라데이션 */
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {PRIMARY}, stop:1 {PRIMARY_DARK});
    color: white;
    border: none;
    border-radius: 20px;
    padding: 22px 36px;
    font-size: 26px;
    font-weight: 700;
}}
QPushButton:hover {{
    background: {PRIMARY_DARK};
}}
QPushButton:pressed {{
    background: {PRIMARY_DARK};
    padding-top: 24px;
}}

/* 보조(outline) 버튼 */
QPushButton[type="secondary"] {{
    background: {CARD_BG};
    color: {PRIMARY};
    border: 2px solid {PRIMARY};
}}
QPushButton[type="secondary"]:hover {{
    background-color: {PRIMARY_LIGHT};
}}

/* 확인/성공 버튼 (그린 그라데이션) */
QPushButton[type="confirm"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {LEAF_DARK}, stop:1 {LEAF_DARKER});
}}
QPushButton[type="confirm"]:hover {{
    background: {LEAF_DARKER};
}}

/* 취소/위험 버튼 */
QPushButton[type="danger"] {{
    background: {CARD_BG};
    color: {DANGER};
    border: 2px solid {DANGER};
}}
QPushButton[type="danger"]:hover {{
    background-color: {DANGER_BG};
}}
'''


def apply_shadow(widget, blur=40, color=(46, 46, 56, 70), offset=(0, 10)):
    """카드/버튼/뱃지 등에 은은한 그림자를 준다."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setColor(QColor(*color))
    effect.setOffset(*offset)
    widget.setGraphicsEffect(effect)
    return effect


def make_blob(parent, size, rgba_template, alpha=0.35):
    """장식용 원형 블롭(QLabel). 배경에 은은하게 깔아 화면에 입체감을 준다."""
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QLabel

    blob = QLabel(parent)
    blob.setObjectName('Blob')
    blob.setAttribute(Qt.WA_StyledBackground, True)
    color = rgba_template.format(a=alpha)
    blob.setStyleSheet(
        f'QLabel#Blob {{ background-color: {color}; '
        f'border-radius: {size // 2}px; }}'
    )
    blob.setFixedSize(size, size)
    blob.lower()
    return blob
