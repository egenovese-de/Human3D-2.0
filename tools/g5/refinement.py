"""Bounded, smoothed normal displacement and direct-geometry controls."""
from time import perf_counter

import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import coo_matrix, diags
from scipy.spatial import cKDTree

from evidence import CONFIG, angles, face_normals, unit, visible_surface
from human3d.native_rig import validate_rebind
from observations import observation_vertices


def refine(body, vertices, faces, views, cameras, evidence, raster, photograph_only=False):
    start = perf_counter()
    cm = vertices * 10
    area = np.cross(cm[faces[:, 1]] - cm[faces[:, 0]], cm[faces[:, 2]] - cm[faces[:, 0]])
    normal = np.zeros_like(cm)
    for index in faces.T:
        np.add.at(normal, index, area)
    normal = unit(normal)
    accum, weight = np.zeros(len(cm)), np.zeros(len(cm))
    size = CONFIG['image_size']
    for view in views:
        projection = cameras[view.id]
        points = observation_vertices(body, vertices, view) * 10
        candidate = visible_surface(raster, projection, points, faces, size)
        if photograph_only:
            from scipy.ndimage import distance_transform_edt
            rows, cols = np.indices(candidate.mask.shape)
            mask = cv2.resize(view.mask.astype(np.uint8), (size, size), interpolation=cv2.INTER_NEAREST_EXACT).astype(bool)
            _, nearest = distance_transform_edt(~mask, return_indices=True)
            outside = candidate.mask & ~mask & (candidate.triangle >= 0)
            face = candidate.triangle[outside]
            dy = nearest[0][outside] - rows[outside]
            dx = nearest[1][outside] - cols[outside]
            input_xy = face_normals(points, faces)[face] @ projection.axes()[:2].T
            slope = np.linalg.norm(input_xy, axis=1)
            displacement = (dx * input_xy[:, 0] - dy * input_xy[:, 1]) * projection.span / size
            reliability = np.clip(slope, 0, 1)
        else:
            maps = evidence[view.id]
            selected = candidate.valid & maps['depth'].valid & maps['normal'].valid
            if not selected.any():
                continue
            face = candidate.triangle[selected]
            face_camera = candidate.normals[selected]
            depth_difference = candidate.depth_cm[selected] - maps['depth'].values[selected]
            consistency = angles(face_camera, maps['normal'].values[selected])
            yy, xx = np.nonzero(selected)
            focal = size * projection.distance / projection.span
            ray = np.c_[-(xx + .5 - size * (.5 + projection.dx)) / focal,
                        (yy + .5 - size * (.5 + projection.dy)) / focal, np.ones(len(xx))]
            slope = (face_camera * ray).sum(axis=1)
            displacement = depth_difference * slope
            reliability = np.clip(slope, 0, 1) / (1 + (consistency / 30) ** 2)
        for index in faces[face].T:
            np.add.at(accum, index, np.clip(displacement, -2, 2) * reliability)
            np.add.at(weight, index, reliability)
    pairs = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges = np.unique(np.concatenate([pairs, pairs[:, ::-1]]), axis=0)
    adjacency = coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])),
                           shape=(len(cm), len(cm))).tocsr()
    smooth = diags(1 / np.maximum(np.asarray(adjacency.sum(1)).ravel(), 1)) @ adjacency
    offsets = accum / (weight + 3)
    for _ in range(12):
        offsets = .35 * offsets + .65 * (smooth @ offsets)
    offsets = np.clip(offsets, -CONFIG['local_max_mm'] / 10, CONFIG['local_max_mm'] / 10)
    output = vertices + offsets[:, None] * normal / 10
    rejection = None
    try:
        validate_rebind(body, output)
        after = face_normals(output, faces)
        before = face_normals(vertices, faces)
        strong = np.linalg.norm(area, axis=1) > 1e-4
        if np.any((after[strong] * before[strong]).sum(1) <= 0):
            raise ValueError('local face normal inversion')
    except ValueError as error:
        rejection = str(error)
        output = vertices
    return output, {'seconds': perf_counter() - start, 'rejection': rejection,
                    'max_proposed_mm': float(np.abs(offsets).max() * 10),
                    'moved_vertices': int((np.linalg.norm(output - vertices, axis=1) > 1e-10).sum())}


def direct_fit(basis, body, faces, reference, reference_faces, seed, same_topology):
    """Bounded direct fit. Independent vertices use bidirectional sample ICP."""
    rng = np.random.default_rng(41)
    ids = np.unique(faces)
    idx = rng.choice(ids, size=min(1300, len(ids)), replace=False)
    names = list(basis.globals) + list(basis.regional)
    lower = [(.49 if n == 'Age' else .10) if n in basis.globals else -.65 for n in names]
    upper = [.90 if n in basis.globals else .65 for n in names]
    initial = np.clip([seed[n] for n in names], lower, upper)
    truth = reference[idx] / 10 if same_topology else reference[np.unique(reference_faces)] / 10
    model = lambda x: basis.evaluate(dict(zip(names, x)))
    start = perf_counter()
    calls = 0
    if same_topology:
        result = least_squares(lambda x: (model(x)[idx] - truth).ravel(), initial,
                               bounds=(lower, upper), max_nfev=30, diff_step=1e-3)
        values, calls = result.x, result.nfev
    else:
        target = cKDTree(truth)
        probes = truth[rng.choice(len(truth), min(2500, len(truth)), replace=False)]
        values = initial
        for _ in range(4):
            points = model(values)
            dist, match = target.query(points[idx])
            _, reverse = cKDTree(points[ids]).query(probes)
            result = least_squares(lambda x: np.r_[(model(x)[idx] - truth[match]).ravel(),
                                                  (model(x)[ids[reverse]] - probes).ravel()],
                                   values, bounds=(lower, upper), loss='soft_l1', f_scale=.1,
                                   max_nfev=7, diff_step=1e-3)
            values, calls = result.x, calls + result.nfev
    proposed = model(values)
    rejection = None
    accepted_fraction = 1.
    try:
        validate_rebind(body, proposed)
    except ValueError as error:
        rejection = str(error)
        lo, hi = 0., 1.
        for _ in range(10):
            alpha = (lo + hi) / 2
            try:
                validate_rebind(body, model(initial + alpha * (values - initial)))
            except ValueError:
                hi = alpha
            else:
                lo = alpha
        accepted_fraction = lo
        proposed = model(initial + lo * (values - initial))
    return proposed, {'seconds': perf_counter() - start, 'solver_steps': calls,
                      'rejected_full_candidate': rejection, 'accepted_fraction': accepted_fraction,
                      'objective': 'direct correspondence' if same_topology else 'approximate bidirectional vertex ICP'}
