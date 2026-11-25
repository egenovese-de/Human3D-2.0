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


MORPH_ASSETS = {
    "measure-hips-circ-decr.target": "8a98e80047ab89148d60067aad3b452ce715eadcaf7a1e28402140dd1ac8fb11",
    "measure-hips-circ-incr.target": "e4294db231dd3283680e6be4b9d3d8d81aa7c575a32f937f8d0751b1ec3d6512",
    "measure-thigh-circ-decr.target": "fe5303874b0ffe26a69cefd3e213b6478eec4648f60b0b110a1e176ccf24eaa9",
    "measure-thigh-circ-incr.target": "5dca89b139df6f9b7c7641485dee18e9f0da10087359b9df5ca6a1e752ea0bcc",
    "measure-calf-circ-decr.target": "2914fc47781e23987607c6546f4535ae5d8b04e2e2bec908ab588ee94e74aa15",
    "measure-calf-circ-incr.target": "c6106ec484a875a8763a7e9b12a4891da8efcd5152efbc1c7061f40bdc4353a6",
    "measure-upperarm-circ-decr.target": "42e5780765402bfedf65c59cf8f846ffe6fe06b120e11762376a4ab9ec57f383",
    "measure-upperarm-circ-incr.target": "37f960203ae6c006399d3d26ab81e6d1de81523e86f845549aa94ca345c5d980",
}


def _verified_assets(directory: Path, expected: dict[str, str]) -> dict[str, bytes]:
    assets = {}
    for name, digest in expected.items():
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


def _morph_targets(assets: dict[str, bytes], vertex_count: int) -> dict:
    targets = {}
    for name, data in assets.items():
        offsets = []
        indices = set()
        for line in data.decode("utf-8").splitlines():
            fields = line.split()
            if not fields or fields[0].startswith("#"):
                continue
            index = int(fields[0])
            delta = tuple(map(float, fields[1:]))
            if (index in indices or not 0 <= index < vertex_count
                    or len(delta) != 3 or not all(map(math.isfinite, delta))):
                raise ValueError(f"Invalid morph offset: {name}")
            indices.add(index)
            offsets.append((index, *delta))
        if not offsets:
            raise ValueError(f"Empty morph target: {name}")
        targets[name.removeprefix("measure-").removesuffix(".target")] = offsets
    return targets


def freeze_neutral(directory: Path, artifact_directory: Path, *, with_morphs: bool = False) -> str:
    assets = _verified_assets(directory, ASSETS)
    mesh = _mesh(assets["base.obj"].decode("utf-8"))
    rig = _rig(json.loads(assets["default.mhskel"]),
               json.loads(assets["default_weights.mhw"]), mesh["vertices"])
    payload = {"schema_version": 1, "kind": "frozen_body", "source_asset_digests": ASSETS,
               "algorithm_version": "makehuman-neutral-v1", "mesh": mesh, "rig": rig}
    if with_morphs:
        morph_assets = _verified_assets(directory, MORPH_ASSETS)
        payload["source_asset_digests"] = ASSETS | MORPH_ASSETS
        payload["morph_targets"] = _morph_targets(morph_assets, len(mesh["vertices"]))
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
