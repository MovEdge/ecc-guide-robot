"""
mov_ui 화면 7종을 실제 ROS 스택(mov_stt/mov_dest_resolver/mov_fsm/mov_tts) 없이
캡처하는 스크립트. ui_node.py를 거치지 않고 MainWindow를 직접 만들어서,
ui_node가 ROS 콜백에서 하던 것과 동일한 setter 호출(set_text/set_choices/...)만
더미 값으로 흉내낸다 — end-to-end 실행 없이 화면 모양만 보기 위함.

실행: python3 docs/ui_screens/capture_ui.py
(리포 루트에서 실행. PyQt5만 있으면 되고 rclpy는 필요 없음.)
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO_ROOT, 'src', 'mov_ui'))

from PyQt5.QtWidgets import QApplication
from mov_ui.main_window import MainWindow
from mov_ui.styles import STYLESHEET
from mov_ui.i18n import i18n

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

app = QApplication(sys.argv)
app.setStyleSheet(STYLESHEET)

noop_callbacks = {
    'on_speak_clicked': lambda: None,
    'on_confirm_clicked': lambda: None,
    'on_retry_clicked': lambda: None,
    'on_choice_clicked': lambda place_name: None,
    'on_listening_cancel_clicked': lambda: None,
    'on_cancel_clicked': lambda: None,
    'on_new_destination_clicked': lambda: None,
    'on_home_clicked': lambda: None,
}

window = MainWindow(noop_callbacks)
window.show()  # offscreen platform이라 실제 창은 안 뜨지만 레이아웃 계산엔 필요


def capture(state, filename, setup=None):
    if setup:
        setup()
    window.set_state(state)
    app.processEvents()
    pixmap = window.grab()
    path = os.path.join(OUT_DIR, filename)
    pixmap.save(path, 'PNG')
    print(f'saved {path}')


capture('IDLE', '1_idle.png')

capture('LISTENING', '2_listening.png')

capture('CONFIRMING', '3_confirming.png',
        lambda: window.confirming_page.set_text('카페 가는 길 알려줘'))

# landmarks.csv(slam/slam_frommap/out3/landmarks.csv)에 실제로 있는 카페 3곳 그대로 사용
capture('CHOOSING', '4_choosing.png',
        lambda: window.choosing_page.set_choices(
            '카페', ['1847 카페(1847 CAFE)', '뚜레쥬르(TOUS LES JOURS)', '스타벅스(썬큰가든)(STARBUCKS)']))

def _setup_navigating():
    window.navigating_page.set_destination('1847 카페(1847 CAFE)')
    window.navigating_page.set_remaining('42%')
    window.navigating_page.set_progress_percent(42)

capture('NAVIGATING', '5_navigating.png', _setup_navigating)

capture('ARRIVED', '6_arrived.png')

capture('ERROR', '7_error.png',
        lambda: window.error_page.set_message('장소를 찾을 수 없어요. 다시 말씀해 주세요.'))

# 영어 버전도 하나(IDLE)만 추가로 — 언어 토글이 실제로 동작하는지 같이 보여줌
i18n.toggle()
window.lang_button.setText(window._lang_label())
capture('IDLE', '8_idle_en.png')

print('done')
