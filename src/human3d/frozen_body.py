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
    if not isinstance(body, dict) or body.get("schema_version") != 1 or body.get("kind") != "frozen_body":
        raise ValueError("unsupported_frozen_body")
    validate_frozen_body(body)
    return body


def validate_frozen_body(body):
    """Validate structural references before consuming a content-addressed body."""
    def vector(value, length):
        return len(value) == length and all(type(x) in (int, float) and math.isfinite(x) for x in value)

    def index(value, count):
        return type(value) is int and 0 <= value < count

    try:
        mesh, rig = body["mesh"], body["rig"]
        vertices, uv, faces = mesh["vertices"], mesh["texcoords"], mesh["faces"]
        if not vertices or not uv or not faces or not all(vector(v, 3) for v in vertices) or not all(vector(v, 2) for v in uv):
            raise ValueError("mesh")
        for face in faces:
            corners = face["corners"]
            if len(corners) < 3 or any(len(c) != 2 or not index(c[0], len(vertices)) or not index(c[1], len(uv)) for c in corners):
                raise ValueError("face")
        joints, bones, skin = rig["joints"], rig["bones"], rig["skin"]
        if not joints or not bones or len(skin) != len(vertices) or not all(vector(v, 3) for v in joints.values()):
            raise ValueError("rig")
        for name, bone in bones.items():
            if bone["head"] not in joints or bone["tail"] not in joints:
                raise ValueError("bone joint")
            seen = {name}
            parent = bone.get("parent")
            while parent:
                if parent in seen or parent not in bones:
                    raise ValueError("bone hierarchy")
                seen.add(parent)
                parent = bones[parent].get("parent")
        for influences in skin:
            if any(name not in bones or type(w) not in (int, float) or not math.isfinite(w) or w < 0 for name,w in influences.items()):
                raise ValueError("skin")
            if influences and not math.isclose(math.fsum(influences.values()), 1., abs_tol=1e-6):
                raise ValueError("skin normalization")
        for name, indices in rig["joint_vertices"].items():
            if name not in joints or not indices or any(not index(i, len(vertices)) for i in indices):
                raise ValueError("joint vertices")
        if set(rig["joint_vertices"]) != set(joints):
            raise ValueError("joint binding")
        for offsets in body.get("morph_targets", {}).values():
            seen = set()
            for entry in offsets:
                if len(entry) != 4 or not index(entry[0], len(vertices)) or entry[0] in seen or not vector(entry[1:], 3):
                    raise ValueError("morph")
                seen.add(entry[0])
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as error:
        raise ValueError("invalid_frozen_body_structure") from error

def morph_controls(body: dict) -> dict[str, str]:
    targets = body.get("morph_targets", {})
    stems = {name.removesuffix("-incr") for name in targets if name.endswith("-incr")}
    return {stem.rsplit("-", 1)[0]: stem for stem in sorted(stems) if f"{stem}-decr" in targets}


def deform_vertices(body: dict, controls: dict[str, float]) -> tuple[tuple[float, ...], ...]:
    """Evaluate bounded signed circumference controls on the neutral vertices."""
    vertices = [list(vertex) for vertex in body["mesh"]["vertices"]]
    morphs = body.get("morph_targets", {})
    supported = morph_controls(body)
    from .regional_morphs import apply_regional_controls, regional_controls

    length_edits = {}
    regional_edits = {}
    regional = regional_controls(body)
    head_width = controls.get("head_width")
    for name, value in sorted(controls.items()):
        if not math.isfinite(value) or not -1 <= value <= 1:
            raise ValueError(f"out_of_range_morph: {name}")
        if name in {"head_width", "jaw_width"}:
            continue
        if name in regional:
            regional_edits[name] = value
            continue
        if name.endswith("_length"):
            length_edits[name] = value
            continue
        direction = "incr" if value >= 0 else "decr"
        try:
            offsets = morphs[f"{supported[name]}-{direction}"]
        except KeyError as error:
            raise ValueError(f"unsupported_morph: {name}") from error
        for index, x, y, z in offsets:
            vertex = vertices[index]
            for axis, offset in enumerate((x, y, z)):
                vertex[axis] += abs(value) * offset
    if length_edits:
        from .proportions import length_controls, lengthen

        for name, value in length_edits.items():
            if name not in length_controls(body):
                raise ValueError(f"unsupported_morph: {name}")
            if value:
                vertices = lengthen(body, vertices, name, value)
    if regional_edits:
        vertices = apply_regional_controls(body, vertices, regional_edits)
    if head_width is not None:
        from .face import has_head_control, widen_head

        if not has_head_control(body):
            raise ValueError("head_control_unavailable")
        if head_width:
            vertices = widen_head(body, vertices, head_width)
    if "jaw_width" in controls:
        from .face import widen_jaw

        vertices = widen_jaw(body, vertices, controls["jaw_width"])
    return tuple(map(tuple, vertices))


def load_project_body(store) -> dict:
    digest = store.load().frozen_body_digest
    if digest is None:
        raise ValueError("project_has_no_frozen_body")
    return load_frozen_body(store.directory / "frozen" / f"{digest}.json")
