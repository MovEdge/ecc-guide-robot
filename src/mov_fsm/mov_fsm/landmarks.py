"""
배회(patrol) 목표로 쓸 랜드마크 좌표만 최소로 읽는 로더.

mov_dest_resolver.resolver_core에도 같은 landmarks.csv를 읽는 load_landmarks()가
있지만, 그쪽은 LLM 매칭용 필드(desc)와 google-genai 의존성까지 같이 끌고 온다.
배회는 이름/좌표만 있으면 되는 훨씬 가벼운 목적이라, mov_dest_resolver 내부
구현(배 담당)에 결합되지 않도록 여기서 최소한만 따로 읽는다.
"""

import csv
import os
from dataclasses import dataclass

from ament_index_python.packages import get_package_share_directory

# mov_dest_resolver.resolver_core.DEFAULT_LANDMARKS_CSV와 동일 경로 —
# mov_slam 패키지의 share 리소스로 설치된 랜드마크 DB를 가리킨다(2026-09-03,
# 절대경로 하드코딩에서 전환. 원본 산출 과정은 /workspace/slam/slam_frommap 참고).
DEFAULT_LANDMARKS_CSV = os.path.join(
    get_package_share_directory('mov_slam'), 'landmarks', 'landmarks.csv')


@dataclass
class PatrolPoint:
    name: str
    x: float
    y: float


def load_patrol_points(csv_path: str = DEFAULT_LANDMARKS_CSV) -> list[PatrolPoint]:
    points = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if not row.get('name'):
                continue
            points.append(PatrolPoint(
                name=row['name'], x=float(row['x']), y=float(row['y'])))
    return points
