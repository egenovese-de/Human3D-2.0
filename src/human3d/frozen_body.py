"""Native inspection and vertex deformation of a frozen body."""
import hashlib
import json
import math
from pathlib import Path
import re


def load_frozen_body(path: Path) -> dict:
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if not re.fullmatch(r"[a-f0-9]{64}", path.stem) or digest != path.stem:
        raise ValueError("frozen_body_digest_mismatch")
    body = json.loads(data)
    if body["schema_version"] != 1 or body["kind"] != "frozen_body":
        raise ValueError("unsupported_frozen_body")
    return body


def deform_vertices(body: dict, controls: dict[str, float]) -> tuple[tuple[float, ...], ...]:
    """Evaluate bounded signed circumference controls on the neutral vertices."""
    vertices = [list(vertex) for vertex in body["mesh"]["vertices"]]
    morphs = body.get("morph_targets", {})
    for name, value in sorted(controls.items()):
        if not math.isfinite(value) or not -1 <= value <= 1:
            raise ValueError(f"out_of_range_morph: {name}")
        direction = "incr" if value >= 0 else "decr"
        try:
            offsets = morphs[f"{name}-circ-{direction}"]
        except KeyError as error:
            raise ValueError(f"unsupported_morph: {name}") from error
        for index, x, y, z in offsets:
            vertex = vertices[index]
            for axis, offset in enumerate((x, y, z)):
                vertex[axis] += abs(value) * offset
    return tuple(map(tuple, vertices))
