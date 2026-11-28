"""Measure RGB model outputs and save verified float observation payloads."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion, distance_transform_edt, gaussian_filter
from scipy.stats import spearmanr

from evidence import (CONFIG, SIZE, affine_inverse, aligned_depth, angles, dsine_to_camera, perspective_normals,
                      visible_surface)
from projection import Camera, Raster


def describe_depth(raw, reference, normal, camera, train, test):
    truth = reference.depth_cm
    scale, offset = affine_inverse(raw[train], truth[train])
    mapped = aligned_depth(raw, scale, offset)
    test = test & np.isfinite(mapped)
    error = mapped[test] - truth[test]
    inverse_scale = float(np.dot(raw[train], 1 / truth[train]) / max(np.dot(raw[train], raw[train]), 1e-12))
    scale_only = aligned_depth(raw, inverse_scale, 0)
    calibrated_depth = np.where(np.isfinite(truth), truth, 0)
    triple = binary_erosion(reference.valid, iterations=2)[1:-1, 1:-1] & test[1:-1, 1:-1]
    point_normals = perspective_normals(np.where(np.isfinite(mapped), mapped, 0), camera)
    ref_normals_from_depth = perspective_normals(calibrated_depth, camera)
    pred_smooth = perspective_normals(gaussian_filter(np.where(np.isfinite(mapped), mapped, 0), 1.0), camera)
    grad_ref = np.stack(np.gradient(calibrated_depth), axis=-1)[1:-1, 1:-1][triple]
    grad = np.stack(np.gradient(np.where(np.isfinite(mapped), mapped, 0)), axis=-1)[1:-1, 1:-1][triple]
    normals = normal[1:-1, 1:-1][triple] if normal is not None else None
    rho = spearmanr(raw[test], 1 / truth[test]).statistic
    result = {'affine_inverse_pixel_mae_mm': float(np.abs(error).mean() * 10),
              'scale_only_inverse_pixel_mae_mm': float(np.abs(scale_only[test] - truth[test]).mean() * 10),
              'constant_plane_pixel_mae_mm': float(np.abs(truth[train].mean() - truth[test]).mean() * 10),
              'abs_rel': float(np.abs(error / truth[test]).mean()),
              'rank_spearman': float(rho) if np.isfinite(rho) else None,
              'centered_depth_gradient_error_mm_per_px': float(np.linalg.norm(grad - grad_ref, axis=-1).mean() * 10),
              'derived_to_truth_median_deg': float(np.median(angles(point_normals[triple], reference.normals[1:-1, 1:-1][triple]))),
              'derived_smoothed_to_truth_median_deg': float(np.median(angles(pred_smooth[triple], reference.normals[1:-1, 1:-1][triple]))),
              'oracle_depth_normal_median_deg': float(np.median(angles(ref_normals_from_depth[triple], reference.normals[1:-1, 1:-1][triple]))),
              'direct_vs_derived_median_deg': float(np.median(angles(point_normals[triple], normals))) if normals is not None else None,
              'affine_inverse': [scale, offset], 'test_pixels': int(test.sum())}
    return result, mapped


def describe_normal(raw, reference):
    distance = distance_transform_edt(reference.mask)
    domain = reference.mask & (np.linalg.norm(reference.normals, axis=-1) > .9)
    angular = angles(raw, reference.normals)
    inner = reference.valid
    return {'mean_deg': float(angular[inner].mean()), 'median_deg': float(np.median(angular[inner])),
            'p95_deg': float(np.percentile(angular[inner], 95)),
            'boundary_1_to_3px_median_deg': float(np.median(angular[domain & (distance <= 3)])),
            'pixel_count': int(inner.sum())}


def main(args):
    raster = Raster(args.raster)
    args.output.mkdir(parents=True, exist_ok=True)
    matrix = {}
    yy, xx = np.indices((SIZE, SIZE))
    for path in sorted(args.refs.glob('*.npz')):
        case = path.stem
        rows = matrix[case] = {}
        with np.load(path) as item:
            vertices, faces = item['reference'], item['reference_faces']
        case_dir = args.output / case
        case_dir.mkdir(exist_ok=True)
        meshes = {}
        for image in sorted((args.rgb / case).glob('*.png')):
            key = image.stem
            yaw = int(key.split('-')[0])
            camera = Camera(yaw, **CONFIG['main_camera_cm'])
            if yaw not in meshes:
                surface = visible_surface(raster, camera, vertices, faces, SIZE)
                if case.startswith('A_') and (case in ('A_high_mass', 'A_heldout_1') or yaw == 0):
                    path_out = case_dir / f'{yaw}.npz'
                    np.savez_compressed(path_out, depth_cm=surface.depth_cm, normal_right_up_toward=surface.normals,
                        mask=surface.mask, visible_triangle=surface.triangle, valid=surface.valid)
                meshes[yaw] = surface
            reference = meshes[yaw]
            rgb = np.asarray(Image.open(image).convert('RGBA'))
            pixels = rgb[..., 3] >= 128
            row = rows[key] = {'render_vs_raster_iou': float((pixels & reference.mask).sum() / (pixels | reference.mask).sum()),
                               'sha256_rgb': sha256(image.read_bytes()).hexdigest(),
                               'camera': camera.manifest(SIZE), 'observation_pose': 'native rest'}
            previous = args.predictions / case
            depth_file, normal_file = previous / f'{key}-depth.npy', previous / f'{key}-normal.npy'
            normal = dsine_to_camera(np.load(normal_file)) if normal_file.exists() else None
            domain = reference.valid
            train = domain & ((xx + yy) % 3 == 0)
            test = domain & ~train
            if depth_file.exists():
                raw = np.load(depth_file)
                row['depth'], _ = describe_depth(raw, reference, normal, camera, train, test)
            if normal is not None:
                row['normal'] = describe_normal(normal, reference)
            for kind, res in (('depth', 280), ('normal', 256)):
                file = previous / f'{key}-{kind}-{res}.npy'
                if file.exists():
                    data = np.load(file)
                    row[f'{kind}_{res}'] = (describe_depth(data, reference, normal, camera, train, test)[0]
                                            if kind == 'depth' else describe_normal(dsine_to_camera(data), reference))
        print(case, len(rows), flush=True)
    (args.output / 'quality.json').write_text(json.dumps(matrix, indent=2, allow_nan=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('refs', 'rgb', 'predictions', 'raster', 'output'):
        parser.add_argument(key, type=Path)
    main(parser.parse_args())
