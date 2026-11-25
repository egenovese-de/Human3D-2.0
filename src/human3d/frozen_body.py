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


def morph_controls(body: dict) -> dict[str, str]:
    targets = body.get("morph_targets", {})
    stems = {name.removesuffix("-incr") for name in targets if name.endswith("-incr")}
    return {stem.rsplit("-", 1)[0]: stem for stem in sorted(stems) if f"{stem}-decr" in targets}


def deform_vertices(body: dict, controls: dict[str, float]) -> tuple[tuple[float, ...], ...]:
    """Evaluate bounded signed circumference controls on the neutral vertices."""
    vertices = [list(vertex) for vertex in body["mesh"]["vertices"]]
    morphs = body.get("morph_targets", {})
    supported = morph_controls(body)
    for name, value in sorted(controls.items()):
        if not math.isfinite(value) or not -1 <= value <= 1:
            raise ValueError(f"out_of_range_morph: {name}")
        direction = "incr" if value >= 0 else "decr"
        try:
            offsets = morphs[f"{supported[name]}-{direction}"]
        except KeyError as error:
            raise ValueError(f"unsupported_morph: {name}") from error
        for index, x, y, z in offsets:
            vertex = vertices[index]
            for axis, offset in enumerate((x, y, z)):
                vertex[axis] += abs(value) * offset
    return tuple(map(tuple, vertices))


def load_project_body(store) -> dict:
    digest = store.load().frozen_body_digest
    if digest is None:
        raise ValueError("project_has_no_frozen_body")
    return load_frozen_body(store.directory / "frozen" / f"{digest}.json")
