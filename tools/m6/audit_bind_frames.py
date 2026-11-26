"""Audit source and canonical USD bind frames without assuming homologous twist."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import numpy as np

from human3d.frozen_body import deform_vertices, load_project_body
from human3d.native_rig import pose_transforms, rebind_joints
from human3d.session import Session

SOURCE_TO_CANONICAL = np.array([[1., 0., 0.], [0., 0., 1.], [0., -1., 0.]])
CORRESPONDENCE = {
    f"{source}_{side}": f"{native}.{side}"
    for source, native in (("upperarm", "upperarm01"), ("lowerarm", "lowerarm01"),
                           ("hand", "wrist"), ("thigh", "upperleg01"), ("calf", "lowerleg01"), ("foot", "foot"))
    for side in ("L", "R")
}


def revision(root):
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def angular_distance(a, b):
    cosine = (np.trace(a.T @ b) - 1) / 2
    return float(np.degrees(np.arccos(np.clip(cosine, -1, 1))))


def relative(matrix, parent):
    return np.linalg.solve(parent, matrix)


def chain_summary(globals_, parents):
    ordered = {}
    def reconstruct(key):
        if key is None:
            return np.eye(4)
        if key not in ordered:
            parent = parents[key]
            expected = globals_[parent] if parent else np.eye(4)
            ordered[key] = reconstruct(parent) @ relative(globals_[key], expected)
        return ordered[key]

    return max(float(np.max(np.abs(reconstruct(name) - globals_[name]))) for name in parents)

def bind_transform(rotation, translation):
    result = np.eye(4)
    result[:3, :3] = rotation
    result[:3, 3] = translation
    return result


def native_audit(directory):
    session = Session(directory)
    body = load_project_body(session.store)
    vertices = deform_vertices(body, {})
    rig = body["rig"]
    joints = rebind_joints(rig, vertices)
    bones = rig["bones"]
    alignment = session.current_shared_fit().alignments[session.shared_evidence().views[0].ref.photo_id]
    transforms = pose_transforms(rig, joints, alignment)
    rest, posed = {}, {}
    for name, bone in bones.items():
        head = joints[bone["head"]]
        rotation, shift = transforms[name]
        rest[name] = bind_transform(np.eye(3), head)
        posed[name] = bind_transform(rotation, rotation @ head + shift)
    parents = {name: bone["parent"] for name, bone in bones.items()}
    return {"name": directory.parent.name, "bones": len(bones),
            "rest_chain_residual_dm": chain_summary(rest, parents),
            "pose_chain_residual_matrix": chain_summary(posed, parents),
            "bind_skin_transform_residual_matrix": max(
                float(np.max(np.abs(posed[key] @ np.linalg.inv(rest[key]) - bind_transform(*transforms[key]))))
                for key in bones)}


def source_audit(path):
    payload = path.read_bytes()
    data = json.loads(payload)
    bones = data["bones"]
    rest = {name: np.asarray(row["rest_global"]) for name, row in bones.items()}
    pose = {name: np.asarray(row["posed_global"]) for name, row in bones.items()}
    parents = {name: row["parent"] for name, row in bones.items()}
    residuals, rotations = {}, {}
    for name, native in CORRESPONDENCE.items():
        parent = parents[name]
        local_rest = relative(rest[name], rest[parent])
        local_pose = relative(pose[name], pose[parent])
        basis = np.asarray(bones[name]["pose_basis"])
        residuals[name] = float(np.max(np.abs(local_rest @ basis - local_pose)))
        rotation = pose[name][:3, :3] @ np.linalg.inv(rest[name][:3, :3])
        converted = SOURCE_TO_CANONICAL @ rotation @ SOURCE_TO_CANONICAL.T
        rotations[native] = {
            "source_change_degrees": angular_distance(converted, np.eye(3)),
            "mapped_rotation_orthogonality_error": float(np.max(np.abs(converted.T @ converted - np.eye(3)))),
            "cross_rig_rotation_error": None,
            "correspondence": "direction_only",
        }
    return {"fixture": path.parent.name, "input_sha256": sha256(payload).hexdigest(),
            "source_basis_closure": max(residuals.values()), "source_segment_audit": rotations}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidate", "rig_fixtures", "holdout_native", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    native = [native_audit(next(args.holdout_native.glob(f"*_{identity}_bend32-1")) / "project")
              for identity in ("f_af01", "m_la01")]
    fixtures = [path for identity in ("f_af01", "m_la01")
                for path in sorted(args.rig_fixtures.glob(f"{identity}_*/manifest.json"))
                if not json.loads(path.read_text())["morphology_asymmetry"]]
    if not fixtures:
        raise ValueError("no_source_rig_fixtures")
    # Algebraic control for both signed rotations around all three axes.
    for index, axis in enumerate(np.eye(3)):
        cross = np.cross(axis, np.eye(3)).T
        for angle in (np.pi / 2, -np.pi / 2):
            rotation = np.eye(3) + np.sin(angle) * cross + (1 - np.cos(angle)) * (cross @ cross)
            converted = SOURCE_TO_CANONICAL @ rotation @ SOURCE_TO_CANONICAL.T
            probe = np.eye(3)[(index + 1) % 3]
            expected = np.sign(angle) * np.cross(axis, probe)
            np.testing.assert_allclose(converted @ (SOURCE_TO_CANONICAL @ probe),
                                       SOURCE_TO_CANONICAL @ expected, atol=1e-12)
    report = {"candidate_sha": revision(args.candidate), "lab_sha": revision(Path(__file__).parents[2]),
              "signed_axis_algebra_controls": 6, "native": native,
              "source": [source_audit(path) for path in fixtures]}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
