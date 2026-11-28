"""Create and score RGB clothing and occlusion controls on a calibrated fixture."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_erosion

from evidence import CONFIG, SIZE, affine_inverse, aligned_depth, angles, dsine_to_camera, visible_surface
from projection import Camera, Raster


def dress(vertices, thickness):
    y, width = vertices[:, 1], np.abs(vertices[:, 0])
    effect = np.clip((y - 2) / 8, 0, 1) * np.clip((57 - y) / 10, 0, 1)
    effect *= np.clip((25 - width) / 8, 0, 1)
    # Low-frequency textile ridges alter the visible shape without changing the
    # hidden body used by the anatomical score.
    ripple = .22 * np.sin(vertices[:, 0] * .62 + y * .32)
    points = vertices.copy()
    points[:, 2] += (thickness + ripple) * effect * np.tanh(vertices[:, 2] / 6)
    points[:, 0] += thickness * .4 * effect * np.tanh(vertices[:, 0] / 8)
    return points


def prepare(reference, output):
    output.mkdir(parents=True, exist_ok=True)
    with np.load(reference) as data:
        body, faces = data['reference'], data['reference_faces']
    for tag, thickness in [('control_studio', 0), ('close_garment', 1.5),
                           ('loose_garment', 6), ('external_panel', 0), ('striped_background', 0)]:
        vertices = dress(body, thickness) if thickness else body.copy()
        modified = (np.linalg.norm(vertices - body, axis=1) > .05)[faces].any(1)
        if tag == 'external_panel':
            n = len(body)
            vertices = np.vstack((vertices, np.array([[-34, 18, 55], [8, 18, 55],
                                                       [8, 63, 55], [-34, 63, 55]])))
            tris = np.vstack((faces, [[n, n+1, n+2], [n, n+2, n+3]]))
            modified = np.concatenate((modified, [True, True]))
        else:
            tris = faces
        np.savez_compressed(output / f'{tag}.npz', reference=vertices, reference_faces=tris,
                            body=body, body_faces=faces, modified=modified)


def evaluate(captures, predictions, raster_file, output):
    raster = Raster(raster_file)
    report = {}
    for file in sorted(captures.glob('*.npz')):
        with np.load(file) as data:
            body, faces = data['body'], data['body_faces']
            verts, surface_faces = data['reference'], data['reference_faces']
            modified = data['modified']
        report[file.stem] = {}
        for yaw in (0, 90):
            folder = predictions / file.stem
            camera = Camera(yaw, **CONFIG['main_camera_cm'])
            reference = visible_surface(raster, camera, body, faces, SIZE)
            visible = visible_surface(raster, camera, verts, surface_faces, SIZE)
            depth = np.load(folder / f'{yaw}-depth.npy')
            normal = dsine_to_camera(np.load(folder / f'{yaw}-normal.npy'))
            surface_region = visible.valid & modified[np.maximum(visible.triangle, 0)]
            yy, xx = np.indices(depth.shape)
            train = visible.valid & ((xx + yy) % 3 == 0)
            test = visible.valid & ~train
            aligned = aligned_depth(depth, *affine_inverse(depth[train], visible.depth_cm[train]))
            metrics = {}
            for label, support in [('visible_surface', test), ('covered_visible', test & surface_region),
                                   ('covered_body', test & surface_region & reference.valid),
                                   ('exposed_body', test & ~surface_region & reference.valid)]:
                truth = visible if label in ('visible_surface', 'covered_visible') else reference
                valid = support & np.isfinite(aligned)
                if valid.sum() < 20:
                    continue
                errors = np.abs(aligned[valid] - truth.depth_cm[valid]) * 10
                metrics[label] = dict(pixels=int(valid.sum()), depth_mae_mm=float(errors.mean()),
                     normal_median_deg=float(np.median(angles(normal[valid], truth.normals[valid]))))
            report[file.stem][str(yaw)] = metrics
        print(file.stem, report[file.stem], flush=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'evaluate'])
    parser.add_argument('paths', nargs='+', type=Path)
    args = parser.parse_args()
    (prepare if args.mode == 'prepare' else evaluate)(*args.paths)
