"""G2 Blender BVH symmetric surface metric, regional cuts and structural checks."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('g4', type=Path)
parser.add_argument('root', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--stress', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
sys.path.insert(0, str(args.g4.resolve() / 'tools/g2'))
from surface import distances, samples, stats, tree


def regions(points, limits):
    y = (points[:, 1] - limits[0]) / (limits[1] - limits[0])
    x = np.abs(points[:, 0])
    front = points[:, 2] >= 0
    arms = x > np.where(y > .75, 22, 20)
    return {
        'head': y >= .875, 'neck': (y >= .825) & (y < .875) & (x < 11),
        'shoulders': (y >= .78) & (y < .855) & (x >= 11),
        'chest': (y >= .70) & (y < .825) & ~arms & front,
        'upper_back': (y >= .70) & (y < .825) & ~arms & ~front,
        'abdomen': (y >= .61) & (y < .70) & ~arms & front,
        'waist': (y >= .575) & (y < .655) & ~arms,
        'pelvis': (y >= .465) & (y < .575) & ~arms & front,
        'gluteal': (y >= .465) & (y < .575) & ~arms & ~front,
        'upper_arms': arms & (y >= .63) & (y < .78),
        'forearms': arms & (y >= .48) & (y < .63),
        'thighs': (y >= .275) & (y < .485) & (x < 25),
        'calves': (y >= .075) & (y < .275) & (x < 25),
    }


def cross_section(vertices, faces, height):
    polygons = vertices[faces]
    points = []
    for start, end in ((0, 1), (1, 2), (2, 0)):
        a, b = polygons[:, start], polygons[:, end]
        intersects = (a[:, 1] > height) != (b[:, 1] > height)
        a, b = a[intersects], b[intersects]
        factor = (height - a[:, 1]) / (b[:, 1] - a[:, 1])
        points.extend((a + factor[:, None] * (b - a))[:, [0, 2]])
    xy = np.array(points)
    if not len(xy):
        return {}
    # Exclude the hanging arms from torso width and depth.
    torso = xy[np.abs(xy[:, 0]) < 21]
    if len(torso) < 3:
        return {}
    return {'width_cm': float(np.ptp(torso[:, 0])), 'depth_cm': float(np.ptp(torso[:, 1])),
            'anterior_cm': float(torso[:, 1].max()), 'posterior_cm': float(torso[:, 1].min())}


def intersection_pairs(bvh, faces):
    result = set()
    for a, b in bvh.overlap(bvh):
        if a < b and not np.isin(faces[a], faces[b]).any():
            result.add((a, b))
    return result


def compare(file, case):
    with np.load(file) as arrays:
        ref, ref_faces, faces = [arrays[k] for k in ('reference', 'reference_faces', 'faces')]
        fits = {k: arrays[k] for k in arrays.files if k not in ('reference', 'reference_faces', 'faces')}
    ref_tree = tree(ref, ref_faces)
    ref_samples = samples(ref, ref_faces, 819)
    reference_range = ref[ref_faces, 1].min(), ref[ref_faces, 1].max()
    ref_regions = regions(ref_samples, reference_range)
    levels = {name: reference_range[0] + ratio * (reference_range[1] - reference_range[0])
              for name, ratio in [('chest', .75), ('abdomen', .675), ('waist', .62), ('pelvis', .535)]}
    ref_sections = {key: cross_section(ref, ref_faces, level) for key, level in levels.items()}
    output = {}
    for label, points in fits.items():
        pred_tree = tree(points, faces)
        pred_samples = samples(points, faces, 818)
        pred_regions = regions(pred_samples, reference_range)
        da, db = distances(pred_samples, ref_tree), distances(ref_samples, pred_tree)
        local = {}
        for key, mask in ref_regions.items():
            values = np.r_[da[pred_regions[key]], db[mask]]
            if values.size:
                local[key] = stats(values) | {'samples': int(values.size)}
        section = {}
        for key, level in levels.items():
            region = cross_section(points, faces, level)
            section[key] = {name.replace('_cm', '_signed_error_mm'): (value - ref_sections[key][name]) * 10
                            for name, value in region.items() if name in ref_sections[key]}
        intersect = intersection_pairs(pred_tree, faces)
        row = output[label] = {'symmetric_mm': stats(np.r_[da, db]), 'candidate_to_reference_mm': stats(da),
                'reference_to_candidate_mm': stats(db), 'regional_mm': local, 'sections': section,
                'disjoint_index_triangle_crossing_pairs': len(intersect), 'new_intersection_pairs_vs_local_parent': None}
        if label in ('D7', 'D8', 'L0'):
            parent = {'D7': 'D3', 'D8': 'D6', 'L0': 'D0'}[label]
            initial = intersection_pairs(tree(fits[parent], faces), faces)
            added = len(intersect - initial)
            row['new_intersection_pairs_vs_local_parent'] = added
            row['local_validation'] = 'reject and retain parent' if added else 'pass'
        if case.startswith('A_') or args.stress:
            ids = np.unique(faces)
            row['direct_vertex_mm'] = stats(np.linalg.norm(points[ids] - ref[ids], axis=1) * 10)
    for label, row in output.items():
        if row.get('local_validation') == 'reject and retain parent':
            parent = {'D7': 'D3', 'D8': 'D6', 'L0': 'D0'}[label]
            output[label] = output[parent] | {
                'local_validation': row['local_validation'],
                'new_intersection_pairs_vs_local_parent': row['new_intersection_pairs_vs_local_parent'],
                'rejected_surface_mm': row['symmetric_mm']}
    return output


data = {}
paths = sorted(args.root.glob('*.npz')) if args.stress else sorted(args.root.rglob('meshes.npz'))
for path in paths:
    case = path.stem if args.stress else path.parent.name
    key = path.stem if args.stress else path.parent.relative_to(args.root).as_posix()
    data[key] = compare(path, case)
    print(key, {k: round(x['symmetric_mm']['mean'], 3) for k, x in data[key].items()}, flush=True)
args.output.write_text(json.dumps(data, indent=2, allow_nan=False))
