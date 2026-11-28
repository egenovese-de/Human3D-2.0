"""Independently evaluate pixel-center raster channels with Blender BVH rays."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from mathutils.bvhtree import BVHTree

parser = argparse.ArgumentParser(description=__doc__)
for key in ('g4', 'reference', 'maps', 'result'):
    parser.add_argument(key, type=Path)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
sys.path.insert(0, str(args.g4.resolve() / 'tools/g2'))
from projection import Camera

config = json.loads(Path(__file__).with_name('config.json').read_text())
size = config['image_size']
rng = np.random.default_rng(309)
with np.load(args.reference) as ref:
    tree = BVHTree.FromPolygons(ref['reference'].tolist(), ref['reference_faces'].tolist(), all_triangles=True)
results = {}
for file in sorted(args.maps.glob('*.npz')):
    yaw = int(file.stem)
    camera = Camera(yaw, **config['main_camera_cm'])
    axes = camera.axes()
    origin = np.array([0, camera.center_y, 0]) + axes[2] * camera.distance
    focal = size * camera.distance / camera.span
    with np.load(file) as record:
        rgba = record['normal_right_up_toward']
        truth = record['depth_cm']
        selected = np.argwhere(record['valid'])
        selected = selected[rng.choice(len(selected), 96, replace=False)]
        background = np.argwhere(~record['mask'])
        background = background[rng.choice(len(background), 96, replace=False)]
        depths, normals, disagreements = [], [], 0
        for row, col in np.concatenate((selected, background)):
            ray = (col + .5 - size / 2) / focal * axes[0] - (row + .5 - size / 2) / focal * axes[1] - axes[2]
            point, normal, index, distance = tree.ray_cast(origin, ray)
            if record['mask'][row, col] != (point is not None):
                disagreements += 1
            if point is None or not record['mask'][row, col]:
                continue
            camera_z = float((origin - np.asarray(point)) @ axes[2])
            depths.append(abs(camera_z - truth[row, col]) * 10)
            direction = axes @ np.asarray(normal)
            normals.append(np.degrees(np.arccos(np.clip(direction @ rgba[row, col], -1, 1))))
        results[file.stem] = {'pixels': 192, 'ray_misses_or_false_foreground': disagreements,
                              'depth_max_mm': float(np.max(depths)), 'normal_max_degrees': float(np.max(normals)),
                              'inverse_z_used_for_perspective_interpolation': True,
                              'normal_length_max_error': float(np.max(np.abs(np.linalg.norm(rgba[record['valid']], axis=1) - 1)))}
        if disagreements or max(depths) > .04 or max(normals) > .2:
            raise ValueError(results[file.stem])
args.result.write_text(json.dumps(results, indent=2))
print('Independent BVH ray agreement:', results)
