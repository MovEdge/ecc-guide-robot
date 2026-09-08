# Gazebo 시뮬레이터 (Ignition Fortress)

현장 주행 테스트에서 localization 문제가 발견되어, 그 원인이 Nav2/AMCL 설정 문제인지 하드웨어 문제인지 시뮬레이터에서 먼저 격리 검증하기 위해 구축. 배경은 [SESSION_LOG.md](SESSION_LOG.md) 9번 항목 참고, 진행 상황은 [ROADMAP.md](ROADMAP.md) Phase 1 참고.

## 스택

이 Jetson arm64 저장소엔 **Gazebo Classic이 없다** (`gazebo11`/`ros-humble-gazebo-ros-pkgs`/`ros-humble-turtlebot3-gazebo` 전부 미존재 — apt에 아예 안 올라와 있음). 대신 **Ignition Gazebo Fortress**(`ign gazebo`, 6.18.0)를 쓴다.

`ros-humble-ros-gz-sim`과 `ros-humble-ros-gz` 메타패키지도 이 조합(humble+arm64)에서는 빌드팜 공백으로 없다 (iron/rolling엔 있음). 그래서 표준 `ros_gz_sim` 스폰 launch 유틸 대신:
- **스폰**: `ign service`로 `/world/<world>/create`(`ignition.msgs.EntityFactory`) 직접 호출
- **토픽 브리징**: `ros_gz_bridge`의 `parameter_bridge` 실행 파일 직접 사용 (이건 humble+arm64에도 있음)

## 파일 구조 (`src/mov_navigation/`)

```
urdf/turtlebot3_waffle_sim.urdf   # turtlebot3_description 지오메트리 + 시뮬레이션 플러그인
worlds/sim_test_world.sdf         # 맵 없는 빈 테스트 월드 (구동/센서 단독 검증용)
worlds/ecc_map_world.sdf          # mapjh.pgm 압출 결과 포함된 실제 테스트 월드
scripts/map_to_walls_world.py     # <map>.pgm+yaml → Gazebo world 변환 스크립트 (범용, 인자로 맵 지정)
scripts/run_sim.sh                # 월드+스폰+브리지 원샷 실행
```

### `turtlebot3_waffle_sim.urdf`
`ros-humble-turtlebot3-description`의 URDF는 **Gazebo 태그가 전혀 없다** (공식 `turtlebot3_gazebo` 패키지가 그 역할을 하는데, 그 패키지 자체가 이 저장소엔 없음). 그래서 지오메트리는 원본 그대로 복사하고, 다음을 새로 추가함:
- `DiffDrive` 플러그인 (`wheel_left_joint`/`wheel_right_joint`, `wheel_separation=0.288`, `wheel_radius=0.033` — 원본 URDF의 joint origin/collision에서 실측한 값)
- `base_scan` 링크에 `gpu_lidar` 센서 (360 샘플, range 0.12~3.5m — 표준 LDS-01 참고값. **실기가 ld08/coin_d4면 다를 수 있으니 보정 필요**)
- mesh 경로는 `package://turtlebot3_description/...`가 아니라 `/opt/ros/humble/share/turtlebot3_description/...` 절대경로로 고쳐놓음 (`ros_gz_sim` 없이 `ign service`로 직접 스폰하면 `package://`가 해석 안 됨)

## 실행 방법

```bash
docker exec -it ros_humble bash
bash /workspace/ecc-guide-robot/src/mov_navigation/scripts/run_sim.sh
```

내부적으로: 기존 gazebo/bridge 프로세스 정리 → `ecc_map_world.sdf` headless 실행 → 로봇 스폰(현재 좌표: `-66.45, -12.2` — 벽/no-go 경계에서 2.3m 정도 떨어진 위치, 아래 "남은 제한사항" 참고) → `parameter_bridge` 실행. 로그는 `/tmp/sim_logs/`.

GUI로 보고 싶으면 서버는 그대로 두고 별도 터미널에서:
```bash
ign gazebo -g
```

### 검증 명령어
```bash
ign topic -e -t /stats -n 1                 # real_time_factor ~1.0이어야 함
ros2 topic echo /scan --once                 # ranges에 .inf 아닌 값이 섞여야 함
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}" -r 10
```

## `map_to_walls_world.py` 동작 방식

1. `<map>.pgm`을 `<map>.yaml`의 `negate`/`occupied_thresh` 기준으로 occupancy mask로 변환 (현재 `ecc_map_world.sdf`는 `mapjh.yaml` 기준. `mapjh.pgm`의 no-go 구역은 픽셀값 127(occ≈0.5, `occupied_thresh: 0.65`/`free_thresh: 0.25`  사이라 map_server가 "unknown"으로 해석함)이라 여기 포함 안 됨 — 물리적 벽이 아니라 Nav2 costmap+planner(`allow_unknown: false`)로만 막는 구역이라 의도적으로 그렇게 함)
2. `cv2.dilate`로 인접한 벽 조각을 먼저 뭉침 (성능 문제 때문 — 아래 참고)
3. `cv2.findContours` + `approxPolyDP`로 컨투어 추출/단순화
4. shapely로 폴리곤 보정: `buffer(0)`(자기교차 복구) → **항상 convex hull로 대체**(triangulation 실패 방지) → **CCW 방향으로 강제 정렬**(라이다 인식 문제 방지, 아래 참고)
5. 각 폴리곤을 SDF `<polyline>` extrusion으로 출력 (높이 1m, 별도 mesh 파일/라이브러리 불필요)

재실행: `python3 scripts/map_to_walls_world.py <map.yaml> <output_world.sdf>`

## 디버깅 기록 (같은 문제 반복 안 겪도록)

**① 성능 — real_time_factor 0.09 (10배 느림)**
real.pgm 전체(294m×208m)를 픽셀 단위 그대로 압출하면 1552개의 개별 collision shape가 나오는데, 이 개수 자체가 병목이었음(라이다 렌더링은 무관 — 빈 월드에서 라이다 켜도 real_time_factor 0.999로 정상이었음). `DILATE_KERNEL_PX`/`DILATE_ITERATIONS`로 인접 벽을 먼저 병합해서 226개까지 줄이니 real_time_factor 1.0 회복. **폴리곤 개수가 벽 디테일보다 성능에 훨씬 중요.**

**② Triangulation 실패 (`Unable to extrude mesh`)**
오목한(concave) 폴리곤에서 Ignition의 polyline 압출기가 자주 실패함. shapely `is_valid`/`buffer(0)`로 "수학적으로 유효한" 폴리곤을 만들어도 여전히 실패하는 경우가 있었음(면적 비율 98% 이상인 거의-convex한 도형도 실패) — **결국 모든 폴리곤을 convex hull로 강제 치환**하는 게 가장 안정적인 해결책이었음. 개별 벽 디테일(오목한 코너 등)은 손실되지만 국지적인 노이즈/가구 블록에서만 눈에 띄고 구조벽엔 영향 거의 없음.

**③ 라이다가 벽을 전혀 감지 못함 (`/scan` 전부 `.inf`)**
스폰 위치·range 문제인 줄 알았으나(실제로 처음엔 스폰 위치가 벽에서 8.8m 떨어진 곳이라 이것도 원인 중 하나였음), 벽 근처(1m)로 옮겨도 여전히 `.inf`만 나옴. Ignition 공식 예제 world로 렌더링 환경 자체는 정상 동작함을 확인했고, 일반 박스 primitive는 동적 스폰 로봇도 잘 감지하는 것도 확인함 → **원인은 우리가 생성한 폴리곤이 전부 시계방향(CW)으로 감겨 있어서, 압출된 벽 옆면의 법선이 안쪽을 향했고 back-face culling 때문에 gpu_lidar의 depth 렌더 패스에서 안 보였던 것**. 일반 카메라/GUI 렌더링에서는 문제없이 보여서 한참 헷갈렸음. `shapely.geometry.polygon.orient(sign=1.0)`로 전부 반시계(CCW)로 강제 통일해서 해결.

**④-1 세그폴트 — `DISPLAY` 환경변수 없음**
반복적으로 gazebo가 조용히 죽는(프로세스 자체가 사라지는) 문제 발생. 로그 확인해보니 실제로는 `Ogre::Hlms::createDatablock`에서 세그폴트로 크래시하고 있었음 (`~/.ignition/rendering/ogre2.log`에 `ERROR: libGL.so.1 failed to load`). 원인: **`$DISPLAY`가 비어있으면** Ogre2의 GL3Plus(GLX 기반) 렌더 경로가 headless(`-s`)로 돌려도 더미 렌더 컨텍스트조차 못 만들어서 크래시함 — 진짜 GPU 렌더링과 무관하게 그냥 *어떤* X 디스플레이든 하나 필요함. `export DISPLAY=:1`(호스트 `ls /tmp/.X11-unix/`로 확인한 실제 번호)로 해결. `run_sim.sh`에 기본값으로 넣어둠(`DISPLAY="${DISPLAY:-:1}"`, 이미 설정돼 있으면 안 건드림).

**④-2 CPU 레이캐스팅(`type="lidar"`) 대체 시도는 실패**
이 Ignition 버전(6.18/Fortress)은 `type="lidar"` 센서를 지원 안 함 ("Sensor type LIDAR not supported yet") — `gpu_lidar`만 써야 함. (참고로 "gpu_lidar"는 실제 GPU 없이 소프트웨어 렌더링(ogre2/llvmpipe)으로도 정상 동작함 — 이 Jetson 컨테이너엔 `nvidia-drm` 드라이버가 없어서 `libEGL ... failed to create dri2 screen` 경고가 뜨지만 렌더링 자체는 문제없이 됨.)

## 남은 제한사항

- **스폰 위치**(`-66.45, -12.2`)는 임의의 자유공간 지점 — 실제 로봇이 실측 주행을 시작했던 지점과 무관. 알게 되면 `run_sim.sh`의 `SPAWN_X`/`SPAWN_Y` 교체 필요. (2026-09-01 당시엔 `mapjh.pgm`의 no-go 구역을 점유(occupied)로 구웠던 버전이라 원래 스폰 위치가 벽 안이 돼서 옮겼던 것 — 지금은 no-go가 unknown 처리라 물리적 벽은 아니지만, 옮긴 위치 자체는 계속 써도 무방해서 그대로 둠)
- **라이다 스펙**(range/샘플 수)이 표준 LDS-01 참고값 — 실기 센서(ld08/coin_d4)와 스펙이 다르면 URDF의 `<lidar>` 블록 보정 필요
- 벽 226개 중 1개(`wall_141_0`)는 여전히 triangulation 실패 — 무시 가능한 수준(전체 맵 규모 대비 미미)
- IMU는 시뮬레이션에 없음 — 실기가 `robot_localization`(EKF)으로 바퀴 오도메트리+IMU를 융합하고 있다면, 지금 시뮬레이터의 순수 바퀴 오도메트리는 실기보다 더 정확하게 나올 수 있어 비교 시 유의

## AMCL 연동 (2026-08-29 완료)

`launch/sim_localization.launch.py`로 map_server + amcl + lifecycle_manager를 띄우고, `config/nav2_params_waffle_pi.yaml`(실기와 동일, `map_server`가 이미 `real.yaml`을 가리킴)을 그대로 재사용. 실행 순서:

```bash
bash scripts/run_sim.sh
ros2 launch launch/sim_localization.launch.py   # /initialpose도 10초 후 자동 발행
```

### 디버깅 기록 — AMCL이 pose를 전혀 발행 안 함

**증상**: `/amcl_pose`가 완전히 조용함, 에러도 없음. `amcl` 디버그 로그(`--log-level debug`)로 보니 `tf2_ros_message_filter: Removed oldest message because buffer is full` 반복 — 스캔이 큐에 쌓이기만 하고 콜백까지 도달을 못 함.

**시도 1 (실패)**: 라이다 프레임(`waffle/base_footprint/lidar`)에 대한 TF 자체가 없었음 — `robot_state_publisher`를 안 띄웠고, Ignition의 URDF→SDF 변환이 fixed joint로 연결된 `base_link`/`base_scan`을 `base_footprint`로 병합해버림. `tf2_ros static_transform_publisher`로 `base_footprint → waffle/base_footprint/lidar` 고정 TF를 추가해서 해결 (launch 파일의 `lidar_frame_static_tf` 노드).

**시도 2 (실패)**: `odom → base_footprint` TF는 실기 아키텍처를 그대로 재현하려고 `ekf_node`(robot_localization, `config/ekf.yaml`)가 발행하게 했었는데, EKF가 별도 프로세스로 `/clock`을 구독해서 TF를 만드는 구조라 스캔 타임스탬프를 따라가지 못하고 계속 큐가 꽉 차서 드랍됨 (원인 완전히 규명은 못 함 — cross-process 타이밍 이슈로 추정).

**최종 해결**: `ekf_node`를 빼고, `scripts/odom_to_tf.py`(간단한 `/odom` 구독 → `TransformBroadcaster`)로 `odom → base_footprint` TF를 직접 발행. `/odom`은 Gazebo DiffDrive 플러그인이 직접 발행하는 걸 이미 안정적으로 확인했었으니, 여기서 TF까지 만드는 게 가장 신뢰도 높은 경로였음. **IMU 융합(EKF)은 이 기본 파이프라인이 검증된 뒤 재도입 필요** — 지금은 순수 바퀴 오도메트리만 씀.

### 알려진 한계 — 자동 ground-truth 비교 불가

AMCL 추정치를 Gazebo의 "진짜" 위치와 자동으로 비교하려고 했으나, **Ignition이 `ign service create`로 동적 스폰한 엔티티의 pose를 안정적으로 브로드캐스트하지 않음** — 아래 3가지 방법 전부 실패 (플러그인은 다 정상 로드/실행됐지만 값이 갱신 안 되거나 토픽 자체가 안 뜸):
1. `/world/.../pose/info` — 스폰 시점 값에서 멈춤
2. `/world/.../dynamic_pose/info` — 마찬가지
3. `ignition-gazebo-pose-publisher-system` 플러그인(`/model/waffle/pose`, `/model/turtlebot3_waffle/pose` 둘 다 시도) — 플러그인 로드는 확인됐으나 토픽에 데이터가 안 뜸

추정 원인: Ignition의 "levels/performer" 시스템이 world 로드 시점에 정의된 엔티티만 "활성 퍼포머"로 추적하고, 나중에 `ign service create`로 스폰한 엔티티는 이 추적 대상에서 빠지는 것으로 보임. `/world/.../state` 서비스(요청-응답)로는 데이터가 오긴 하지만 raw ECS 컴포넌트 바이너리라 파싱이 비실용적.

**현재 검증 방법**: GUI로 직접 눈으로 확인 (`ign gazebo -g`) — 로봇이 벽을 따라 실제로 움직이는 걸 보면서 AMCL 추정치(RViz 등에서 시각화 시)가 비슷하게 따라가는지 육안 확인.

**나중에 근본적으로 고치려면**: 로봇을 `ign service create`로 동적 스폰하지 말고, world SDF 파일 자체에 처음부터 `<include>`(정적으로) 박아 넣는 방식으로 바꿔야 함 — URDF를 SDF로 변환해서 `ecc_map_world.sdf`에 직접 포함시키는 작업 필요 (스폰 위치를 매번 스크립트로 바꾸는 유연성은 잃음).

## 다음 단계

- Nav2 전체 스택(planner/controller/bt_navigator) 붙여서 실제 목적지까지 주행시켜보기
- IMU + EKF 재도입 (타이밍 문제 원인 규명 후)
- ground-truth 비교 자동화 (정적 include 방식으로 전환)
- `mov_*` 노드 체인을 이 시뮬레이터에 연결 (ROADMAP.md Phase 1 Step 2~4)
