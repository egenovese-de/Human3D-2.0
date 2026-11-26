"""Build articulated two-layer release USDZ controls on the canonical contract."""
import argparse
import json
from pathlib import Path

from PIL import Image

from human3d.frozen_body import deform_vertices, load_project_body
from human3d.garments import GarmentAsset, correct_clearance, prototype
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.session import Session
from human3d.usd_export import export_body


def run(previous, output, report):
    rows = []
    for project in sorted((previous / "holdout-native").glob("*_bend32-1/project")):
        session = Session(project)
        fit = session.current_shared_fit()
        target = session.shared_evidence().views[0]
        alignment = fit.alignments[target.ref.photo_id]
        body = load_project_body(session.store)
        neutral = deform_vertices(body, fit.fit.controls)
        rig = body["rig"]
        transforms = pose_transforms(rig, rebind_joints(rig, neutral), alignment)
        posed = skin_vertices(neutral, rig["skin"], transforms)
        folder = output / project.parent.name
        folder.mkdir(parents=True, exist_ok=True)
        result = {"fixture": folder.name, "attempts": []}
        for inner_ease, outer_ease in ((0,10),(0,5),(3,10)):
            assets = []
            attempt = {"inner_ease_mm": inner_ease, "outer_ease_mm": outer_ease, "layers": []}
            result["attempts"].append(attempt)
            for layer, ease in enumerate((inner_ease, outer_ease)):
                shell = prototype(body, neutral, "top", ease_mm=ease, layer=layer)
                shell, measured = correct_clearance(shell, body, posed, transforms)
                attempt["layers"].append({"layer": layer, "violations": measured.violations,
                                          "sampled_clearance_mm": measured.minimum*100})
                assets.append(GarmentAsset(shell, Image.new("RGB", (128,128), ((41,87,155),(159,57,32))[layer]), 0))
            path = folder / "layered.usdz"
            try:
                export_body(path, body, fit.fit, alignment, texture=Image.new("RGB",(128,128),(143,102,78)),
                            garments=assets)
            except ValueError as error:
                attempt["error"] = str(error)
                continue
            attempt["exported"] = True
            break
        rows.append(result)
        report.write_text(json.dumps(rows, indent=2, allow_nan=False)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("previous", "output", "report"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
