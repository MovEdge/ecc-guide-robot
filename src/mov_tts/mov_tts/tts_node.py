"""
`/tts/speak`으로 들어오는 텍스트를 Gemini TTS로 합성해서 스피커로 재생한다.

원래 계획(TEAM.md/SESSION_LOG)은 "룰베이스 mp3 재생" 정도라 별도 패키지 없이
mov_ui가 흡수하기로 했었으나(2026-08-중), 실제 목적지명 등 상황에 따라 달라지는
문장을 말해야 해서(예: "OO로 안내를 시작합니다") 고정 mp3로는 부족함 —
Gemini TTS로 임의 텍스트를 그때그때 합성하는 것으로 재도입(2026-09-02).

Gemini TTS는 `client.models.generate_content`가 아니라 `client.interactions.create`
(Interactions API)로 호출한다 — 이 레포에서 LLM 호출에 쓰던 방식과 다르니 주의.
`generation_config.speech_config`는 dict가 아니라 **리스트**로 넘겨야 함
(`[{"voice": ...}]`) — dict로 넘기면 400 에러. 응답의 `output_audio`는 24kHz
mono 16bit PCM을 base64로 담고 있어서, WAV로 감싸 `aplay`로 재생한다(추가
오디오 라이브러리 의존성 없이 이미 설치돼 있는 ALSA CLI만 사용).

캐싱(2026-09-02, 실기 end-to-end 테스트 중 추가): 실기에서 매 발화마다
API 왕복(6~8초, 가끔 그 이상)이 그대로 지연으로 드러남 — 반면 실제 발화
문구는 "도착했습니다"(완전 고정) + "OO(로/으로) 안내를 시작합니다"(장소명만
바뀌는 템플릿, 후보는 `landmarks.csv` 수십 개뿐)라 사실상 종류가 유한함.
그래서 (모델, 보이스, 텍스트) 조합을 키로 합성 결과 WAV를 `TTS_CACHE_DIR`에
영구 캐싱 — 같은 문장이 다시 들어오면 API 호출 없이 캐시 파일을 바로 재생해
지연이 거의 없어진다. 새로운 문장은 여전히 처음 한 번은 API 호출이 필요함.
캐시 파일은 임시 경로에 완성한 뒤 `os.replace`로 최종 위치에 원자적으로
옮긴다 — 합성 중 실패해도 손상된 파일이 캐시로 남아 다음 요청까지 계속
깨진 채로 재생 시도되는 일이 없게 하기 위함.
"""
import base64
import hashlib
import os
import subprocess
import tempfile
import wave

from dotenv import load_dotenv
from google import genai

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

# 실측(2026-09-02): gemini-3.5-flash-lite 등 텍스트 모델과 별도로, TTS 전용
# preview 모델을 써야 함. 최신 모델로 조용히 바뀌는 걸 막기 위해 latest 별칭
# 대신 버전 고정 — resolver_core.py의 GEMINI_MODEL과 동일한 이유/패턴.
TTS_MODEL = os.environ.get('TTS_MODEL', 'gemini-3.1-flash-tts-preview')
# 사용 가능한 prebuilt voice 목록(공식 문서): Kore, Puck, Charon, Fenrir, Leda,
# Orus, Aoede, Callirrhoe, Autonoe, Enceladus, Iapetus, Umbriel, Algieba,
# Despina, Erinome, Algenib, Rasalgethi, Laomedeia, Achernar, Alnilam,
# Schedar, Gacrux, Pulcherrima, Achird, Zubenelgenubi, Vindemiatrix,
# Sadachbia, Sadaltager, Sulafat, Zephyr. 한국어 텍스트로 실제 테스트해 정상
# 합성됨을 확인함(언어는 입력 텍스트 기준 자동 인식, voice는 음색만 결정).
TTS_VOICE = os.environ.get('TTS_VOICE', 'Kore')
# 이 로봇엔 ALSA 카드가 여러 개 잡힘(ReSpeaker, Jetson 내장 HDMI/APE 등,
# `aplay -l` 참고) — 소리는 디스플레이(HDMI 오디오)로 나와야 하는데 aplay
# 기본 장치가 그쪽이 아닐 수 있어서, 확인되면 예: "plughw:1,3" 같은 값으로
# 지정. 비워두면 ALSA 기본 장치로 재생(맞을 수도, 아닐 수도 있음).
TTS_AUDIO_DEVICE = os.environ.get('TTS_AUDIO_DEVICE', '')
# 합성 WAV 영구 캐시 경로. 컨테이너 재생성 시에도 남아있길 바라면 워크스페이스
# 마운트 아래(예: /workspace/ecc-guide-robot/cache) 쪽으로 지정.
TTS_CACHE_DIR = os.environ.get(
    'TTS_CACHE_DIR', os.path.join(os.path.expanduser('~'), '.cache', 'mov_tts'))


def cache_path(text: str) -> str:
    key = f'{TTS_MODEL}|{TTS_VOICE}|{text}'
    digest = hashlib.sha256(key.encode('utf-8')).hexdigest()[:20]
    return os.path.join(TTS_CACHE_DIR, f'{digest}.wav')


def ensure_cached(client, text: str, log=lambda msg: None) -> str:
    """text의 캐시 WAV 경로를 반환, 없으면 합성해서 캐싱한 뒤 반환.

    tts_node.on_speak과 캐시 예열 스크립트(scripts/prewarm_cache.py)가
    같은 로직을 공유해 둘 사이에 캐시 키/합성 방식이 어긋나지 않게 한다.
    """
    wav_path = cache_path(text)
    if os.path.exists(wav_path):
        log(f'캐시 재생: "{text}"')
        return wav_path

    os.makedirs(TTS_CACHE_DIR, exist_ok=True)
    log(f'합성 요청: "{text}"')
    interaction = client.interactions.create(
        model=TTS_MODEL,
        input=text,
        response_format={'type': 'audio'},
        generation_config={'speech_config': [{'voice': TTS_VOICE}]},
    )

    audio = interaction.output_audio
    pcm = base64.b64decode(audio.data)
    # 합성 도중 실패해도 캐시 자리에 손상된 파일이 남지 않도록,
    # 임시 파일에 완성한 뒤 원자적으로 캐시 경로로 옮긴다.
    tmp_path = os.path.join(
        tempfile.gettempdir(), f'mov_tts_{os.getpid()}_{hashlib.sha256(text.encode()).hexdigest()[:8]}.wav')
    with wave.open(tmp_path, 'wb') as wf:
        wf.setnchannels(audio.channels)
        wf.setsampwidth(2)  # 16bit PCM 고정 (mime_type이 항상 audio/l16)
        wf.setframerate(audio.sample_rate)
        wf.writeframes(pcm)
    os.replace(tmp_path, wav_path)
    return wav_path


class TtsNode(Node):

    def __init__(self):
        super().__init__('tts_node')
        load_dotenv()

        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            self.get_logger().error(
                'GEMINI_API_KEY가 설정되지 않음 — .env 파일을 확인하세요')
            raise RuntimeError(
                'GEMINI_API_KEY 미설정: tts_node를 실행하려면 '
                '.env에 GEMINI_API_KEY를 설정해야 함')
        self.client = genai.Client(api_key=api_key)

        os.makedirs(TTS_CACHE_DIR, exist_ok=True)

        self.create_subscription(String, '/tts/speak', self.on_speak, 10)
        self.get_logger().info('TTS Node 준비 완료')

    def on_speak(self, msg: String):
        text = msg.data
        if not text:
            return

        try:
            wav_path = ensure_cached(self.client, text, log=self.get_logger().info)
        except Exception as e:
            self.get_logger().error(f'TTS 합성 실패: {e}')
            return

        # subprocess.run으로 블로킹 재생해서, 다음 발화 요청이 재생 중간에
        # 겹쳐 끊기지 않게 함(ROS2 기본 단일 스레드 executor라 콜백이 끝나야
        # 다음 메시지를 처리하므로 자연히 순차 재생됨).
        cmd = ['aplay']
        if TTS_AUDIO_DEVICE:
            cmd += ['-D', TTS_AUDIO_DEVICE]
        cmd.append(wav_path)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            self.get_logger().error(f'오디오 재생 실패: {result.stderr.strip()}')


def main(args=None):
    rclpy.init(args=args)
    node = TtsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
