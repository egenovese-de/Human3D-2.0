"""Check facial morph locality and frozen rig invariants on a local body."""
import argparse
import json
from pathlib import Path

import numpy as np

from human3d.frozen_body import deform_vertices, load_frozen_body
from human3d.native_rig import infer_support_plane, validate_rebind


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("body", type=Path)
    args = parser.parse_args()
    body = load_frozen_body(args.body)
    canonical = json.dumps(body, sort_keys=True)
    base = np.asarray(deform_vertices(body, {}))
    body_vertices = sorted({index for face in body["mesh"]["faces"] if face["group"] == "body"
                            for index, _ in face["corners"]})
    support = infer_support_plane(body["rig"], base, body_vertices)
    assert support is not None and abs(support - base[body_vertices, 1].min()) < .01
    displaced = np.asarray(deform_vertices(body, {"jaw_width": .5}))
    validate_rebind(body, displaced)
    movement = np.abs(displaced - base)
    changed = np.any(movement > 1e-10, axis=1)
    assert changed.any()
    assert all(body["rig"]["skin"][index].get("jaw", 0) > 0 for index in np.flatnonzero(changed))
    assert json.dumps(body, sort_keys=True) == canonical
    print(json.dumps({"jaw_moved_vertices": int(changed.sum()), "jaw_max_displacement_mm": float(movement.max() * 100),
                      "canonical_topology_uv_rig_unchanged": True, "neutral_support_plane": support}, indent=2))


if __name__ == "__main__":
    main()
