"""Re-measure fixed torso sections from the verified G5 evidence archive."""
import argparse
import io
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np

CASES = ('A_high_mass', 'A_heldout_1', 'A_slim')
LEVELS = {'chest': .75, 'abdomen': .675, 'waist': .62, 'pelvis': .535}


def torso_loop(vertices, faces, y):
    coordinates, neighbors = {}, {}
    face_signs = vertices[faces, 1] > y
    crossed = face_signs.any(axis=1) & ~face_signs.all(axis=1)
    for tri, signs in zip(faces[crossed], face_signs[crossed]):
        pair = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            if signs[i] == signs[j]:
                continue
            edge = tuple(sorted((int(tri[i]), int(tri[j]))))
            if edge not in coordinates:
                a, b = vertices[list(edge)]
                fraction = (y - a[1]) / (b[1] - a[1])
                coordinates[edge] = (a + fraction * (b - a))[[0, 2]]
            pair.append(edge)
        a, b = pair
        neighbors.setdefault(a, set()).add(b)
        neighbors.setdefault(b, set()).add(a)
    unseen = set(neighbors)
    loops = []
    while unseen:
        seed = min(unseen)
        todo = [seed]
        component = set()
        while todo:
            item = todo.pop()
            if item in component:
                continue
            component.add(item)
            todo.extend(neighbors[item] - component)
        unseen -= component
        if any(len(neighbors[item]) != 2 for item in component):
            continue
        path, prev, cur = [], None, seed
        while not path or cur != seed:
            path.append(cur)
            following = min(neighbors[cur] - {prev})
            prev, cur = cur, following
        ring = np.array([coordinates[item] for item in path])
        if not ring[:, 0].min() < 0 < ring[:, 0].max():
            continue
        x, z = ring.T
        area = abs(np.dot(x, np.roll(z, 1)) - np.dot(z, np.roll(x, 1))) / 2
        loops.append((area, ring))
    if not loops:
        raise ValueError(f'No closed torso loop at {y:.4f} cm')
    return max(loops, key=lambda x: x[0])


def geometry(ring):
    vectors = np.roll(ring, -1, axis=0) - ring
    lengths = np.linalg.norm(vectors, axis=1)
    mask = lengths > 1e-9
    return ring[mask], vectors[mask], lengths[mask]


def directed(source, target):
    vertices, vectors, lengths = geometry(source)
    ends = np.cumsum(lengths)
    arc = (np.arange(512) + .5) * ends[-1] / 512
    ids = np.searchsorted(ends, arc)
    source_points = vertices[ids] + vectors[ids] * ((arc - (ends - lengths)[ids]) / lengths[ids])[:, None]
    vertices, vectors, lengths = geometry(target)
    offsets = source_points[:, None, :] - vertices[None, :, :]
    fraction = np.clip((offsets * vectors).sum(axis=-1) / lengths**2, 0, 1)
    return np.linalg.norm(offsets - fraction[..., None] * vectors, axis=-1).min(axis=1)


def main(source, output):
    results = {}
    with ZipFile(source) as archive:
        surface = json.loads(archive.read('measurements/calibrated-surface.json'))
        for subject in CASES:
            raw = archive.read(f'geometry/{subject}/snapshots_and_local_proposals.npz')
            with np.load(io.BytesIO(raw), allow_pickle=False) as meshes:
                ref, faces = meshes['reference'], meshes['reference_faces']
                floor, ceiling = ref[faces, 1].min(), ref[faces, 1].max()
                results[subject] = {}
                for section, ratio in LEVELS.items():
                    y = floor + ratio * (ceiling - floor)
                    area, ref_ring = torso_loop(ref, faces, y)
                    ref_circumference = geometry(ref_ring)[2].sum()
                    row = {'height_cm': float(y), 'reference_circumference_cm': float(ref_circumference),
                           'reference_area_cm2': float(area), 'fits': {}}
                    results[subject][section] = row
                    for arm in [*(f'D{i}' for i in range(10)), 'L0']:
                        parent = {'D7': 'D3', 'D8': 'D6', 'L0': 'D0'}.get(arm)
                        retained = parent if surface[subject][arm].get('local_validation') == 'reject and retain parent' else arm
                        try:
                            fit_area, ring = torso_loop(meshes[retained], meshes['faces'], y)
                            distances = np.r_[directed(ring, ref_ring), directed(ref_ring, ring)] * 10
                        except ValueError as error:
                            row['fits'][arm] = {'unavailable': str(error)}
                            continue
                        row['fits'][arm] = {
                            'geometry': retained, 'circumference_error_mm': float((geometry(ring)[2].sum() - ref_circumference) * 10),
                            'area_error_cm2': float(fit_area - area),
                            'symmetric_shape_mean_mm': float(distances.mean()),
                            'symmetric_shape_p95_mm': float(np.percentile(distances, 95)),
                        }
    output.write_text(json.dumps(results, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    main(args.archive, args.output)
