"""Measure the release appearance consumer of supported Boolean visibility."""
import argparse
from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from human3d.anatomical_evidence import AnatomicalEvidence, RegionVisibility
from human3d.appearance import prepare_view
from human3d.frozen_body import load_project_body
from human3d.originals import OriginalStore
from human3d.session import Session
from human3d.texture_bake import bake_atlas


def run(previous, output):
    rows = []
    for identity in ("f_af01", "m_la01"):
        path = next((previous / "holdout-native").glob(f"*_{identity}_bend0-1")) / "project"
        session = Session(path)
        body = load_project_body(session.store)
        view = session.shared_evidence().views[0]
        target = view.ref.photo_id
        alignment = session.current_shared_fit().alignments[target]
        source = OriginalStore(session.store.directory)
        for confidence in (None, .799, .8, 1):
            selected = view
            if confidence is not None:
                evidence = AnatomicalEvidence(view.ref.photo_digest, "lab", "visibility-boundary", view.candidate,
                                              regions=(RegionVisibility("left_arm", False, confidence),))
                selected = replace(view, detection=replace(view.detection, anatomical=evidence))
            appearance = prepare_view(source, selected, alignment)
            atlas = bake_atlas(body, {}, {target: (appearance, view.detection.image_size)}, target, size=256)
            rows.append({"identity": identity, "confidence": confidence,
                         "hidden_regions": sorted(appearance.hidden_regions),
                         "observed_uv_fraction": atlas.observed_fraction,
                         "mean_rgb": np.asarray(atlas.color).mean(axis=(0, 1)).tolist()})
    output.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for argument in ("previous", "output"):
        parser.add_argument(argument, type=Path)
    run(**vars(parser.parse_args()))
