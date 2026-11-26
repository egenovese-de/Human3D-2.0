"""Verify persisted shared geometry while switching targets in a disposable Q project copy."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory

import numpy as np

from audit_bind_frames import revision
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.session import Session


def run(source, destination):
    copytree(source, destination)
    session = Session(destination)
    body = load_project_body(session.store)
    original = session.store.load()
    targets = tuple(photo.id for photo in original.photos.photos if photo.included)
    if len(targets) < 2:
        raise ValueError("target_switch_requires_multiple_photos")
    rows = []
    for target in (*targets, original.photos.target):
        session.select_target(target)
        project = session.store.load()
        evidence = session.shared_evidence()
        fit = session.current_shared_fit()
        if fit is None or target not in fit.alignments:
            raise ValueError("missing_current_target_alignment")
        points = np.asarray(deform_vertices(body, fit.fit.controls), dtype="<f8")
        rows.append(dict(target=target, frozen_body=project.frozen_body_digest,
                         shared_fit=project.shared_fit_digest,
                         evidence_digest=evidence.dependency_digest,
                         neutral_vertices_sha256=sha256(points.tobytes()).hexdigest(),
                         yaw_deg=fit.alignments[target].camera.yaw_degrees))
    for field in ("frozen_body", "shared_fit", "evidence_digest", "neutral_vertices_sha256"):
        if len({row[field] for row in rows}) != 1:
            raise ValueError(f"target_switch_changed_{field}")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidate", "native_projects", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    cases = []
    with TemporaryDirectory() as folder:
        for source in sorted(args.native_projects.glob("*_bend0-4/project")):
            name = source.parent.name
            cases.append(dict(fixture=name, targets=run(source, Path(folder) / name)))
    if not cases:
        raise ValueError("no_four_view_projects")
    args.output.write_text(json.dumps(dict(candidate_sha=revision(args.candidate),
                                          lab_sha=revision(Path(__file__).parents[2]), cases=cases),
                                     indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
