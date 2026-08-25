# Team

Team **MovEdge** — ECC Guide Robot

## 담당 파트

| 팀원 | 담당 영역 | 주요 패키지(예정) |
|---|---|---|
| 곽 | STT, 터치스크린 UI, 음성출력(TTS) | `mov_stt`, `mov_ui`, `mov_tts` |
| 최 | 네비게이션, 전체 시스템 통합/FSM, 하드웨어 디자인·배치 | `mov_navigation`, `mov_fsm` |
| 배 | SLAM/맵, 랜드마크 좌표 DB, LLM API 연동 | `mov_slam`, `mov_dest_resolver` |

## 패키지 소유권 규칙

- 각 패키지의 최초 구현/구조 결정은 담당자가 주도한다.
- 담당자 외 다른 팀원이 해당 패키지를 수정해야 하면, PR 전에 담당자에게 알린다.
- `mov_interfaces`(공용 msg/srv/action)는 3인 공동 소유 — 변경 시 [GIT_WORKFLOW.md](GIT_WORKFLOW.md)의 리뷰 규칙을 따른다.

## 역할 변경

담당 파트가 바뀌면 이 표만 갱신하면 된다. 각 패키지 폴더의 `CLAUDE.md`에도 담당자를 명시해 Claude Code가 "지금 이 코드는 누구 담당인지" 참조할 수 있게 한다.
