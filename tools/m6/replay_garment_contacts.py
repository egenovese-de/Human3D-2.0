"""Replay the Q posed-garment inputs with the M6 candidate contact classifier."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from time import perf_counter

import numpy as np

from human3d.frozen_body import deform_vertices, load_project_body
from human3d.garments import CATEGORIES, measure_clearance, posed_garment, prototype
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.session import Session
from human3d.triangle_collision import triangle_contacts


def triangles(polygons):
    return np.asarray([(face[0], face[i], face[i + 1])
                       for face in polygons for i in range(1, len(face) - 1)])


def revision(root):
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def replay(root, historical):
    expected = {(row["identity"], row["target_bend_deg"], row["category"]): row
                for row in historical}
    for identity in ("f_af01", "m_la01"):
        projects = {angle: next(root.glob(f"*_{identity}_bend{angle}-1")) / "project"
                    for angle in (0, 32)}
        body = load_project_body(Session(projects[0]).store)
        neutral = deform_vertices(body, {})
        rig = body["rig"]
        joints = rebind_joints(rig, neutral)
        faces = triangles([tuple(i for i, _ in face["corners"]) for face in body["mesh"]["faces"]
                           if face["group"] == "body"])
        for angle, project in projects.items():
            session = Session(project)
            target = session.shared_evidence().views[0].ref.photo_id
            alignment = session.current_shared_fit().alignments[target]
            transforms = pose_transforms(rig, joints, alignment)
            posed = skin_vertices(neutral, rig["skin"], transforms)
            body_triangles = np.asarray(posed)[faces]
            manifest = project.parent / "benchmark.json"
            for category in CATEGORIES:
                garment = prototype(body, neutral, category)
                points = posed_garment(garment, transforms)
                indices = triangles([tuple(i for i, _ in face) for face in garment.faces])
                sampled = measure_clearance(garment, body, posed, points)
                started = perf_counter()
                contacts = triangle_contacts(body_triangles, np.asarray(points)[indices])
                reference = expected[identity, angle, category]
                yield {
                    "identity": identity, "target_bend_deg": angle, "category": category,
                    "native_benchmark_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                    "historical_triangle_pairs": reference["triangle_pairs"],
                    "historical_sampled_violations": reference["sampled_violations"],
                    "sampled_violations": sampled.violations,
                    "crossing": contacts.crossing, "coplanar_overlap": contacts.coplanar_overlap,
                    "touching": contacts.touching, "classifier_seconds": perf_counter() - started,
                }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidate", "holdout_native", "historical", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    historical = args.historical.read_bytes()
    report = {
        "candidate_sha": revision(args.candidate),
        "lab_sha": revision(Path(__file__).parents[2]),
        "historical_sha256": hashlib.sha256(historical).hexdigest(),
        "cases": list(replay(args.holdout_native, json.loads(historical))),
    }
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
