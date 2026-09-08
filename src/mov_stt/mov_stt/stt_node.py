import os
import select
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError

import numpy as np
import webrtcvad
from faster_whisper import WhisperModel

import rclpy
from rclpy.node import Node
from std_msgs.msg import Empty
from mov_interfaces.msg import SttResult

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000  # 480
FRAME_BYTES = FRAME_SAMPLES * 2  # int16 mono

# 말이 시작되기 전 최대 대기 시간(무음이면 실패 처리)
MAX_WAIT_FOR_SPEECH_SEC = 5.0
# 말이 시작된 뒤, 이만큼 연속 무음이면 발화 종료로 판단.
# 너무 짧으면 문장 중간 자연스러운 끊김에도 잘라버릴 위험이 있어 0.9로만
# 낮춤(기존 1.2) — 체감 지연의 더 큰 부분은 beam_size(_transcribe 참고)였음.
SILENCE_TO_STOP_SEC = 0.9
# 안전장치: 아무리 길어도 이 시간 넘으면 강제 종료
MAX_RECORDING_SEC = 15.0

# ReSpeaker에서 raw PCM을 그대로 뽑는 ALSA 장치. plughw로 채널/샘플레이트
# 변환을 ALSA에 맡긴다(tts_node의 TTS_AUDIO_DEVICE와 같은 이유 — 이 로봇의
# ReSpeaker는 원래 6채널 UAC1.0 장치라 raw hw로 1채널만 여는 게 항상 되리라는
# 보장이 없음).
#
# 카드 번호(hw:N,0)가 아니라 카드 이름(CARD=ArrayUAC10)으로 지정한다 —
# 2026-09-03 실기에서 ReSpeaker를 젯슨 USB 포트에 직결하지 않고 USB 허브를
# 거치게 배선을 바꾸자 카드 번호가 0→3으로 밀렸고, 번호로 고정해둔
# STT_AUDIO_DEVICE가 엉뚱한 장치(허브의 다른 USB 기기)를 잡아서 "말은
# 했는데 빈 문자열/이상한 결과만 나오는" 문제로 이어졌다(VAD는 그 장치의
# 신호에도 반응해 녹음 자체는 진행됐지만, Whisper엔 사람 음성이 아니었음).
# 카드 번호는 USB 꽂는 순서/허브 유무에 따라 바뀌지만 카드 이름은
# 드라이버가 고정으로 부여해서 안 바뀐다 — `arecord -l`으로 확인 가능.
STT_AUDIO_DEVICE = os.environ.get('STT_AUDIO_DEVICE', 'plughw:CARD=ArrayUAC10,DEV=0')
# 프레임(30ms) 하나 받는 데 이 시간 넘게 걸리면 마이크 스트림이 멈춘 것으로
# 보고 강제 종료한다. 원래 python-sounddevice의 블로킹 read()를 직접 썼는데
# 타임아웃이 없어서, 실기에서 시스템 부하로 오디오 스레드가 스케줄을 못
# 받으면(2026-09-03 실측 — RViz 등이 CPU를 많이 먹을 때 재현) read()가
# 영원히 안 끝나는 문제가 있었다. 15초 MAX_RECORDING_SEC 안전장치는 "루프를
# 몇 번 도는지"로 세는 거라 read() 자체가 멈추면 무력화되고, ROS2가 콜백
# 하나 끝나야 다음 메시지를 처리하는 구조라 이후 모든 "말하기" 트리거가
# 영원히 씹히는 결과로 이어졌다(취소 버튼도 UI 화면만 바꿀 뿐 이 상태는
# 못 끊음). subprocess(arecord)로 캡처를 옮기면, 멈췄을 때 프로세스를
# 강제 kill할 수 있어 콜백이 반드시 끝나는 걸 보장할 수 있다 — 스레드는
# 멈춘 네이티브 호출을 파이썬에서 안전하게 끊을 방법이 없지만, 별도
# 프로세스는 항상 죽일 수 있다.
FRAME_READ_TIMEOUT_SEC = 3.0

# Whisper 전사(_transcribe) 자체엔 타임아웃이 없어서, 특정 오디오(특히
# 실제 발화가 아니라 VAD가 배경 소음을 오탐지해 녹음된 경우)에서 몇 분씩
# 걸리는 걸 확인했다(2026-09-03 실기 재현, 234초 관측). 녹음(캡처) 쪽은
# subprocess+타임아웃으로 이미 막았지만, 이 단계가 막혀 있으면 사용자
# 입장에선 여전히 "말해도 화면이 안 넘어간다"와 똑같이 보인다. ctranslate2
# 네이티브 호출이라 스레드를 강제로 끊을 방법이 없어서(외부 프로세스로
# 옮기려면 매번 모델을 다시 로드해야 해 비용이 큼), 대신 스레드풀에 던지고
# 이 시간 안에 안 끝나면 결과를 포기하고 다음 요청을 받는다 — 버려진
# 스레드는 백그라운드에서 계속 CPU를 쓰며 돌지만(못 끊음), 콜백/노드
# 자체는 막히지 않는다. 실측된 정상 케이스(느려도 12~26초)는 다 통과하고
# 병적으로 오래 걸리는 케이스만 끊어내도록 여유 있게 잡음.
#
# 20초로 처음 잡았다가(2026-09-03) 실기 재테스트에서 정상 발화도 걸리는
# 걸 확인해서 40초로 올림 — 사용자가 재현한 로그에 25.6초 걸린 정상 성공
# 케이스가 있었는데(Nav2/RViz 등이 같이 CPU를 먹는 실제 end-to-end 상황),
# 20초는 그것도 잘라버림. 234초짜리 병적 케이스를 걸러내는 목적은 여전히
# 만족하면서, 정상 범위(느려도 수십 초)는 넉넉히 봐주도록 올렸다.
TRANSCRIBE_TIMEOUT_SEC = 40.0


def _read_exact(pipe, n, timeout_s):
    """timeout_s 안에 정확히 n바이트를 못 받으면 None(타임아웃 또는 EOF)."""
    buf = b''
    deadline = time.monotonic() + timeout_s
    while len(buf) < n:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        ready, _, _ = select.select([pipe], [], [], remaining)
        if not ready:
            return None
        chunk = os.read(pipe.fileno(), n - len(buf))
        if not chunk:  # EOF — arecord 프로세스가 죽음
            return None
        buf += chunk
    return buf


class SttNode(Node):

    def __init__(self):
        super().__init__('stt_node')
        self.get_logger().info('STT Node 시작 — Whisper 모델 로딩 중...')

        self.vad = webrtcvad.Vad(1)  # 0~3, 클수록 무음 판정에 엄격

        # 구독을 모델 로딩보다 먼저 만든다. 콜백은 spin() 시작 후에나 실행되니
        # (생성자가 끝나기 전엔 spin 자체가 안 돎) 로딩 중 안전성 문제는 없고,
        # 대신 로딩 중에 들어온 트리거도 DDS 큐에 쌓였다가 로딩 완료 후 처리된다.
        # 반대 순서(모델 로딩 후 구독 생성)면 로딩 중 트리거는 구독이 아예
        # 없어서 에러 없이 조용히 유실된다 — 실제로 이 순서 때문에 발생했던 버그.
        self.subscription = self.create_subscription(
            Empty, '/stt/start_listening', self.listener_callback, 10)
        self.publisher_ = self.create_publisher(SttResult, '/stt/result', 10)
        # 마이크 스트림이 실제로 열린 시점에 발행 — UI가 트리거를 보내자마자
        # "듣고 있어요" 화면으로 넘어가면, 아직 마이크가 열리기 전(장치 오픈
        # 지연, 혹은 모델 로딩 중이었다면 그 시간까지)인데도 화면만 먼저
        # 바뀌는 문제가 있어서 추가함. UI는 /stt/result가 아니라 이걸 보고
        # LISTENING으로 전환한다(mov_ui/ui_node.py 참고).
        self.listening_started_pub = self.create_publisher(
            Empty, '/stt/listening_started', 10)

        self.model = self._load_whisper_model()
        # _transcribe를 여기 던지고 TRANSCRIBE_TIMEOUT_SEC 안에 안 끝나면
        # 포기한다(위 상수 설명 참고). max_workers를 1보다 크게 둬서,
        # 포기한 스레드가 자리를 계속 차지해도 다음 전사가 새 워커를 받아
        # 진행할 수 있게 한다. 4 → 2로 낮춤(2026-09-03) — cpu_threads=2와
        # 곱하면 최악의 경우도 4스레드로 막혀서, 6코어 기기에서 load
        # average가 50 넘게 치솟아 재부팅까지 갔던 문제(위 _load_whisper_model
        # 주석 참고)의 재발을 줄인다.
        self._transcribe_pool = ThreadPoolExecutor(max_workers=2)

        self.get_logger().info('STT Node 준비 완료')

    def _load_whisper_model(self):
        try:
            model = WhisperModel('small', device='cuda', compute_type='float16')
            self.get_logger().info('Whisper small 모델을 CUDA로 로드함')
        except Exception as e:
            self.get_logger().warn(f'CUDA 로드 실패({e}), CPU로 재시도')
            # cpu_threads 기본값(0=ctranslate2가 알아서 결정, 보통 코어 수만큼)을
            # 그대로 두면 추론 한 번이 사실상 코어를 전부 쓴다 — 이 로봇은
            # 6코어인데, TRANSCRIBE_TIMEOUT_SEC이 넘어가 "포기"된 스레드가
            # 백그라운드에서 계속 도는 채로 새 추론이 또 겹치면(느린 발화가
            # 연달아 들어오는 경우) 코어 하나를 여러 추론이 동시에 나눠 쓰려고
            # 경쟁해서 load average가 50을 넘고 실제로 재부팅까지 이어지는 걸
            # 실기에서 확인함(2026-09-03). 추론 하나당 코어 사용량을 제한해서
            # 여러 개가 겹쳐도 전체 부하가 폭발하지 않게 한다.
            model = WhisperModel('small', device='cpu', compute_type='int8', cpu_threads=2)
            self.get_logger().info('Whisper small 모델을 CPU로 로드함')
        return model

    def listener_callback(self, msg):
        self.get_logger().info('STT 트리거 수신, 녹음 시작')
        result_msg = SttResult()

        audio = self._record_until_silence()
        if audio is None:
            result_msg.success = False
            result_msg.text = ''
            result_msg.error_message = '무음 감지'
            self.publisher_.publish(result_msg)
            self.get_logger().info('무음으로 종료됨')
            return

        future = self._transcribe_pool.submit(self._transcribe, audio)
        try:
            text = future.result(timeout=TRANSCRIBE_TIMEOUT_SEC)
        except FutureTimeoutError:
            self.get_logger().error(
                f'Whisper 처리 시간 초과({TRANSCRIBE_TIMEOUT_SEC}초) — 포기하고 다음 요청 처리')
            result_msg.success = False
            result_msg.text = ''
            result_msg.error_message = 'STT 처리 시간 초과'
            self.publisher_.publish(result_msg)
            return
        except Exception as e:
            self.get_logger().error(f'Whisper 처리 오류: {e}')
            result_msg.success = False
            result_msg.text = ''
            result_msg.error_message = 'STT 처리 오류'
            self.publisher_.publish(result_msg)
            return

        result_msg.success = True
        result_msg.text = text
        result_msg.error_message = ''
        self.publisher_.publish(result_msg)
        self.get_logger().info(f'STT 결과 발행됨: {text}')

    def _record_until_silence(self):
        """ReSpeaker(card 0)에서 VAD 기반으로 녹음. 발화 없거나 스트림이
        멈추면(타임아웃) None 반환 — 어느 쪽이든 이 메서드는 반드시 끝난다."""
        frames = []
        speech_started = False
        silence_frame_count = 0
        silence_frames_to_stop = int(SILENCE_TO_STOP_SEC * 1000 / FRAME_MS)
        max_wait_frames = int(MAX_WAIT_FOR_SPEECH_SEC * 1000 / FRAME_MS)
        max_total_frames = int(MAX_RECORDING_SEC * 1000 / FRAME_MS)

        proc = subprocess.Popen(
            ['arecord', '-D', STT_AUDIO_DEVICE, '-f', 'S16_LE',
             '-r', str(SAMPLE_RATE), '-c', '1', '-t', 'raw', '-q'],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            frame_bytes = _read_exact(proc.stdout, FRAME_BYTES, FRAME_READ_TIMEOUT_SEC)
            if frame_bytes is None:
                self.get_logger().error('마이크 스트림이 열리지 않음(타임아웃) — 녹음 중단')
                return None
            self.listening_started_pub.publish(Empty())

            waited_frames = 0
            for _ in range(max_total_frames):
                if frame_bytes is None:
                    self.get_logger().error('마이크 읽기가 멈춤(타임아웃) — 녹음 중단')
                    return None

                is_speech = self.vad.is_speech(frame_bytes, SAMPLE_RATE)

                if not speech_started:
                    if is_speech:
                        speech_started = True
                        frames.append(frame_bytes)
                    else:
                        waited_frames += 1
                        if waited_frames >= max_wait_frames:
                            return None
                else:
                    frames.append(frame_bytes)
                    if is_speech:
                        silence_frame_count = 0
                    else:
                        silence_frame_count += 1
                        if silence_frame_count >= silence_frames_to_stop:
                            break

                frame_bytes = _read_exact(proc.stdout, FRAME_BYTES, FRAME_READ_TIMEOUT_SEC)
        finally:
            proc.kill()
            try:
                # arecord가 커널 레벨(USB 드라이버 응답 없음 등, D-state)에서
                # 멈추면 kill(SIGKILL)을 보내도 실제로 죽는 데까지 오래 걸리거나
                # 안 죽을 수 있다(2026-09-03 실기에서 SIGKILL 후에도 process가
                # 바로 안 사라지는 걸 확인) — wait()에 타임아웃 없이 그냥
                # 기다리면 이 메서드가, 그리고 콜백 전체가 다시 무한 대기에
                # 빠진다. 타임아웃을 걸어서 좀비로 남더라도(하드웨어 자체가
                # 응답 안 하는 상황이라 이 프로세스 하나로는 못 고침) 콜백은
                # 반드시 끝나게 한다.
                proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self.get_logger().error(
                    'arecord 프로세스가 kill에도 응답 없음 — 좀비로 남겨두고 계속 진행')

        if not speech_started:
            return None

        pcm_bytes = b''.join(frames)
        audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return audio

    def _transcribe(self, audio):
        # beam_size 기본값(5)은 CPU에서 체감될 정도로 느림 — 이 Jetson의
        # ctranslate2가 CUDA 없이 빌드돼 있어(aarch64 pip wheel 자체가 그럼)
        # Whisper가 항상 CPU로 도는 게 근본 원인. 1(그리디)로 낮춰서 속도를
        # 확보하고, 정확도는 CONFIRMING 화면에서 사람이 확인/재시도로 보완.
        #
        # language='ko'로 고정돼 있었는데, 영어로 말하는 사용자도 지원해야 해서
        # (UI 언어 토글과 무관하게 실제 발화 언어를 그대로 따라가야 함) None으로
        # 바꿔 Whisper 자체 언어 감지를 쓴다. 언어 감지 패스가 한 번 더 붙어
        # 약간 느려지고, 아주 짧은 발화에서는 감지가 흔들릴 수 있지만
        # (CONFIRMING 화면에서 결과 확인/재시도로 보완 가능한 범위) 한국어
        # 고정보다 이쪽이 맞다.
        segments, _ = self.model.transcribe(audio, language=None, beam_size=1)
        return ''.join(segment.text for segment in segments).strip()


def main(args=None):
    rclpy.init(args=args)
    node = SttNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
