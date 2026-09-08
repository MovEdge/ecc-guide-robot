# mov_stt

담당: 곽 — 전체 담당표는 [../../docs/TEAM.md](../../docs/TEAM.md) 참고 (문서 자체가 없던 상태였음 —
2026-09-03 실기 안정성 문제 대응 중 배가 처음 작성. 원본 설계/구현 의도는 곽 확인 필요)

## 역할

`/stt/start_listening` 트리거를 받으면 ReSpeaker 마이크에서 VAD(webrtcvad) 기반으로 발화
구간을 녹음하고, Whisper(`faster-whisper`, `small` 모델, CPU)로 전사해 `/stt/result`로
발행한다.

## 인터페이스

전체 계약은 [../../docs/INTERFACES.md](../../docs/INTERFACES.md)가 원본.

| 방향 | 이름 | 타입 | 비고 |
|---|---|---|---|
| sub | `/stt/start_listening` | `std_msgs/Empty` | 녹음 시작 트리거 |
| pub | `/stt/listening_started` | `std_msgs/Empty` | 마이크 스트림이 실제로 열린 시점에 발행 |
| pub | `/stt/result` | `mov_interfaces/SttResult` | 전사 결과. `success=false`면 `error_message`에 `'무음 감지'`/`'STT 처리 오류'`/`'STT 처리 시간 초과'` 중 하나 |

## 실행/테스트 방법

```bash
colcon build --packages-select mov_stt --symlink-install
ros2 run mov_stt stt_node
ros2 topic pub -1 /stt/start_listening std_msgs/msg/Empty '{}'
ros2 topic echo /stt/result
```

마이크 장치는 `STT_AUDIO_DEVICE` 환경변수로 지정(기본 `plughw:CARD=ArrayUAC10,DEV=0`, 아래
"실기 확인 사항" 참고). `arecord -l`로 실제 카드 이름 확인 가능.

## 현재 상태 / TODO

- [x] **캡처를 `subprocess`(arecord) 기반으로 재작성(2026-09-03, 배)** — 원래
      `sounddevice.RawInputStream.read()`를 타임아웃 없이 블로킹 호출했는데, 실기에서 이게
      멈추면 ROS2 콜백이 영원히 안 끝나서 이후 모든 트리거가 씹히는 문제를 재현/확인함.
      `arecord` 서브프로세스 + `select()` 기반 프레임(30ms)당 3초 타임아웃으로 교체 —
      멈추면 프로세스를 kill(안 죽으면 5초 후 좀비로 남기고 진행)해서 콜백이 반드시 끝나게
      함. 상세 배경은 [../../docs/SESSION_LOG.md](../../docs/SESSION_LOG.md) #13-1.
- [x] **Whisper 전사(`_transcribe`)에 타임아웃 추가(2026-09-03, 배)** — 마이크 쪽을 고친
      뒤에도 특정 오디오(VAD가 배경 소음을 발화로 오탐지한 경우)에서 Whisper 자체가 234초까지
      걸리는 걸 재현 확인. `ThreadPoolExecutor` + `future.result(timeout=40)`로 넘으면 포기하고
      실패 처리(`'STT 처리 시간 초과'`). ctranslate2 네이티브 호출이라 스레드를 강제 종료는
      못 함 — 포기된 스레드는 백그라운드에서 계속 CPU를 쓰며 돎. 상세는 SESSION_LOG #13-3.
- [x] **Whisper `cpu_threads` 제한(2026-09-03, 배)** — 위 "포기된 스레드가 계속 돎" 특성 +
      ctranslate2 기본값(`cpu_threads=0`, 추론 한 번에 코어를 거의 다 씀)이 겹쳐 실기(6코어)에서
      load average 52 + 재부팅을 관측함. **재부팅의 정확한 원인(브라운아웃 등)은 확인 못 함 —
      이 스레드 경쟁이 원인이라는 것도 시간상 상관관계에 기반한 추정이지 직접 측정한 사실은
      아님.** 다만 ctranslate2가 기본적으로 코어를 무제한 쓸 수 있다는 것 자체는 사실이라,
      `cpu_threads=2` + 스레드풀 `max_workers` 4→2로 제한해둠(원인 추정이 틀리더라도 유효한
      안전장치). 상세는 SESSION_LOG #13-4 — **재부팅이 계속되면 이 추정부터 재검증할 것.**
- [x] **오디오 장치를 카드 이름 기반으로 변경(2026-09-03, 배)** — ReSpeaker를 USB 허브 경유로
      바꿔 꽂자 ALSA 카드 번호가 0→3으로 밀려서, 숫자로 고정해뒀던 `STT_AUDIO_DEVICE`
      (`plughw:0,0`)가 허브의 다른 장치를 잡는 문제를 실기에서 확인. `plughw:CARD=ArrayUAC10,DEV=0`
      형태로 변경 — 카드 이름은 USB 재열거 순서와 무관하게 고정됨. 상세는 SESSION_LOG #13-5.
- [x] **UI SIGABRT 크래시 대응(2026-09-03, 배, `mov_ui` 쪽 수정)** — `ui_node`가 실기 테스트
      중 exit code -6(SIGABRT)으로 죽는 걸 확인. PyQt5가 슬롯(ROS 콜백 포함) 안 미처리 예외에
      기본적으로 프로세스를 abort시키는 것으로 알려진 동작과 exit code가 일치하지만, **실제
      트레이스백은 확보 못 해서 정확한 원인 코드 경로는 미확인**. `sys.excepthook`을 설치해
      증상(전체 크래시)만 우선 막음 — 상세는 SESSION_LOG #13-2.
- [ ] 위 5개 항목 전부 곽 리뷰 전 — 이 패키지 원 설계자 확인 필요
- [ ] VAD(`webrtcvad.Vad(1)`)가 배경 소음을 발화로 오탐지하는 경우가 실기에서 관측됨(빈 전사
      결과로 이어짐) — aggressiveness 상향(`Vad(2)`/`Vad(3)`) 등 튜닝 검토 안 함, 미해결
