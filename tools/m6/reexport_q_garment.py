"""Replay Q texturing and garment export from a stored fit and original observations."""
import argparse
from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from human3d.appearance import prepare_view
from human3d.frozen_body import load_project_body
from human3d.garment_fit import fit_garment
from human3d.garments import GarmentAsset
from human3d.originals import OriginalStore
from human3d.session import Session
from human3d.texture_bake import bake_atlas, neutralize_covered_body_color
from human3d.usd_export import export_body


def run(project, output):
    session = Session(project)
    snapshot = session.store.load()
    body = load_project_body(session.store)
    evidence = session.shared_evidence()
    shared = session.current_shared_fit()
    target = snapshot.photos.target
    originals = OriginalStore(session.store.directory)
    views = {view.ref.photo_id: (prepare_view(originals, view, shared.alignments[view.ref.photo_id]),
                                 view.detection.image_size)
             for view in evidence.views if view.ref.photo_id in shared.scores}
    view, size = views[target]
    controls = shared.fit.controls
    top = fit_garment(body, shared.fit, view, size, "top")
    regional = replace(view, foreground=np.asarray(top.coverage) > 0)
    garment = bake_atlas(body, controls, {target: (regional, size)}, target, size=256, garment=top.garment)
    atlas = bake_atlas(body, controls, views, target)
    body_color = neutralize_covered_body_color(body, atlas.color, [top.garment])
    shell = GarmentAsset(top.garment, garment.color, garment.observed_fraction)
    output.parent.mkdir(parents=True, exist_ok=True)
    export_body(output, body, shared.fit, shared.alignments[target], texture=body_color, garments=[shell], ground=True)
    print(json.dumps({"fixture": project.parent.name, "overlap": top.overlap,
                      "observed_uv_fraction": garment.observed_fraction}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("output", type=Path)
    run(**vars(parser.parse_args()))
