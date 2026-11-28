"""Run G5 interventions against an independently recorded qualified Engine B baseline."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import resource
from time import perf_counter

import cv2
import numpy as np

from baseline import engine_b
from evidence import CONFIG, SIZE, angles, visible_surface
from lab_search import bounded_fit
from observations import DenseLoss, admit, make_maps, observation_vertices
from projection import Raster
from refinement import direct_fit, refine
from human3d.experimental import NativeBasis
from projection import Camera
from human3d.frozen_body import load_project_body
from human3d.native_rig import validate_rebind
from human3d.session import Session

MATRIX = {'D1': ('oracle', ('depth',)), 'D2': ('oracle', ('normal',)),
          'D3': ('oracle', ('depth', 'normal')), 'D4': ('predicted', ('depth',)),
          'D5': ('predicted', ('normal',)), 'D6': ('predicted', ('depth', 'normal'))}


def modify_camera(camera, perturbation):
    field, amount = perturbation.split(':')
    amount = float(amount)
    if field == 'perspective':
        return replace(camera, perspective=bool(amount))
    return replace(camera, **{field: getattr(camera, field) + amount})


def reprojection(raster, vertices, faces, targets, names):
    rows = {}
    for yaw in names:
        camera = Camera(yaw, **CONFIG['main_camera_cm'])
        target = targets[yaw]
        predicted = visible_surface(raster, camera, vertices * 10, faces, SIZE)
        common = target.valid & predicted.valid
        from human3d.experimental import ContourLoss
        cost, iou = ContourLoss(target.mask, SIZE, 0)(predicted.mask)
        rows[str(yaw)] = {'iou': iou, 'contour_composite': cost,
            'common_pixels': int(common.sum()), 'depth_mae_mm':
            float(np.abs(target.depth_cm[common] - predicted.depth_cm[common]).mean() * 10) if common.any() else None,
            'normal_mean_deg': float(angles(target.normals[common], predicted.normals[common]).mean())
            if common.any() else None}
    return rows


def subject(args):
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    folder = args.baseline
    projection_mode = 'estimated' if args.estimated else 'calibrated'
    if args.views != CONFIG['main_views']:
        folder = output / 'baseline'
    if (folder / 'D0.npy').exists():
        neutral = np.load(folder / 'D0.npy')
        report = json.loads((folder / 'attempt.json').read_text())
        session = Session(folder / 'project')
        angles_by_id = {photo.id: int(Path(photo.name).stem) for photo in session.store.load().photos.photos}
        seed = report['diagnostics']['metrics']['anatomical_controls']
        fit = report['diagnostics']['metrics']['engine_b_fitting']
    else:
        neutral, seed, fit, report, session, angles_by_id = engine_b(
            args.runtime, args.rgb, folder, num_views=args.views, estimated=args.estimated)
        np.save(folder / 'D0.npy', neutral)
    raster = Raster(args.raster)
    body = load_project_body(session.store)
    basis = NativeBasis(args.runtime, body)
    views, cameras, registration = admit(body, basis, session, angles_by_id, folder, args.estimated)
    if args.perturb:
        cameras = {key: modify_camera(value, args.perturb) for key, value in cameras.items()}
        views = [replace(view, project=lambda v, n, camera=cameras[view.id]: camera.project(v * 10, n)[:, :2])
                 for view in views]
        neutral, seed, _, fit = bounded_fit(basis, body, views, lambda: None)
    with np.load(args.reference, allow_pickle=False) as loaded:
        reference, ref_faces, faces = (loaded[key].copy() for key in ('reference', 'reference_faces', 'faces'))
    init = perf_counter()
    exact, predicted, maps = make_maps(raster, neutral, faces, views, cameras, reference, ref_faces, angles_by_id,
                                      args.predictions, args.rgb, body, args.estimated)
    fits = {'D0': neutral, 'initial': basis.evaluate({})}
    metrics = {'D0': fit, 'registration': registration,
               'view_order': [angles_by_id[view.id] for view in views],
               'mode': projection_mode, 'perturbation': args.perturb, 'normal_convention': 'physical-outward-v2',
               'attempt_stages': report['diagnostics']['stages'],
               'normal_intrinsics': args.normal_intrinsics,
               'photo_ids': {view.id: angles_by_id[view.id] for view in views},
               'alignment_and_preprocess_seconds': perf_counter() - init}
    if args.resume and (output / 'fit.json').exists():
        previous = json.loads((output / 'fit.json').read_text())
        for name, row in previous.items():
            if name not in metrics:
                metrics[name] = row
        with np.load(output / 'meshes.npz') as recorded:
            fits.update({name: recorded[name] / 10 for name in recorded.files
                         if name not in ('reference', 'reference_faces', 'faces', 'D0', 'initial')})
    if args.parity:
        replay, _, _, _ = bounded_fit(basis, body, views, lambda: None)
        error_mm = float(np.max(np.abs(replay - neutral))) * 100
        metrics['schedule_parity_max_mm'] = error_mm
        if error_mm > 1e-8:
            raise ValueError(f'G5 no-extra control diverges from Engine B by {error_mm} mm')
    for key in args.matrix:
        if key not in MATRIX:
            continue
        family, components = MATRIX[key]
        evidence = exact if family == 'oracle' else predicted
        if any(any(term not in evidence[view.id] for term in components) for view in views):
            metrics[key] = {'status': 'unavailable model or alignment'}
            continue
        dense = DenseLoss(raster, faces, cameras, evidence, components, args.estimated)
        start = perf_counter()
        snapshots = {} if key == 'D3' else None
        points, controls, iou, measured = bounded_fit(basis, body, views, lambda: None, dense, snapshots)
        metrics[key] = measured | {'seconds': perf_counter() - start, 'controls': controls, 'fit_iou': iou}
        metrics[key]['components'] = {str(angles_by_id[view.id]): dense.components(
             view, observation_vertices(body, points, view), 160) for view in views}
        fits[key] = points
        if snapshots:
            fits.update({f'{key}_{stage}': value for stage, value in snapshots.items()})
        print(args.reference.stem, projection_mode, key, metrics[key]['seconds'], flush=True)
    if not args.estimated and not args.perturb:
        for key, source, observations in (('D7', 'D3', exact), ('D8', 'D6', predicted), ('L0', 'D0', exact)):
            if key in args.matrix and source in fits:
                fits[key], metrics[key] = refine(body, fits[source], faces, views, cameras, observations,
                                                 raster, photograph_only=key == 'L0')
    if 'D9' in args.matrix:
        fits['D9'], metrics['D9'] = direct_fit(basis, body, faces, reference, ref_faces, seed,
                                               args.reference.stem.startswith('A_'))
    holdouts = CONFIG['holdout_yaw_deg']
    for yaw in holdouts:
        maps[yaw] = visible_surface(raster, Camera(yaw, **CONFIG['main_camera_cm']),
                                    reference, ref_faces, SIZE)
    for key, points in fits.items():
        if key not in metrics:
            metrics[key] = {}
        start = perf_counter()
        try:
            validate_rebind(body, points)
            metrics[key]['rebind'] = 'pass'
        except ValueError as error:
            metrics[key]['rebind'] = str(error)
        metrics[key]['validation_s'] = perf_counter() - start
        metrics[key]['heldout'] = reprojection(raster, points, faces, maps, holdouts)
    metrics['peak_rss_kib_linux'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    np.savez_compressed(output / 'meshes.npz', reference=reference, reference_faces=ref_faces, faces=faces,
                        **{key: points * 10 for key, points in fits.items()})
    (output / 'fit.json').write_text(json.dumps(metrics, indent=2, allow_nan=False))
    print(args.reference.stem, projection_mode, 'saved', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ('runtime', 'rgb', 'reference', 'predictions', 'raster', 'baseline', 'output'):
        parser.add_argument(argument, type=Path)
    parser.add_argument('--estimated', action='store_true')
    parser.add_argument('--views', type=int, choices=(1, 2, 4, 8), default=CONFIG['main_views'])
    parser.add_argument('--matrix', nargs='+', default=list(MATRIX) + ['D7', 'D8', 'D9', 'L0'])
    parser.add_argument('--perturb')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--parity', action='store_true')
    parser.add_argument('--normal-intrinsics', default='synthetic calibrated')
    cv2.setNumThreads(1)
    subject(parser.parse_args())
