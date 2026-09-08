# mov_slam

담당: 배 — 전체 담당표는 [../../docs/TEAM.md](../../docs/TEAM.md) 참고

## 역할

ROS 노드는 없음. ECC 실측 맵(`maps/mapjh.yaml`+`mapjh.pgm`, nav2 map_server용)과
랜드마크 좌표DB(`landmarks/landmarks.csv`)를 `share/mov_slam/`에 설치해, 다른
패키지(`mov_navigation`, `mov_dest_resolver`, `mov_fsm`)가
`get_package_share_directory('mov_slam')`로 절대경로 없이 참조하게 하는 리소스 전용 패키지.

원본 SLAM 작업 디렉토리는 `/workspace/slam/slam_frommap/`(out/out2/out3, backup, 각종
검증용 이미지, `MakeROSMap.py`)에 그대로 있고 git 추적 밖이다. 새 맵/좌표DB를 확정할
때마다 최종본만 여기 `maps/`, `landmarks/`로 복사해 "승격"한다 — 중간 산출물/백업/검증
이미지는 패키지에 넣지 않는다.

## 인터페이스

토픽/서비스 없음(리소스 전용 패키지).

## 실행/테스트 방법

```bash
colcon build --packages-select mov_slam
# 설치된 리소스 경로 확인
ros2 pkg prefix mov_slam
ls $(ros2 pkg prefix mov_slam)/share/mov_slam/maps
ls $(ros2 pkg prefix mov_slam)/share/mov_slam/landmarks
```

## 현재 상태 / TODO

- [x] 패키지 신설(2026-09-03) — `/workspace/slam/slam_frommap/out3/{mapjh.yaml,mapjh.pgm,landmarks.csv}`를
      내부화. `mov_fsm`/`mov_dest_resolver`/`mov_navigation`의 하드코딩 절대경로를
      `get_package_share_directory('mov_slam')` 기반으로 교체(연관 커밋 참고)
- [ ] 맵/좌표DB 갱신 시 승격 절차(스크립트 or 문서화) 정리
