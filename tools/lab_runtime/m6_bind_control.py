"""Procedural adapter; not a replay of historical human fixtures."""
import json
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m6"))
from audit_bind_frames import bind_transform, chain_summary, angular_distance, SOURCE_TO_CANONICAL

def main(output):
    root = bind_transform(np.eye(3), [0., 1., 0.])
    rows = []
    for sign in (-1, 1):
        rotation = np.array([[0., -sign, 0.], [sign, 0., 0.], [0., 0., 1.]])
        child = root @ bind_transform(rotation, [0., 2., 0.])
        residual = chain_summary({"root": root, "child": child}, {"root": None, "child": "root"})
        angle = angular_distance(SOURCE_TO_CANONICAL @ rotation @ SOURCE_TO_CANONICAL.T, np.eye(3))
        assert residual < 1e-12 and abs(angle - 90.) < 1e-10
        rows.append({"sign": sign, "chain_residual": residual, "angle_deg": angle})
    output.write_bytes((json.dumps({"scope":"procedural M6 bind-frame function control", "cases":rows},sort_keys=True)+"\n").encode())

if __name__ == "__main__":
    main(Path(sys.argv[1]))
