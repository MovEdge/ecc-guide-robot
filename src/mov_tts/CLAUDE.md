# mov_tts

담당: 곽 — 전체 담당표는 [../../docs/TEAM.md](../../docs/TEAM.md) 참고 (TEAM.md에는 원래부터 곽 담당으로
예정돼 있었으나 실제 구현은 없던 상태 — 2026-09-02 최가 인프라 부분만 먼저 구현)

## 역할

`/tts/speak`으로 들어오는 임의의 텍스트를 Gemini TTS(`gemini-3.1-flash-tts-preview`)로 합성해서
스피커로 재생한다. 원래 "룰베이스 mp3 재생"으로 mov_ui에 흡수하기로 했었지만(TEAM.md/SESSION_LOG
기존 결정), 목적지명처럼 매번 달라지는 문장("OO로 안내를 시작합니다")을 말하려면 고정 mp3로는
부족해서 실시간 TTS로 재도입.

## 인터페이스

전체 계약은 [../../docs/INTERFACES.md](../../docs/INTERFACES.md)가 원본(draft, 팀 리뷰 전).

| 방향 | 이름 | 타입 | 비고 |
|---|---|---|---|
| sub | `/tts/speak` | `std_msgs/String` | 말할 텍스트. 지금은 `mov_ui`가 발행(목적지 해석 성공 시 "OO로 안내를 시작합니다", 도착 시 "도착했습니다") |

## 실행/테스트 방법

```bash
colcon build --packages-select mov_tts --symlink-install
ros2 run mov_tts tts_node
ros2 topic pub -1 /tts/speak std_msgs/msg/String "{data: '화장실로 안내를 시작합니다'}"

# 랜드마크 전체(한국어+영어) 캐시 예열 — ROS 노드 안 띄우고 바로 실행 가능,
# GEMINI_API_KEY만 .env에 있으면 됨. workspace source 후:
python3 src/mov_tts/scripts/prewarm_cache.py
```

스피커가 여러 개(ALSA 카드 여러 장) 잡히는 로봇이면 `aplay`가 쓰는 ALSA 기본 출력 장치가
의도한 스피커가 맞는지 확인 필요(`aplay -l`로 카드 목록 확인, 필요하면 `~/.asoundrc`로 기본
장치 지정).

## 현재 상태 / TODO

- [x] 인프라(2026-09-02, 최가 작업) — `/tts/speak` 구독 → Gemini TTS 합성 → `aplay` 재생까지
      노드 자체는 완성, 실제 API 호출로 한국어 문장 합성/WAV 저장 검증 완료
- [x] **`mov_ui` 와이어링(2026-09-02, 최가 사용자 요청대로 임시 구현)** — `on_dest_result`
      성공 시 "OO로 안내를 시작합니다"(조사 자동 선택), `on_nav_result` 성공 시
      "도착했습니다"를 `/tts/speak`으로 발행. **문구/타이밍은 최가 넣은 임시 버전 — mov_ui가
      곽 담당 패키지라 정식 확정은 곽 리뷰 필요** (LISTENING 진입 시 "듣고 있어요" 등 다른
      상태의 안내 문구는 아직 없음, 필요하면 곽이 추가)
- [x] 스피커 카드 확인됨(2026-09-02, 배, 실기 end-to-end 테스트) — `plughw:1,3`
      (card 1 = NVIDIA Jetson Orin Nano HDA, device 3 = HDMI 0)가 디스플레이 출력. 톤 테스트와
      실제 TTS 재생 둘 다 이 장치로 정상 출력 확인. `launch/app.launch.py`의 `mov_tts` Node에
      `additional_env={"TTS_AUDIO_DEVICE": "plughw:1,3"}`로 기본값 반영함(2026-09-02, 배) —
      이제 `run_full_real.sh`/`full_system.launch.py`로 띄워도 디스플레이로 나감.
- [x] **합성 결과 캐싱 추가(2026-09-02, 배, 사용자 요청)** — 실기 테스트 중 발화당 API 왕복이
      6~8초(가끔 그 이상)로 체감 지연이 컸음. (모델, 보이스, 텍스트) 키로 WAV를
      `TTS_CACHE_DIR`(기본 `~/.cache/mov_tts`)에 영구 캐싱하도록 `tts_node.py` 수정. 같은
      문장 재요청 시 API 호출 없이 캐시 파일 바로 재생(로그에 "합성 요청" 대신 "캐시 재생").
      캐싱/합성 로직은 `ensure_cached()`/`cache_path()`로 모듈 함수화(2026-09-03, 배) —
      노드(`TtsNode.on_speak`)와 아래 예열 스크립트가 같은 로직을 공유해 캐시 키가 어긋나지
      않게 함. 곽 리뷰 필요(mov_tts 담당 외 인원이 수정).
- [x] **캐시 예열 스크립트 추가(2026-09-03, 배, 사용자 요청)** —
      `scripts/prewarm_cache.py`: `landmarks.csv`(36개 랜드마크) + `mov_ui`의 문구 생성
      함수(`_build_navigating_speech`/`_build_arrived_speech`)를 그대로 import해서, 실제
      런타임이 말할 수 있는 모든 문구를 한국어+영어로 미리 합성/캐싱. 화장실/엘리베이터는
      `AUTO_NEAREST_CATEGORIES`라 카테고리명으로만 말하므로(개별 랜드마크 무관) 실질 54개
      문구(장소 24개×2언어 + 카테고리 2개×2언어 + "도착했습니다"×2언어)로 수렴, 전부 캐싱
      완료(2026-09-03 실행). `gemini-3.1-flash-tts`가 분당 10건 쿼터라 동시 요청 시 429가
      나서 순차 처리 + "retry in Ns" 안내를 그대로 따르는 재시도로 구현. 영어 지원은
      `mov_ui`의 i18n(다른 세션에서 추가됨, `i18n.py`/`ui_node._build_navigating_speech`가
      `i18n.lang`에 따라 문구를 다르게 만듦)에 얹혀 도는 것 — TTS 쪽에서 새로 만든 언어
      로직은 없음. `landmarks.csv`가 바뀌면(장소 추가/삭제) 재실행해서 캐시 갱신 필요.
- [ ] docs/INTERFACES.md/TEAM.md 반영 곽 리뷰 전
