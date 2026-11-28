"""Exercise the application G3 adapter using known synthetic G1 landmarks and pose."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import numpy as np

from human3d.bootstrap import freeze_neutral
from human3d.experimental import g3_observation, NativeBasis, raster
from human3d.experimental_camera import Camera
from human3d.experimental_registration import FIT_SIZE, INDEX, POSE_KEYS, Rig
from human3d.frozen_body import load_frozen_body
from human3d.native_rig import rebind_joints
from human3d.vision import Landmark


def qualify(assets):
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        digest = freeze_neutral(assets / "makehuman", root, with_morphs=True)
        body = load_frozen_body(root / f"{digest}.json")
    basis = NativeBasis(assets, body)
    vertices = basis.evaluate({})
    rig = Rig(body["rig"], vertices * 10)
    faces = np.asarray([[index for index, _ in f["corners"]] for f in body["mesh"]["faces"]
                        if f["group"] == "body"], dtype=np.int32)
    pose = np.zeros(len(POSE_KEYS))
    pose[:4] = (.17, -.06, .14, .10)
    camera = Camera(yaw=15, span=219, center_y=2, elevation=6, distance=430, perspective=True)
    projected = camera.project(rig.anchors(pose), FIT_SIZE) / FIT_SIZE
    points = [Landmark(.5, .5, None, None)] * 33
    for index, (x, y) in zip(INDEX, projected):
        points[index] = Landmark(float(x), float(y), 1., 1.)
    view = SimpleNamespace(ref=SimpleNamespace(photo_id="geometry-oracle"), candidate=0,
                           detection=SimpleNamespace(visible_pose=lambda _: points))
    mask = raster(camera.project, rig.mesh(pose), faces, FIT_SIZE)

    def evaluate(definition):
        result, metadata = g3_observation(body | {"mesh": body["mesh"] | {"vertices": vertices}},
                                          view, mask, (FIT_SIZE, FIT_SIZE), (0, 0), definition, lambda: None)
        if result is None:
            raise RuntimeError(metadata)
        transforms = result.pose.transforms(rebind_joints(body["rig"], vertices))
        assert all(np.isfinite(matrix).all() and np.isfinite(offset).all() for matrix, offset in transforms.values())
        return {"source": result.source, "scale": result.scale, **metadata}

    calibrated = evaluate({"camera": asdict(camera), "canonical_pose": False, "independent_scale": True})
    sector = evaluate({"capture_yaw_sector": 0, "focal_px_on_384": FIT_SIZE * camera.distance / camera.span,
                       "canonical_pose": False, "independent_scale": False})
    assert calibrated["iou"] > .90 and sector["iou"] > .70, (calibrated, sector)
    return {"input": "synthetic exact landmarks, known articulated MakeHuman pose",
            "g1_sampled_parity_mm": basis.parity_error_mm(),
            "calibrated_articulated": calibrated, "verified_sector_focal_prior": sector}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assets", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = qualify(args.assets)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
