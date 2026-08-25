# Git Workflow

## 브랜치 전략 — GitHub Flow

- `main`은 항상 빌드/동작 가능한 상태를 유지한다.
- 새 작업은 `main`에서 브랜치를 따서 진행한다: `feat/<scope>-<짧은설명>`, `fix/<scope>-<짧은설명>`
  - scope는 담당 패키지 축약어: `nav`, `slam`, `stt`, `tts`, `ui`, `dest`, `fsm`, `interfaces`
  - 예: `feat/stt-mic-test`, `fix/nav-costmap-tuning`
- 작업이 끝나면 PR을 열어 `main`으로 병합한다. 브랜치는 병합 후 삭제.

## 커밋 메시지 — Conventional Commits + 한글 설명

```
<type>(<scope>): <한글 설명>
```

- `type`: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `style` 중 하나
- `scope`: 위 브랜치 scope와 동일한 축약어
- 설명은 한글로 간결하게, 무엇을 왜 했는지 (어떻게는 diff가 보여줌)

예:
```
feat(nav): 동적 장애물 회피 로직 추가
fix(stt): 마이크 입력 끊김 현상 수정
docs(interfaces): 좌표 토픽 메시지 타입 변경 반영
```

## PR 규칙

- `main`으로의 모든 병합은 **PR 필수** (직접 push 금지).
- **자가승인 가능**: PR이 본인 담당 패키지([TEAM.md](TEAM.md) 기준)만 건드릴 때.
- **타 팀원 리뷰 필수**: 아래 중 하나라도 해당하면 관련 팀원 승인 후 병합.
  - `mov_interfaces`(공용 msg/srv/action) 변경 → **나머지 2인 모두 승인**
  - 다른 팀원이 담당하는 패키지를 수정 → **해당 담당자 승인**
- PR 설명에는 변경 이유와, 인터페이스(토픽/메시지) 변경이 있다면 그 내용을 명시한다.

## Claude Code 사용 규칙

- 새 기능 구현 전 [INTERFACES.md](INTERFACES.md)를 먼저 확인 — 이미 정의된 토픽/메시지/FSM 상태를 임의로 바꾸지 않는다. 바꿔야 하면 먼저 다른 팀원에게 알리고 문서부터 갱신한다.
- 커밋 전 해당 패키지가 `colcon build`로 정상 빌드되는지 확인한다.
- `build/`, `install/`, `log/`는 커밋하지 않는다 (`.gitignore`에 이미 등록됨).
- 작업이 [ROADMAP.md](ROADMAP.md)의 항목을 완료시켰다면 체크박스를 갱신한다.
- 담당 외 패키지를 수정해야 하는 상황이면, 먼저 사용자(팀원)에게 이유를 확인받는다.
