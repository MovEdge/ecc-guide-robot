#!/usr/bin/env python3
"""
Convert a ROS map_server-style occupancy map (pgm + yaml) into a static
Gazebo (Ignition) world SDF, using <polyline> extrusion so no external mesh
library (trimesh/assimp) is needed -- just opencv for contour extraction.

Usage:
    python3 map_to_walls_world.py <map.yaml> <output_world.sdf>
"""
import sys
import math
import yaml
import cv2
import numpy as np
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry.polygon import orient

WALL_HEIGHT = 1.0         # meters -- tall enough for the lidar/robot, cheap to render
MIN_CONTOUR_AREA_PX = 40  # drop small noise/clutter blobs (real_time_factor was ~0.09
                          # with 1557 individual collision shapes -- most were tiny
                          # fragments, not real structural walls)
APPROX_EPSILON_PX = 2.0   # polygon simplification tolerance, in source pixels
DILATE_KERNEL_PX = 3      # merge nearby wall fragments before contouring, so one
DILATE_ITERATIONS = 8     # physical wall becomes one collision shape instead of many

SYSTEM_PLUGINS = """
    <physics name="1ms" type="ignored">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>

    <plugin filename="ignition-gazebo-physics-system" name="gz::sim::systems::Physics"></plugin>
    <plugin filename="ignition-gazebo-user-commands-system" name="gz::sim::systems::UserCommands"></plugin>
    <plugin filename="ignition-gazebo-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"></plugin>
    <plugin filename="ignition-gazebo-sensors-system" name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>
    <plugin filename="ignition-gazebo-imu-system" name="gz::sim::systems::Imu"></plugin>

    <light type="directional" name="sun">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.8 0.8 0.8 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <attenuation>
        <range>1000</range>
        <constant>0.9</constant>
        <linear>0.01</linear>
        <quadratic>0.001</quadratic>
      </attenuation>
      <direction>-0.5 0.1 -0.9</direction>
    </light>
"""


def load_map_yaml(yaml_path):
    with open(yaml_path) as f:
        meta = yaml.safe_load(f)
    return meta


def occupied_mask(img, negate, occupied_thresh):
    # Same convention as ROS map_server / map_saver:
    #   occ = (255 - p) / 255  if not negate
    #   occ = p / 255          if negate
    p = img.astype(np.float32)
    occ = (255.0 - p) / 255.0 if not negate else p / 255.0
    mask = (occ >= occupied_thresh).astype(np.uint8) * 255
    return mask


def pixel_to_world(col, row, height_px, resolution, origin_x, origin_y):
    x = origin_x + col * resolution
    y = origin_y + (height_px - 1 - row) * resolution
    return x, y


def contour_to_polyline_points(contour, height_px, resolution, origin_x, origin_y):
    pts = []
    for pt in contour.reshape(-1, 2):
        col, row = int(pt[0]), int(pt[1])
        x, y = pixel_to_world(col, row, height_px, resolution, origin_x, origin_y)
        pts.append((x, y))
    return pts


def repair_polygon_points(pts, min_area_m2):
    """Gazebo's polyline extrusion needs a simple (non-self-intersecting)
    polygon. approxPolyDP occasionally produces a bowtie where two wall
    blobs pinch together at a single pixel -- buffer(0) is the standard
    shapely trick to split/repair that into valid simple polygon(s).

    Even shapely-valid simple polygons can still fail Ignition's own
    polyline triangulator when they're extremely concave/zigzag (seen on
    real map clutter blobs) -- those get replaced by their convex hull,
    which is always triangulable. Most wall segments are already close to
    convex (thin straight strips) so this only visibly affects messy
    clusters, not clean walls."""
    poly = Polygon(pts)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        return []
    geoms = list(poly.geoms) if isinstance(poly, MultiPolygon) else [poly]
    results = []
    for g in geoms:
        if g.is_empty or g.area < min_area_m2:
            continue
        # Always use the convex hull -- even polygons that are 98%+ convex by
        # area can still carry a thin concave notch that Ignition's polyline
        # triangulator chokes on (observed directly: wall_150 had a
        # near-zero-area notch despite a 0.986 area/hull ratio).
        hull = g.convex_hull
        if hull.area > 0:
            g = hull
        # Gazebo's polyline extrusion needs a CCW (viewed from +Z) boundary --
        # a CW ring produces inward-facing side-wall normals, which back-face
        # culling then makes invisible to gpu_lidar's depth render pass (even
        # though it still renders fine for the regular GUI camera).
        g = orient(g, sign=1.0)
        coords = list(g.exterior.coords)
        if len(coords) > 1 and coords[0] == coords[-1]:
            coords = coords[:-1]
        if len(coords) >= 3:
            results.append(coords)
    return results


def find_free_start_pose(free_mask, height_px, resolution, origin_x, origin_y):
    """Pick a free-space pixel near the map's free-space centroid as a
    placeholder spawn point. NOT necessarily where the real robot actually
    starts -- override once that's known."""
    ys, xs = np.nonzero(free_mask)
    cy, cx = int(np.mean(ys)), int(np.mean(xs))
    if free_mask[cy, cx] == 0:
        # centroid itself might land on an occupied/unknown pixel; nudge to
        # the nearest actual free pixel by brute-force search on a small ring
        free_idx = np.argmin((xs - cx) ** 2 + (ys - cy) ** 2)
        cy, cx = int(ys[free_idx]), int(xs[free_idx])
    return pixel_to_world(cx, cy, height_px, resolution, origin_x, origin_y)


def main():
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <map.yaml> <output_world.sdf>")
        sys.exit(1)

    yaml_path, out_path = sys.argv[1], sys.argv[2]
    meta = load_map_yaml(yaml_path)

    import os
    map_dir = os.path.dirname(os.path.abspath(yaml_path))
    image_path = os.path.join(map_dir, meta["image"])
    resolution = float(meta["resolution"])
    origin_x, origin_y = float(meta["origin"][0]), float(meta["origin"][1])
    negate = bool(meta.get("negate", 0))
    occupied_thresh = float(meta.get("occupied_thresh", 0.65))
    free_thresh = float(meta.get("free_thresh", 0.25))

    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise RuntimeError(f"failed to read {image_path}")
    height_px, width_px = img.shape[:2]

    occ_mask = occupied_mask(img, negate, occupied_thresh)

    # Merge nearby wall fragments so contouring produces far fewer, larger
    # blobs instead of one collision shape per few-pixel fragment -- this is
    # what actually drives Gazebo's collision-checking cost, not point count.
    kernel = np.ones((DILATE_KERNEL_PX, DILATE_KERNEL_PX), np.uint8)
    merge_mask = cv2.dilate(occ_mask, kernel, iterations=DILATE_ITERATIONS)

    contours, _ = cv2.findContours(merge_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    kept = []
    for c in contours:
        if cv2.contourArea(c) < MIN_CONTOUR_AREA_PX:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, APPROX_EPSILON_PX, True)
        if len(approx) < 3:
            continue
        kept.append(approx)

    total_points_before = sum(len(c) for c in contours)
    total_points_after = sum(len(c) for c in kept)

    # free-space centroid as a placeholder spawn point
    p = img.astype(np.float32)
    occ = (255.0 - p) / 255.0 if not negate else p / 255.0
    free_mask = (occ <= free_thresh).astype(np.uint8) * 255
    start_x, start_y = find_free_start_pose(free_mask, height_px, resolution, origin_x, origin_y)

    # --- build SDF ---
    min_area_m2 = MIN_CONTOUR_AREA_PX * (resolution ** 2)
    collisions_visuals = []
    wall_count = 0
    dropped_contours = 0
    for i, c in enumerate(kept):
        pts = contour_to_polyline_points(c, height_px, resolution, origin_x, origin_y)
        repaired = repair_polygon_points(pts, min_area_m2)
        if not repaired:
            dropped_contours += 1
            continue
        for j, poly_pts in enumerate(repaired):
            name = f"wall_{i}_{j}"
            pt_xml = "\n".join(f"          <point>{x:.4f} {y:.4f}</point>" for x, y in poly_pts)
            block = f"""
      <collision name="{name}">
        <geometry>
          <polyline>
{pt_xml}
            <height>{WALL_HEIGHT}</height>
          </polyline>
        </geometry>
      </collision>
      <visual name="{name}">
        <geometry>
          <polyline>
{pt_xml}
            <height>{WALL_HEIGHT}</height>
          </polyline>
        </geometry>
        <material>
          <ambient>0.6 0.6 0.6 1</ambient>
          <diffuse>0.6 0.6 0.6 1</diffuse>
        </material>
      </visual>"""
            collisions_visuals.append(block)
            wall_count += 1

    walls_xml = "\n".join(collisions_visuals)

    world = f"""<?xml version="1.0" ?>
<!--
  Auto-generated from {os.path.basename(yaml_path)} by map_to_walls_world.py.
  Do not hand-edit -- regenerate instead if the source map changes.

  Source map: {meta['image']}, resolution={resolution}, origin=({origin_x}, {origin_y})
  Contours: {len(contours)} raw -> {len(kept)} kept (area/point filtered)
  Placeholder spawn point (free-space centroid, NOT the real robot's actual
  start pose): ({start_x:.3f}, {start_y:.3f})
-->
<sdf version="1.6">
  <world name="ecc_map_world">
{SYSTEM_PLUGINS}
    <model name="ecc_map_walls">
      <static>true</static>
      <link name="link">{walls_xml}
      </link>
    </model>
  </world>
</sdf>
"""

    with open(out_path, "w") as f:
        f.write(world)

    print(f"image size: {width_px}x{height_px} px ({width_px*resolution:.1f}m x {height_px*resolution:.1f}m)")
    print(f"raw contours: {len(contours)}, kept after filtering: {len(kept)}")
    print(f"total polygon points: {total_points_before} raw -> {total_points_after} after simplification")
    print(f"wall shapes emitted: {wall_count} (contours fully dropped after repair: {dropped_contours})")
    print(f"placeholder spawn point (map frame): x={start_x:.3f} y={start_y:.3f}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
