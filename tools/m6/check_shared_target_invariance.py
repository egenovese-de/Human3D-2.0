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


def run(source, destination, *, reference_changes=False):
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
    result = {"targets": rows}
    if reference_changes:
        reference = next(target for target in targets if target != original.photos.target)
        stored_evidence = session.read_observation(reference)
        original_digest = session.shared_evidence().dependency_digest
        session.include_reference(reference, False)
        excluded_digest = session.shared_evidence().dependency_digest
        if original_digest == excluded_digest or session.current_shared_fit() is not None:
            raise ValueError("reference_exclusion_did_not_invalidate_fit")
        if session.read_observation(reference) != stored_evidence:
            raise ValueError("reference_exclusion_changed_stored_observations")
        session.include_reference(reference, True)
        reopened = Session(destination)
        restored_digest = reopened.shared_evidence().dependency_digest
        if restored_digest != original_digest or reopened.read_observation(reference) != stored_evidence:
            raise ValueError("reference_reinclusion_did_not_restore_evidence")
        result["reference_change"] = dict(
            reference=reference, original_digest=original_digest, excluded_digest=excluded_digest,
            restored_digest=restored_digest, stale_fit_rejected=True, observations_preserved=True,
            fit_reusable_after_restoring_exact_dependencies=reopened.current_shared_fit() is not None,
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidate", "native_projects", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--reference-changes", action="store_true")
    args = parser.parse_args()
    cases = []
    with TemporaryDirectory() as folder:
        for source in sorted(args.native_projects.glob("*_bend0-4/project")):
            name = source.parent.name
            cases.append(dict(fixture=name, **run(source, Path(folder) / name, reference_changes=args.reference_changes)))
    if not cases:
        raise ValueError("no_four_view_projects")
    args.output.write_text(json.dumps(dict(candidate_sha=revision(args.candidate),
                                          lab_sha=revision(Path(__file__).parents[2]), cases=cases),
                                     indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
