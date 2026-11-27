"""Oracle anatomy controls on held-out surfaces in the native frame."""
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.optimize import lsq_linear
from scipy.spatial import cKDTree


REGIONS = ("shoulder_arm", "thorax", "abdomen", "pelvis_gluteal", "thigh", "lower_leg", "head")


def regions(points):
    x, y, _ = points.T
    return np.select(
        [y >= 6.4, (abs(x) >= 1.9) & (y >= 0), y >= 4.0, y >= 2.5, y >= 0.6, y >= -3.4],
        [6, 0, 1, 2, 3, 4], default=5,
    )


def statistics(distances, labels):
    def summary(group):
        if len(group) == 0:
            return None
        return {"mean_mm": float(group.mean() * 100), "p95_mm": float(np.percentile(group, 95) * 100), "samples": len(group)}
    return {"global": summary(distances), **{
        name: summary(distances[labels == i]) for i, name in enumerate(REGIONS)
    }}


def samples(vertices, faces, count, seed):
    rng = np.random.default_rng(seed)
    triangles = vertices[faces]
    a, b, c = triangles.transpose(1, 0, 2)
    areas = np.linalg.norm(np.cross(b - a, c - a), axis=1)
    ids = rng.choice(len(faces), count, p=areas / areas.sum())
    uv = rng.random((count, 2))
    uv = np.where(uv.sum(axis=1, keepdims=True) > 1, 1 - uv, uv)
    return a[ids] + uv[:, :1] * (b - a)[ids] + uv[:, 1:] * (c - a)[ids]


def procedural_fixture(amplitude):
    """Union of original ellipsoids, tessellated by marching tetrahedra."""
    parts = [
        ((0, 4.4, .2), (1.72, 1.82, .92)),
        ((0, 2.7, .15), (1.22 + amplitude, 1.55, .88 + amplitude)),
        ((0, 1.1, .12), (1.63, 1.42, .99)),
        ((0, 6.18, .31), (.54, .97, .53)),
        ((0, 7.42, .46), (.84, 1.10, .88)),
    ]
    for side in (-1, 1):
        parts.extend([
            ((side * 1.85, 4.35, .23), (.62, 1.29, .70)),
            ((side * 2.55, 3.45, .38), (.70, 1.12, .66)),
            ((side * 3.35, 2.55, .63), (.73, 1.11, .57)),
            ((side * 4.00, 1.71, 1.25), (.65, .76, .51)),
            ((side * 1.05, -.63, .13), (.92, 2.07, .97)),
            ((side * 1.39, -2.35, .10), (.77, 1.46, .78)),
            ((side * 1.63, -4.28, .09), (.72 + amplitude, 1.91, .79)),
            ((side * 1.89, -6.17, .04), (.56, 1.93, .61)),
            ((side * 2.06, -7.72, .48), (.67, .70, 1.05)),
        ])
    axes = [np.arange(lo, hi, .137) for lo, hi in ((-5.1, 5.2), (-8.7, 8.9), (-1.7, 2.3))]
    grid = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1)
    field = np.minimum.reduce([np.sum(((grid - c) / r) ** 2, axis=-1) - 1 for c, r in parts])
    offsets = np.array([(0,0,0), (1,0,0), (1,1,0), (0,1,0), (0,0,1), (1,0,1), (1,1,1), (0,1,1)])
    cubes = np.stack([field[i:i+len(axes[0])-1, j:j+len(axes[1])-1, k:k+len(axes[2])-1] for i,j,k in offsets])
    crossings = np.argwhere((cubes.min(axis=0) < 0) & (cubes.max(axis=0) > 0))
    vertices, faces, edge_ids = [], [], {}
    for corner in crossings:
        indices = corner + offsets
        values = field[tuple(indices.T)]
        points = grid[tuple(indices.T)]

        def edge(i, j):
            key = tuple(sorted((tuple(indices[i]), tuple(indices[j]))))
            if key not in edge_ids:
                edge_ids[key] = len(vertices)
                vertices.append(points[i] + (points[j] - points[i]) * values[i] / (values[i] - values[j]))
            return edge_ids[key]

        for tet in ((0,1,2,6), (0,2,3,6), (0,3,7,6), (0,7,4,6), (0,4,5,6), (0,5,1,6)):
            inside = [i for i in tet if values[i] < 0]
            outside = [i for i in tet if values[i] >= 0]
            if len(inside) in (0, 4):
                continue
            if len(inside) == 2:
                a, b, c, d = [edge(i, j) for i in inside for j in outside]
                facets = [(a, b, d), (a, d, c)]
            else:
                facets = [tuple(edge(i, j) for i in inside for j in outside)]
            for a, b, c in facets:
                normal = np.cross(vertices[b] - vertices[a], vertices[c] - vertices[a])
                faces.append((a, b, c) if normal @ (points[outside[0]] - points[inside[0]]) > 0 else (a, c, b))
    return np.asarray(vertices), np.asarray(faces)


def save_obj(path, vertices, triangles):
    with path.open("w") as stream:
        np.savetxt(stream, vertices, fmt="v %.9g %.9g %.9g")
        np.savetxt(stream, triangles + 1, fmt="f %d %d %d")


def sections(vertices, faces):
    """Horizontal cross sections at fixed native-frame levels."""
    from scipy.spatial import ConvexHull
    result = {}
    triangles = vertices[faces]
    for name, height in (("thorax", 4.05), ("abdomen", 2.7), ("pelvis", 1.1), ("thigh", -1.4), ("lower_leg", -5.0), ("head", 7.5)):
        points = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            a, b = triangles[:, i], triangles[:, j]
            mask = (a[:, 1] < height) != (b[:, 1] < height)
            a, b = a[mask], b[mask]
            points.extend((a + (b - a) * ((height - a[:, 1]) / (b[:, 1] - a[:, 1]))[:, None])[:, [0, 2]])
        xy = np.asarray(points).reshape(-1, 2)
        if name in ("thigh", "lower_leg"):
            xy = xy[xy[:, 0] > 0]
        else:
            xy = xy[abs(xy[:, 0]) < 1.85]
        result[name] = float(ConvexHull(xy).area * 100) if len(xy) >= 3 else None
    return result


def benchmark(base, triangles, macro, fields, body, out):
    from human3d.native_rig import validate_rebind

    out.mkdir()
    body_ids = np.unique(triangles)
    train = body_ids[::3]
    heldout = np.setdiff1d(body_ids, train)
    base_joints = validate_rebind(body, base)
    regional_design = fields[:, train].reshape(len(fields), -1).T
    macro_design = macro[:, train].reshape(len(macro), -1).T
    rows, fixtures = [], []
    x, y, z = base.T
    for kind, amplitudes in (("warp", (.12, -.10, .18, -.16)), ("proxy", (-.10, .16))):
        for index, amplitude in enumerate(amplitudes, 1):
            subject = f"{kind}{index:02}"
            if kind == "warp":
                truth = base.copy()
                truth[:, 0] += amplitude * x * np.exp(-((y - 1.2) / 2.3) ** 2)
                truth[:, 2] += amplitude * 2 * np.exp(-((y - .2) / 1.8) ** 2 - (x / 2.2) ** 2)
                truth[:, 1] += amplitude * .6 * np.tanh(y / 3)
                truth_faces = triangles
                truth_joints = validate_rebind(body, truth)
                observations = truth[train]
                eval_points = truth[heldout]
            else:
                truth, truth_faces = procedural_fixture(amplitude)
                truth_joints = None
                observed_tree = cKDTree(samples(truth, truth_faces, 80000, 201))
                observations = observed_tree.data[observed_tree.query(base[train])[1]]
                eval_points = samples(truth, truth_faces, 24000, 202)
            save_obj(out / f"{subject}_truth.obj", truth, truth_faces)
            reference_sections = sections(truth, truth_faces)
            fixtures.append({"subject": subject, "vertices": len(truth), "faces": len(truth_faces),
                             "section_perimeters_mm": reference_sections, "pose": "fixed native-frame proxy",
                             "registration": "fixed authored frame; no subject-specific transform",
                             "volume": None, "volume_reason": "benchmark does not establish comparable closed anatomical regions"})
            weights = lsq_linear(macro_design, (observations - base[train]).reshape(-1), bounds=(0, 1)).x
            endpoints = macro[:, train] + base[train]
            prototype = macro[np.argmin(np.mean(np.linalg.norm(endpoints - observations, axis=2), axis=1))]
            parametric = np.tensordot(weights, macro, axes=1)
            for method, start in (("neutral", np.zeros_like(base)), ("parametric", parametric),
                                  ("prototype", prototype), ("hybrid", (parametric + prototype) / 2)):
                initial = base + start
                started = perf_counter()
                fit = lsq_linear(regional_design, (observations - initial[train]).reshape(-1), bounds=(-.35, .35))
                if not fit.success:
                    raise RuntimeError(f"Regional solve failed: {subject} {method}")
                final = initial + np.tensordot(fit.x, fields, axes=1)
                seconds = perf_counter() - started
                save_obj(out / f"{subject}_{method}.obj", final, triangles)
                for phase, candidate in (("initial", initial), ("refined", final)):
                    tree = cKDTree(samples(candidate, triangles, 80000, 203))
                    d_target = tree.query(eval_points)[0]
                    d_candidate = cKDTree(eval_points).query(samples(candidate, triangles, len(eval_points), 204))[0]
                    candidate_samples = samples(candidate, triangles, len(eval_points), 204)
                    try:
                        joints = validate_rebind(body, candidate)
                        shift = max(np.linalg.norm(joints[k] - base_joints[k]) for k in joints) * 100
                        joint_error = max(np.linalg.norm(joints[k] - truth_joints[k]) for k in joints) * 100 if truth_joints else None
                        structural = {"status": "PASS", "maximum_joint_shift_mm": float(shift),
                                      "maximum_joint_error_mm": None if joint_error is None else float(joint_error)}
                    except ValueError as exc:
                        structural = {"status": "FAIL", "reason": str(exc)}
                    perimeters = sections(candidate, triangles)
                    rows.append({
                        "subject": subject, "method": method, "phase": phase,
                        "target_to_candidate": statistics(d_target, regions(eval_points)),
                        "candidate_to_target": statistics(d_candidate, regions(candidate_samples)),
                        "paired_heldout": statistics(np.linalg.norm(candidate[heldout] - truth[heldout], axis=1), regions(base[heldout])) if kind == "warp" else None,
                        "section_deviations_mm": {k: perimeters[k] - v if perimeters[k] is not None and v is not None else None for k, v in reference_sections.items()},
                        "native_rebind": structural, "uv": "native mesh indexing unchanged",
                        "refinement_seconds": seconds if phase == "refined" else None,
                    })
    return {"fixture_license": "Apache-2.0 original procedural generator",
            "observation_scope": "oracle native-frame 3D, no images; fixed nearest-point correspondences for proxy",
            "distance_scope": "bidirectional nearest sampled surface estimates, not exact point-to-triangle distances",
            "section_scope": "convex-hull cross-section proxies at fixed levels",
            "proxy_limitation": "abstract unrigged ellipsoid union; unresolved pose and anatomical landmark mismatch",
            "warp_training_vertices": len(train), "warp_heldout_vertices": len(heldout),
            "fixtures": fixtures, "rows": rows}
