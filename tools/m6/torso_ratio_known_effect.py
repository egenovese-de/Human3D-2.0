"""Measure the opt-in torso ratio consumer against a controlled anatomical perturbation."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from audit_bind_frames import revision
from human3d.anatomical_evidence import AnatomicalEvidence, QuantitativeObservation
from human3d.fitting import _optimize
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.session import Session
from human3d.torso_evidence import _torso_section, torso_ratio_penalty


def run(candidate, project, output):
    session = Session(project)
    body = load_project_body(session.store)
    neutral = np.asarray(deform_vertices(body, {}))
    mesh = body["mesh"]
    faces = [[v for v, _ in face["corners"]] for face in mesh["faces"] if face["group"] == "body"]
    triangles = np.asarray([(face[0], face[i], face[i + 1]) for face in faces for i in range(1, len(face) - 1)])
    y = np.asarray(mesh["vertices"])[np.unique(triangles), 1]
    waist, chest = y.min() + np.ptp(y) * np.asarray([.61, .71])

    def ratio(points):
        return _torso_section(points, triangles, chest) / _torso_section(points, triangles, waist)

    known = np.asarray(deform_vertices(body, {"bust": .5}))
    target_ratio = ratio(known)
    measured = QuantitativeObservation(
        "b" * 64, 0, "torso", "circumference", "torso.chest_to_waist_circumference@v1",
        "subject_local", "ratio", "canonical-known-effect", value=target_ratio, uncertainty=.002, visibility=1.,
    )
    supplied = AnatomicalEvidence("b" * 64, "fixture", "known-effect", 0, schema_version=2, observations=(measured,))
    view = SimpleNamespace(ref=SimpleNamespace(photo_id="fixture"), candidate=0, observed_regions=("torso",),
                           detection=SimpleNamespace(anatomical=supplied))
    penalty = torso_ratio_penalty(body, SimpleNamespace(views=(view,), unresolved=()), {"fixture"})
    controls, _ = _optimize(body, lambda _: {"fixture": 1.}, {}, ("bust", "waist"), (.25, .125),
                             measurement_penalty=penalty)
    fitted = deform_vertices(body, controls)
    record = dict(candidate_sha=revision(candidate), lab_sha=revision(Path(__file__).parents[2]),
                  frozen_sha256=session.store.load().frozen_body_digest,
                  scope="Canonical known-effect control; no independent source-family validation",
                  base_ratio=ratio(neutral), injected_ratio=target_ratio,
                  baseline_penalty=penalty(neutral), fitted_penalty=penalty(fitted),
                  fitted_ratio=ratio(fitted), fitted_controls=controls,
                  intended_positive_bust_penalty=penalty(known),
                  opposite_bust_penalty=penalty(deform_vertices(body, {"bust": -.5})))
    if not record["intended_positive_bust_penalty"] < record["baseline_penalty"] < record["opposite_bust_penalty"]:
        raise ValueError("torso consumer did not respond in the expected direction")
    if abs(record["fitted_ratio"] - target_ratio) >= abs(record["base_ratio"] - target_ratio):
        raise ValueError("bounded optimizer did not approach the observed torso ratio")
    output.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidate", "project", "output"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
