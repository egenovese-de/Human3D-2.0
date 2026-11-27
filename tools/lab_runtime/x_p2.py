"""Canonical pose benchmark for native, dominant-bone and blended morph fields."""

import argparse
import json
from math import atan2, cos, radians, sin
from pathlib import Path
from time import perf_counter

import numpy as np

from bootstrap import ROOT, digest, safe
from human3d.alignment import Alignment, Camera
from human3d.bootstrap import _mesh, _rig
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices, validate_pose, validate_rebind

SOURCE = "e0ae4eae57347466b5757bbcdaaa7194bdd31c94"
POSES = {"native": None, "a": (35, 12), "t": (90, 12), "x": (50, 23)}
CASES = {
    "upper": {"torso-scale-depth": .25, "torso-vshape": .30, "breast-dist": .25,
              "l-upperarm-scale-horiz": .30, "r-upperarm-scale-horiz": .30},
    "lower": {"hip-scale-horiz": .30, "pelvis-tone": .35, "buttocks-volume": .25,
              "l-upperleg-scale-horiz": .25, "r-upperleg-scale-horiz": .25},
    "combined": {"torso-scale-depth": .35, "torso-vshape": .30, "breast-dist": .25,
                 "hip-scale-horiz": .35, "pelvis-tone": .35, "buttocks-volume": .30,
                 "l-upperarm-scale-horiz": .25, "r-upperarm-scale-horiz": .25,
                 "l-upperleg-scale-horiz": .25, "r-upperleg-scale-horiz": .25},
}


def load_assets(runtime, group, manifest):
    data = json.loads((ROOT / manifest).read_text())
    result = {}
    for entry in data["files"]:
        path = safe(runtime / "assets" / group, data.get("source_prefix", "") + entry["path"])
        if path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
            raise ValueError(f"Unverified {group} asset {path.name}")
        if path.stem in result and (path.suffix == ".target" and path.stem.endswith("-incr")):
            raise ValueError(f"Ambiguous target {path.stem}")
        result[path.stem] = path
    return data["revision"], result


def field(path, size):
    output = np.zeros((size, 3))
    indices = set()
    for line in path.read_text().splitlines():
        tokens = line.partition("#")[0].split()
        if tokens:
            i = int(tokens[0])
            if i in indices or not 0 <= i < size or len(tokens) != 4:
                raise ValueError(f"Invalid target record: {path}")
            output[i] = list(map(float, tokens[1:]))
            indices.add(i)
    if not indices or not np.isfinite(output).all():
        raise ValueError(f"Invalid target field: {path}")
    return output


def alignment(pose):
    camera = Camera(0, 18, 0j, 1)
    angles, depths = {}, {}
    if pose is not None:
        arms, legs = pose
        for label, angle, depth in (("upperarm01", arms, 0), ("lowerarm01", arms, .12),
                                   ("upperleg01", legs, 0), ("lowerleg01", legs, 0)):
            for side, sign in (("L", 1), ("R", -1)):
                key = f"{label}.{side}"
                angles[key] = atan2(cos(radians(angle)), sign * sin(radians(angle)))
                depths[key] = depth
    return Alignment(camera, 0, angles, depths)


def region_masks(points):
    x, y, z = points.T
    ax = abs(x)
    return {
        "axilla": (y > 4) & (y < 5.1) & (ax > 1.25) & (ax < 2.15),
        "shoulder": (y >= 4.8) & (y < 5.8) & (ax > 1.25) & (ax < 2.4),
        "upper_arm": (y > 3.55) & (y < 5.2) & (ax >= 1.95) & (ax < 3.25),
        "lateral_chest": (y > 3.5) & (y < 5.15) & (ax > .85) & (ax < 1.55),
        "breast": (y > 3.2) & (y < 4.8) & (ax > .25) & (ax < 1.3) & (z > .65),
        "pelvis": (y > .05) & (y < 1.7) & (ax < 2),
        "inguinal": (y > -.75) & (y < .7) & (ax < 1.22) & (z > .25),
        "inner_thigh": (y > -3.65) & (y < -.15) & (ax < 1.15),
        "gluteal": (y > -.65) & (y < 1.55) & (ax < 1.8) & (z < -.2),
    }


def distances(points, reference, masks):
    errors = np.linalg.norm(points - reference, axis=1) * 100
    output = {}
    for key, mask in masks.items():
        values = errors[mask]
        if not len(values):
            raise ValueError(f"Empty region {key}")
        output[key] = {"vertices": len(values), "mean_mm": float(values.mean()),
                       "p95_mm": float(np.percentile(values, 95)), "max_mm": float(values.max())}
    return output


def areas(vertices, faces):
    a, b, c = vertices[faces].transpose(1, 0, 2)
    return np.linalg.norm(np.cross(b - a, c - a), axis=1)


def run(runtime, out):
    revision, foundation = load_assets(runtime, "foundation", "DOCS/manifests/makehuman-v1.3.0.json")
    torso_revision, torso = load_assets(runtime, "anatomical_torso", "lab/manifests/makehuman-anatomical-torso.json")
    region_revision, region = load_assets(runtime, "p1_anatomy", "lab/manifests/makehuman-p1-anatomy.json")
    if len({revision, torso_revision, region_revision}) != 1:
        raise ValueError("Mismatched MakeHuman asset revisions")
    mesh = _mesh(foundation["base"].read_text())
    base = np.asarray(mesh["vertices"])
    rig = _rig(json.loads(foundation["default"].read_text()),
               json.loads(foundation["default_weights"].read_text()), mesh["vertices"])
    body = {"mesh": mesh, "rig": rig}
    joints = validate_rebind(body, base)
    body_faces = [f["corners"] for f in mesh["faces"] if f["group"] == "body"]
    faces = np.asarray([[f[0][0], f[i][0], f[i + 1][0]] for f in body_faces for i in range(1, len(f) - 1)])
    ids = np.unique(faces)
    triangles = np.searchsorted(ids, faces)
    masks = {"global": np.ones(len(ids), dtype=bool), **region_masks(base[ids])}
    weights = rig["skin"]
    weight_error = max(abs(sum(weights[i].values()) - 1) for i in ids)
    uv_indices = [u for f in body_faces for _, u in f]
    if min(uv_indices) < 0 or max(uv_indices) >= len(mesh["texcoords"]):
        raise ValueError("Invalid body UV corners")
    dominant = [max(w, key=w.get) if w else None for w in weights]
    target_paths = torso | region
    native = {}
    for case, coefficients in CASES.items():
        shift = sum(coefficient * field(target_paths[f"{key}-incr"], len(base))
                    for key, coefficient in coefficients.items())
        anatomy = base + shift
        native[case] = (anatomy, shift, validate_rebind(body, anatomy))
    out.mkdir(parents=True, exist_ok=False)
    geometry, rows = {}, []
    pose_measurements = {}
    for name, angles in POSES.items():
        target = alignment(angles)
        transforms = pose_transforms(rig, joints, target)
        posed = skin_vertices(base, weights, transforms)
        validate_pose(body, base, posed)
        geometry[f"{name}-neutral"] = posed[ids].tolist()
        pose_measurements[name] = {}
        for limb in ("upperarm01.L", "upperleg01.L"):
            bone = rig["bones"][limb]
            vector = transforms[limb][0] @ (joints[bone["tail"]] - joints[bone["head"]])
            pose_measurements[name][limb] = float(np.degrees(atan2(abs(vector[0]), -vector[1])))
        rotations = np.stack([transforms[b][0] if b else np.eye(3) for b in dominant])
        linear = {key: (rotation, np.zeros(3)) for key, (rotation, _) in transforms.items()}
        prior = areas(posed, faces)
        stable = prior > 1e-6
        for case, (anatomy, shift, rebound) in native.items():
            start = perf_counter()
            reference = skin_vertices(anatomy, weights, pose_transforms(rig, rebound, target))
            a_seconds = perf_counter() - start
            start = perf_counter()
            direct = posed + np.einsum("ijk,ik->ij", rotations, shift)
            b_seconds = perf_counter() - start
            start = perf_counter()
            transported = posed + skin_vertices(shift, weights, linear)
            c_seconds = perf_counter() - start
            fixed = skin_vertices(anatomy, weights, transforms)
            fixed_max_mm = float(np.linalg.norm((fixed - transported)[ids], axis=1).max() * 100)
            if fixed_max_mm > 1e-8:
                raise ValueError(f"Fixed-transform LBS identity failed: {name}/{case}")
            reference_joints = rebind_joints(rig, reference)
            for method, candidate, seconds in (("a", reference, a_seconds), ("b", direct, b_seconds),
                                               ("c", transported, c_seconds)):
                status = "PASS"
                try:
                    validate_pose(body, posed, candidate)
                    fitted = validate_rebind(body, candidate)
                    joint_error = max(np.linalg.norm(fitted[k] - reference_joints[k]) for k in fitted) * 100
                except ValueError as error:
                    status = str(error)
                    joint_error = None
                ratio = areas(candidate, faces)[stable] / prior[stable]
                key = f"{name}-{case}-{method}"
                geometry[key] = candidate[ids].tolist()
                rows.append({"pose": name, "case": case, "method": method, "mesh": key,
                             "distance_to_a": distances(candidate[ids], reference[ids], masks),
                             "fixed_transform_identity_max_mm": fixed_max_mm,
                             "rebind_and_pose": status, "joint_locator_max_error_mm": joint_error,
                             "area_ratio_min": float(ratio.min()), "area_ratio_max": float(ratio.max()),
                             "area_ratio_p01": float(np.percentile(ratio, 1)),
                             "area_ratio_p99": float(np.percentile(ratio, 99)), "seconds": seconds})
    result = {"source_revision": SOURCE, "asset_revision": revision, "pose_angles_deg": pose_measurements,
              "cases": CASES, "vertices": len(ids), "triangles": len(faces), "bones": len(rig["bones"]),
              "uv_corners": len(uv_indices), "max_skin_weight_error": weight_error, "rows": rows}
    (out / "metrics.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (out / "meshes.json").write_text(json.dumps({"triangles": triangles.tolist(), "vertices": geometry,
                                                 "texcoords": mesh["texcoords"],
                                                 "uv_faces": [[[int(np.searchsorted(ids, i)), u] for i, u in f] for f in body_faces]},
                                                separators=(",", ":"), allow_nan=False))
    print(f"X_P2_GEOMETRY {len(rows)} candidates, {len(geometry)} meshes", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.runtime, args.output)
