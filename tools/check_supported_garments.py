"""Check all native base garment categories in recovered poses."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

from human3d.frozen_body import deform_vertices, load_project_body
from human3d.garments import CATEGORIES, correct_clearance, posed_garment, prototype
from human3d.native_rig import pose_transforms, skin_vertices, validate_rebind
from human3d.session import Session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run
    benchmark = json.loads((run / "benchmark.json").read_text())
    session = Session(run / "project")
    shared = session.current_shared_fit()
    body = load_project_body(session.store)
    neutral = deform_vertices(body, shared.fit.controls)
    rig = body["rig"]
    joints = validate_rebind(body, neutral)
    rows = {}
    for name in ("subject_01_front.png", "subject_01_left_profile.png"):
        alignment = shared.alignments[benchmark["photo_ids"][name]]
        transforms = pose_transforms(rig, joints, alignment)
        posed = skin_vertices(neutral, rig["skin"], transforms)
        rows[name] = {}
        for category in CATEGORIES:
            candidate = prototype(body, neutral, category, ease_mm=3)
            corrected, report = correct_clearance(candidate, body, posed, transforms)
            assert candidate.faces == corrected.faces and candidate.uv == corrected.uv
            assert posed_garment(corrected, transforms).shape == corrected.points.shape
            rows[name][category] = asdict(report) | {"minimum_mm": 100 * report.minimum}
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
