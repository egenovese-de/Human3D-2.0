"""Freeze a verified upstream neutral mesh and rig into a native JSON artifact."""
import hashlib
import json
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

ASSETS = {
    "base.obj": "8e761e6624b8f54536409135d1636da63b32486a90d4897f84e121d144f6fb4c",
    "default.mhskel": "99f179bce0aa850b45d4191a1d0d234c5851f881c057439470ded3bddf729a24",
    "default_weights.mhw": "0f3641d651ae3d00ad6b4ccee43142edb109d3bd909d27d9e4139ef1beed8625",
}


def _verified_assets(directory: Path) -> dict[str, bytes]:
    assets = {}
    for name, digest in ASSETS.items():
        data = (directory / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"Bootstrap asset integrity mismatch: {name}")
        assets[name] = data
    return assets


def _mesh(text: str) -> dict:
    vertices = []
    texcoords = []
    faces = []
    group = ""
    for line in text.splitlines():
        if not (tokens := line.split()):
            continue
        kind, *fields = tokens
        if kind == "v":
            vertices.append(tuple(map(float, fields)))
        elif kind == "vt":
            texcoords.append(tuple(map(float, fields)))
        elif kind == "g":
            group = " ".join(fields)
        elif kind == "f":
            corners = [tuple(int(value) - 1 for value in field.split("/")) for field in fields]
            faces.append({"group": group, "corners": corners})
    return {"vertices": vertices, "texcoords": texcoords, "faces": faces}


def _rig(skeleton: dict, weights: dict, vertices: list) -> dict:
    joint_vertices = skeleton["joints"]
    joints = {}
    for name, indices in joint_vertices.items():
        if not indices or any(not 0 <= index < len(vertices) for index in indices):
            raise ValueError(f"Invalid rig joint: {name}")
        joints[name] = [math.fsum(vertices[index][axis] for index in indices) / len(indices)
                        for axis in range(3)]
    bones = skeleton["bones"]
    by_vertex = [{} for _ in vertices]
    for bone, influences in weights["weights"].items():
        if bone not in bones:
            raise ValueError(f"Unknown weighted bone: {bone}")
        for index, weight in influences:
            if not 0 <= index < len(vertices) or not math.isfinite(weight) or weight < 0:
                raise ValueError("Invalid bootstrap skin weight")
            by_vertex[index][bone] = weight
    skin = []
    for influences in by_vertex:
        total = math.fsum(influences.values())
        skin.append({name: weight / total for name, weight in influences.items() if weight > 0})
    return {"joints": joints, "joint_vertices": joint_vertices, "bones": bones,
            "planes": skeleton["planes"], "skin": skin}


def freeze_neutral(directory: Path, artifact_directory: Path) -> str:
    assets = _verified_assets(directory)
    mesh = _mesh(assets["base.obj"].decode("utf-8"))
    rig = _rig(json.loads(assets["default.mhskel"]),
               json.loads(assets["default_weights.mhw"]), mesh["vertices"])
    payload = {"schema_version": 1, "kind": "frozen_body", "source_asset_digests": ASSETS,
               "algorithm_version": "makehuman-neutral-v1", "mesh": mesh, "rig": rig}
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    artifact_directory.mkdir(parents=True, exist_ok=True)
    destination = artifact_directory / f"{digest}.json"
    temporary = None
    try:
        with NamedTemporaryFile(dir=destination.parent, delete=False) as file:
            temporary = Path(file.name)
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            if destination.read_bytes() != data:
                raise ValueError("Existing frozen artifact digest mismatch")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return digest
