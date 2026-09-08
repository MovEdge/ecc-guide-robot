"""
UI/STT/목적지해석 체인을 한 번에 띄운다: mov_stt + mov_dest_resolver + mov_ui.
Nav2는 포함하지 않음 — 소프트웨어 체인만 따로 켜서 UI/STT/목적지해석을
개발/디버그할 때 쓰는 용도 (로봇 하드웨어 없이도 실행 가능). Nav2까지 포함한
실제 사용자용 end-to-end 진입점은 full_system.launch.py 참고.

mov_fsm(배회) 비활성화(2026-09-01) — mapjh.pgm 중앙 복도가 unknown으로 비어있는
지도 문제 때문에 배회가 계속 플래닝 실패를 반복해서 일단 뺐다. 패키지 자체는
src/mov_fsm/에 그대로 있음 — 지도 문제 해결되면 아래 Node 블록만 다시 추가하면 됨.

mov_tts(2026-09-02 추가) — `/tts/speak`(std_msgs/String)로 받은 텍스트를 Gemini
TTS로 합성해 재생. mov_ui가 목적지 해석 성공/도착 시 자동으로 발행하도록
와이어링됨(2026-09-02, 최가 임시 구현 — 문구/타이밍은 곽 UX 결정 대기,
src/mov_tts/CLAUDE.md 참고). 수동 테스트도 여전히 가능:
    ros2 topic pub -1 /tts/speak std_msgs/msg/String "{data: '화장실로 안내를 시작합니다'}"

실행 전:
  - 워크스페이스 빌드/소싱 (colcon build --symlink-install && source install/setup.bash)
  - mov_ui는 화면이 필요함: export DISPLAY=:1 (물리 터치스크린 X서버)
  - mov_dest_resolver/mov_tts는 .env에 GEMINI_API_KEY 필요

    export DISPLAY=:1
    ros2 launch /workspace/ecc-guide-robot/launch/app.launch.py
"""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="mov_stt",
            executable="stt_node",
            name="stt_node",
            output="screen",
        ),
        Node(
            package="mov_dest_resolver",
            executable="dest_resolver_node",
            name="dest_resolver_node",
            output="screen",
        ),
        Node(
            package="mov_ui",
            executable="ui_node",
            name="ui_node",
            output="screen",
        ),
        Node(
            package="mov_tts",
            executable="tts_node",
            name="tts_node",
            output="screen",
            # 실기 확인(2026-09-02): HDA 카드의 device 3(HDMI 0)이 디스플레이
            # 오디오 출력. 지정 안 하면 ALSA 기본 장치(ReSpeaker일 수 있음)로
            # 재생돼 디스플레이에서 소리가 안 날 수 있음. 카드 번호(hw:N,3)가
            # 아니라 카드 이름(CARD=HDA)으로 지정 — USB 허브 유무 등으로 카드
            # 번호가 밀리는 걸 2026-09-03 실기에서 확인함(mov_stt/stt_node.py의
            # STT_AUDIO_DEVICE 주석 참고, 같은 이유).
            additional_env={"TTS_AUDIO_DEVICE": "plughw:CARD=HDA,DEV=3"},
        ),
    ])
