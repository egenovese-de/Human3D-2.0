"""P3 prompt replay and P4 anatomy-to-asset synthetic comparison."""
import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import numpy as np
from PIL import Image, ImageDraw
from scipy.optimize import lsq_linear
from scipy.spatial import ConvexHull

from bootstrap import ROOT, digest
from human3d.alignment import Alignment, Camera
from human3d.bootstrap import MORPH_ASSETS, TORSO_ASSETS, _mesh, _morph_targets, _rig
from human3d.fitting import _optimize, _scorer, length_controls, morph_controls, regional_controls
from human3d.frozen_body import deform_vertices, load_frozen_body
from human3d.native_rig import pose_transforms, skin_vertices, validate_pose, validate_rebind
from human3d.usd_export import export_body
from x_p1_regions import topology
from x_p2 import SOURCE, distances, field, load_assets, region_masks

VIEWS = ("front", "side", "threequarter")
SUBJECTS = tuple(f"subject{i:02}" for i in range(1, 5))
MODES = ("A", "B", "C", "D", "E", "S")
CATEGORIES = {"tapered": .74, "moderate": .875, "straight": 1.02}
ORDINAL = {1: .65, 2: .75, 3: .85, 4: .95, 5: 1.05}
KEYS = ("front_upper", "front_hip", "side_upper", "side_hip", "front_ratio", "side_ratio")


def strict(obj, names):
    if type(obj) is not dict or set(obj) != set(names):
        raise ValueError(f"Expected keys {names}")
    return obj


def number(value, lo, hi):
    if type(value) not in (int, float) or not lo <= value <= hi:
        raise ValueError(f"Numeric value outside [{lo}, {hi}]")


def prediction(obj, lower, upper):
    if obj is None:
        return None
    strict(obj, ("value", "lo", "hi"))
    for value in obj.values():
        number(value, lower, upper)
    if not obj["lo"] <= obj["value"] <= obj["hi"]:
        raise ValueError("Interval does not contain point estimate")
    return (obj["value"], max((obj["hi"] - obj["lo"]) / 2, .005), obj["lo"], obj["hi"])


def label(obj, values):
    if obj is None:
        return None
    strict(obj, ("value", "confidence"))
    if type(obj["value"]) is not type(next(iter(values))) or obj["value"] not in values:
        raise ValueError("Invalid class or ordinal")
    number(obj["confidence"], 0, 1)
    return (values[obj["value"]], .12 - .06 * obj["confidence"], None, None)


def normalized(root):
    data = {}
    for specialized, filename in ((False, "unified.raw.json"), (True, "specialized.raw.json")):
        rows = json.loads((root / filename).read_text())
        expected = {(s, v) for s in SUBJECTS for v in VIEWS}
        for row in rows:
            keys = ("upper", "hip") if specialized else ("A", "B", "C", "D", "E")
            strict(row, ("subject", "view", *keys))
            subject, view = row["subject"], row["view"]
            expected.remove((subject, view))
            if specialized:
                methods = {"S": {f"{view}_{k}": prediction(row[k], .05, .50) for k in keys}}
            else:
                fallback = strict(row["D"], ("ratio", "ordinal"))
                e = strict(row["E"], ("upper", "hip"))
                d_ratio = prediction(fallback["ratio"], .4, 1.4)
                d_label = label(fallback["ordinal"], ORDINAL)
                methods = {
                    "A": {f"{view}_ratio": label(row["A"], CATEGORIES)},
                    "B": {f"{view}_ratio": label(row["B"], ORDINAL)},
                    "C": {f"{view}_ratio": prediction(row["C"], .4, 1.4)},
                    "D": {f"{view}_ratio": d_ratio or d_label},
                    "E": {f"{view}_{k}": prediction(e[k], .05, .50) for k in e},
                }
            for method, obs in methods.items():
                available = {key: value for key, value in obs.items() if value is not None}
                if not available.keys() <= set(KEYS):
                    raise ValueError("Nonorthogonal view cannot supply cross sections")
                data[subject, view, method] = available
        if expected:
            raise ValueError("Missing response rows")
    return data


def section(points, faces, height, center, horizontal):
    tri = points[faces]
    pieces = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        a, b = tri[:, i], tri[:, j]
        crosses = (a[:, 1] < height) != (b[:, 1] < height)
        a, b = a[crosses], b[crosses]
        points = a + (b - a) * ((height - a[:, 1]) / (b[:, 1] - a[:, 1]))[:, None]
        pieces.append(points[:, [0, 2]])
    shell = np.concatenate(pieces)
    shell = shell[abs(shell[:, 0] - center) < horizontal]
    return np.array([*np.ptp(shell, axis=0), ConvexHull(shell).area])


def features(points, faces, ids):
    sole = points[ids, 1].min()
    height = np.ptp(points[ids, 1])
    upper = section(points, faces, sole + .67 * height, 0, .145 * height)
    hip = section(points, faces, sole + .55 * height, 0, .16 * height)
    return np.array([upper[0] / height, hip[0] / height, upper[1] / height,
                     hip[1] / height, upper[0] / hip[0], upper[1] / hip[1]]), [upper[2] * 100, hip[2] * 100]


def silhouette(points, faces, camera):
    image = Image.new("1", (256, 256))
    draw = ImageDraw.Draw(image)
    p = [camera.project(v) for v in points]
    for face in faces:
        draw.polygon([(p[i].real, p[i].imag) for i in face], fill=1)
    return image


def mask_features(image):
    mask = np.asarray(image)
    visible = np.flatnonzero(mask.any(axis=1))
    height = len(range(visible[0], visible[-1] + 1))
    values = []
    for fraction in (.67, .55):
        y = round(visible[-1] - fraction * (height - 1))
        line = mask[y]
        hits = np.flatnonzero(line)
        groups = np.split(hits, np.flatnonzero(np.diff(hits) > 1) + 1)
        width = len(min(groups, key=lambda g: abs(g.mean() - 128)))
        values.append(width / height)
    return values


def design(base, fields, faces, ids):
    neutral, _ = features(base, faces, ids)
    gradient = np.stack([(features(base + .15 * v, faces, ids)[0] -
                         features(base - .15 * v, faces, ids)[0]) / .30 for v in fields], axis=1)
    return neutral, gradient


def fit_features(base, fields, model, obs, anchor=None):
    neutral, gradient = model
    anchor = np.zeros(len(fields)) if anchor is None else anchor
    if not obs:
        return base + np.tensordot(anchor, fields, axes=1)
    idx = [KEYS.index(key) for key in obs]
    target = np.array([row[0] for row in obs.values()])
    sigma = np.array([row[1] for row in obs.values()])
    fit = lsq_linear(np.vstack((gradient[idx] / sigma[:, None], np.eye(len(fields)))),
                     np.r_[(target - neutral[idx]) / sigma, anchor], bounds=(-.55, .55))
    if not fit.success:
        raise ValueError("Bounded evidence fit failed")
    return base + np.tensordot(fit.x, fields, axes=1)


def truth_warp(base, amplitude):
    """P1 independent deformation, reproduced from its pinned procedural generator."""
    x, y, _ = base.T
    points = base.copy()
    points[:, 0] += amplitude * x * np.exp(-((y - 1.2) / 2.3) ** 2)
    points[:, 2] += amplitude * 2 * np.exp(-((y - .2) / 1.8) ** 2 - (x / 2.2) ** 2)
    points[:, 1] += amplitude * .6 * np.tanh(y / 3)
    return points


def load_scene(runtime):
    revision, a = load_assets(runtime, "foundation", "DOCS/manifests/makehuman-v1.3.0.json")
    _, torso = load_assets(runtime, "anatomical_torso", "lab/manifests/makehuman-anatomical-torso.json")
    _, local = load_assets(runtime, "p1_anatomy", "lab/manifests/makehuman-p1-anatomy.json")
    _, m6 = load_assets(runtime, "morph02", "DOCS/manifests/makehuman-morph02.json")
    mesh = _mesh(a["base"].read_text())
    rig = _rig(json.loads(a["default"].read_text()), json.loads(a["default_weights"].read_text()), mesh["vertices"])
    morphs = {}
    for name, expected in (MORPH_ASSETS | TORSO_ASSETS).items():
        path = (m6 | a)[Path(name).stem]
        if digest(path) != expected:
            raise ValueError(f"M6 native morph revision mismatch: {name}")
        morphs[name] = path.read_bytes()
    vertices = np.asarray(mesh["vertices"])
    body = {"mesh": mesh, "rig": rig, "morph_targets": _morph_targets(morphs, len(vertices))}
    polygons = [[i for i, _ in f["corners"]] for f in mesh["faces"] if f["group"] == "body"]
    triangles = np.asarray([[f[0], f[i], f[i + 1]] for f in polygons for i in range(1, len(f) - 1)])
    paths = torso | local
    expanded = np.asarray([field(paths[f"{key}-incr"], len(vertices)) for key in
                          ("hip-scale-horiz", "torso-scale-horiz", "torso-scale-depth", "torso-vshape",
                           "stomach-tone", "buttocks-volume", "pelvis-tone")])
    return revision, body, vertices, polygons, triangles, expanded


def stable(body, base, proposed):
    for scale in (1., .75, .5, .25, 0.):
        points = base + scale * (proposed - base)
        try:
            validate_rebind(body, points)
        except ValueError:
            continue
        return points, scale
    raise ValueError("Neutral anatomy fails rig validation")


def posed(body, points, plan):
    rig = body["rig"]
    rebound = validate_rebind(body, points)
    result = skin_vertices(points, rig["skin"], pose_transforms(rig, rebound, plan))
    validate_pose(body, points, result)
    return result


def m6_calibrated(body, base, images, cameras):
    """Exercise the native M6 shared silhouette objective with known cameras."""
    masks = {}
    alignments = {}
    for name, image, camera in zip(VIEWS, images, cameras):
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        masks[name] = SimpleNamespace(png=buffer.getvalue())
        alignments[name] = Alignment(camera, 0, {})
    score = _scorer(body, masks, alignments, base)
    coarse = _scorer(body, masks, alignments, base, edge=128)
    available = (*morph_controls(body), *length_controls(body), *regional_controls(body))
    seed, _ = _optimize(body, coarse, {}, available, (.25,))
    baseline = np.mean(tuple(score(base).values()))
    if np.mean(tuple(score(deform_vertices(body, seed)).values())) < baseline:
        seed = {}
    controls, scores = _optimize(body, score, seed, available, (.25, .125))
    if np.mean(tuple(scores.values())) < baseline:
        return {}
    return controls


def asset_check(out, name, body, points, cameras, ids):
    from pxr import Gf, Usd, UsdGeom, UsdSkel

    rebound = validate_rebind(body, points)
    frozen = {"schema_version": 1, "kind": "frozen_body", "mesh": body["mesh"] | {"vertices": points.tolist()},
              "rig": body["rig"] | {"joints": {k: v.tolist() for k, v in rebound.items()}}, "morph_targets": {}}
    out = out / name
    out.mkdir()
    payload = json.dumps(frozen, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    path = out / (hashlib.sha256(payload).hexdigest() + ".json")
    path.write_bytes(payload)
    restored = load_frozen_body(path)
    original_hash = digest(path)
    ranges = []
    files = []
    for index, camera in enumerate(cameras):
        export_path = out / f"{name}-pose{index+1}.usdz"
        expected = posed(restored, points, camera)[ids]
        export_body(export_path, restored, SimpleNamespace(controls={}), camera, texture=Image.new("RGB", (32, 32), (175, 175, 175)))
        stage = Usd.Stage.Open(str(export_path))
        mesh = UsdGeom.Mesh.Get(stage, "/Human/Body")
        skeleton = UsdSkel.Skeleton.Get(stage, "/Human/Rig")
        uv = UsdGeom.PrimvarsAPI(mesh).GetPrimvar("st")
        weights = np.asarray(UsdSkel.BindingAPI(mesh.GetPrim()).GetJointWeightsPrimvar().Get()).reshape(len(ids), -1)
        points_attr = mesh.GetPointsAttr().Get()
        canonical_error = float(np.max(np.linalg.norm(np.asarray(points_attr) - points[ids], axis=1)) * 100)
        cache = UsdSkel.Cache()
        if not cache.Populate(UsdSkel.Root.Get(stage, "/Human"), Usd.PrimDefaultPredicate):
            raise ValueError(f"USDZ skeleton cache invalid: {name}")
        transforms = cache.GetSkelQuery(skeleton).ComputeSkinningTransforms(Usd.TimeCode.Default())
        if not cache.GetSkinningQuery(mesh.GetPrim()).ComputeSkinnedPoints(transforms, points_attr, Usd.TimeCode.Default()):
            raise ValueError(f"USDZ skinning evaluation failed: {name}")
        actual = np.asarray(points_attr)
        error = float(np.max(np.linalg.norm(actual - expected, axis=1)) * 100)
        if max(error, canonical_error) > .001 or len(skeleton.GetJointsAttr().Get()) != len(body["rig"]["bones"]) or len(uv.GetIndices()) != 53512:
            raise ValueError(f"USDZ roundtrip failed: {name}")
        if not np.allclose(weights.sum(axis=1), 1, atol=1e-6) or original_hash != digest(path):
            raise ValueError(f"USDZ skin or canonical independence failed: {name}")
        original_export = digest(export_path)
        stage.SetEditTarget(stage.GetSessionLayer())
        editable = mesh.GetPointsAttr().Get()
        initial = editable[0]
        editable[0] = initial + Gf.Vec3f(.01, 0, 0)
        if not mesh.GetPointsAttr().Set(editable) or mesh.GetPointsAttr().Get()[0] == initial:
            raise ValueError(f"USDZ session-layer editing failed: {name}")
        if not cache.GetSkinningQuery(mesh.GetPrim()) or original_export != digest(export_path):
            raise ValueError(f"Editing changed USDZ archive or invalidated skinning: {name}")
        ranges.append(error)
        files.append({"name": f"{name}/{export_path.name}", "sha256": original_export, "session_editable": True})
    if np.max(np.linalg.norm(posed(restored, points, cameras[0]) - posed(restored, points, cameras[1]), axis=1)) < .01:
        raise ValueError(f"Downstream poses have no distinct effect: {name}")
    return {"frozen_sha256": original_hash, "frozen": f"{name}/{path.name}", "export_max_mm": max(ranges), "exports": files}


def peak_resident_bytes():
    import sys

    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "peak_working_set", "working_set", "peak_paged", "paged",
                    "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile")
            ]

        counters = Counters()
        counters.size = ctypes.sizeof(counters)
        process = ctypes.WinDLL("kernel32").GetCurrentProcess
        process.restype = wintypes.HANDLE
        get_info = ctypes.WinDLL("psapi").GetProcessMemoryInfo
        get_info.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
        if not get_info(process(), ctypes.byref(counters), counters.size):
            raise OSError("Unable to read process peak working set")
        return int(counters.peak_working_set)
    import resource
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024))


def run(runtime, out):
    start = perf_counter()
    root = ROOT / "lab/fixtures/x-vlm"
    observations = normalized(root)
    revision, body, base, polygons, faces, fields = load_scene(runtime)
    ids = np.unique(faces)
    masks = {"global": np.ones(len(ids), dtype=bool), **region_masks(base[ids])}
    model = design(base, fields, faces, ids)
    front, side = (Camera(yaw, 12, 128+128j, 1) for yaw in (0, 90))
    downstream = (Alignment(front, 0, {"lowerarm01.L": -1.1}), Alignment(front, 0, {"lowerarm01.R": .7}))
    truth = {s: truth_warp(base, a) for s, a in zip(SUBJECTS, (.12, -.10, .18, -.16))}
    metadata = {p.name: digest(p) for p in root.iterdir() if p.is_file()}
    p3 = []
    count_controls = []
    predicted = {}
    for subject, target in truth.items():
        actual = dict(zip(KEYS, features(target, faces, ids)[0]))
        for method in MODES:
            for fusion in ("front", "fused"):
                obs = observations[subject, "front", method].copy()
                if fusion == "fused":
                    obs.update(observations[subject, "side", method])
                    obs.update(observations[subject, "threequarter", method])
                begin = perf_counter()
                estimate, scale = stable(body, base, fit_features(base, fields, model, obs))
                predicted[subject, method, fusion] = estimate
                p3.append({"subject": subject, "method": method, "fusion": fusion,
                           "observed_fields": {key: {"value": v[0], "signed_error": v[0] - actual[key],
                                                     "interval_hit": None if v[2] is None else bool(v[2] <= actual[key] <= v[3]),
                                                     "interval_width": None if v[2] is None else v[3] - v[2]}
                                               for key, v in obs.items()},
                           "surface": distances(estimate[ids], target[ids], masks),
                           "rebind_scale": scale, "fit_seconds": perf_counter() - begin})
    selected = min(MODES, key=lambda method: np.mean([r["surface"]["global"]["mean_mm"] for r in p3
                                                     if r["subject"] in SUBJECTS[:2] and r["method"] == method and r["fusion"] == "fused"]))
    for subject in SUBJECTS:
        for count in (1, 2, 4, 8, 15, 30):
            # Replay duplicate exact view hashes with controlled ordering.
            views = [VIEWS[i % len(VIEWS)] for i in range(count)]
            distinct = list(dict.fromkeys(views))
            obs = {k: v for view in distinct for k, v in observations[subject, view, selected].items()}
            estimate, _ = stable(body, base, fit_features(base, fields, model, obs))
            expected = predicted[subject, selected, "front" if count == 1 else "fused"]
            if not np.array_equal(estimate, expected):
                raise ValueError("Duplicated view changed the fused anatomy")
            count_controls.append({"subject": subject, "count": count, "unique_views": len(distinct),
                                   "observed_fields": sorted(obs), "same_geometry_at_same_evidence": True})
    out.mkdir(parents=True, exist_ok=False)
    assets = out / "assets"
    assets.mkdir()
    p4 = []
    geometry = {}
    for subject in SUBJECTS[2:]:
        target = truth[subject]
        geometry[f"{subject}-truth"] = target[ids].tolist()
        actual, circumference = features(target, faces, ids)
        truth_volume = topology(target, faces)["volume_l"]
        target_mask = [silhouette(target, polygons, camera) for camera in (front, side)]
        front_features = mask_features(target_mask[0])
        side_features = mask_features(target_mask[1])
        mask_observations = {k: (v, .025) for k, v in zip(KEYS[:4], front_features + side_features)}
        oracle_ids = ids[::3]
        dd = fields[:, oracle_ids].reshape(len(fields), -1).T
        begin_native = perf_counter()
        native_controls = m6_calibrated(body, base, target_mask, (front, side))
        native_seconds = perf_counter() - begin_native
        native_points = np.asarray(deform_vertices(body, native_controls))
        macro_fields = fields[:4]
        initial = fit_features(base, macro_fields, (model[0], model[1][:, :4]), mask_observations)
        regional = fit_features(initial, fields[4:], (features(initial, faces, ids)[0], model[1][:, 4:]), mask_observations)
        variants = {
            "A": native_points,
            "B": initial,
            "C": regional,
            "D": base + np.tensordot(lsq_linear(dd, (target-base)[oracle_ids].reshape(-1), bounds=(-.55, .55)).x, fields, axes=1),
            "E": predicted[subject, selected, "fused"],
        }
        for mode, candidate in variants.items():
            begin = perf_counter()
            points, scale = stable(body, base, candidate)
            errors = distances(points[ids], target[ids], masks)
            test_ids = np.setdiff1d(ids, oracle_ids)
            heldout = np.linalg.norm((points - target)[test_ids], axis=1) * 100
            _, girth = features(points, faces, ids)
            volume = topology(points, faces)["volume_l"]
            poses = [distances(posed(body, points, pose)[ids], posed(body, target, pose)[ids], masks)
                     for pose in downstream]
            iou = {}
            for view, camera, observed in zip(VIEWS, (front, side), target_mask):
                x, y = np.asarray(silhouette(points, polygons, camera)), np.asarray(observed)
                iou[view] = float(np.count_nonzero(x & y) / np.count_nonzero(x | y))
            name = f"{subject}-{mode.lower()}"
            geometry[name] = points[ids].tolist()
            asset = asset_check(assets, name, body, points, downstream, ids)
            p4.append({"subject": subject, "mode": mode, "canonical": errors,
                       "heldout_mean_mm": float(heldout.mean()), "heldout_p95_mm": float(np.percentile(heldout, 95)),
                       "circumference_delta_mm": [x-y for x,y in zip(girth, circumference)],
                       "volume_delta_l": None if volume is None or truth_volume is None else volume-truth_volume,
                       "proportion_delta": dict(zip(KEYS, features(points, faces, ids)[0] - actual)),
                       "silhouette_iou": iou, "posed": poses, "rebind_scale": scale, "asset": asset,
                       "check_seconds": perf_counter() - begin, "m6_controls": native_controls if mode == "A" else None,
                       "m6_fit_seconds": native_seconds if mode == "A" else None})
    out.joinpath("metrics.json").write_text(json.dumps({"source_revision": SOURCE, "asset_revision": revision,
         "image_and_prompt_hashes": metadata, "origin": "ChatGPT interactive visual observation, manually recorded; no isolated API inference",
         "schema_valid_records": 24, "normalized_mode_records": len(observations), "reference_count_controls": count_controls,
         "p3": p3, "p4": p4, "selection_subjects": SUBJECTS[:2],
         "heldout_subjects": SUBJECTS[2:], "selected_method": selected, "runtime_seconds": perf_counter() - start,
         "peak_resident_bytes": peak_resident_bytes()},
         indent=2, allow_nan=False)+"\n")
    out.joinpath("meshes.json").write_text(json.dumps({"triangles": np.searchsorted(ids, faces).tolist(),
         "vertices": geometry}, separators=(",", ":"), allow_nan=False))
    print(f"X_VLM_COMPLETE p3={len(p3)} p4={len(p4)} selected={selected}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.runtime, args.output)
