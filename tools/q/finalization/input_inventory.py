"""Record and verify the immutable meshes, photographs and auxiliary input hashes."""
import argparse
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def inventory(previous, followup, fixture_index):
    data = {"holdout": {}, "rig_fixtures": {}, "auxiliary": {}}
    for folder in sorted((previous / "holdout").glob("*_bend*")):
        metadata = json.loads((folder / "manifest.json").read_text())
        files = {name: digest(folder / name) for name in ("manifest.json", "mesh.json")}
        # Most holdout manifests report mesh bytes. The raw digest is authoritative here.
        for view in metadata["images"]:
            name = view["file"]
            files[name] = digest(folder / name)
            assert files[name] == view["sha256"], (folder.name, name)
            composite = folder / f"rgb-{name}"
            if composite.exists():
                files[composite.name] = digest(composite)
        data["holdout"][folder.name] = files
    for record in json.loads(fixture_index.read_text()):
        folder = followup / "rig-fixtures" / record["fixture"]
        files = {"mesh.json": digest(folder / "mesh.json"), "manifest.json": digest(folder / "manifest.json")}
        assert files["mesh.json"] == record["mesh_sha256"]
        assert files["manifest.json"] == record["manifest_sha256"]
        for view in record["images"]:
            name = view["file"]
            files[name] = digest(folder / name)
            assert files[name] == view["sha256"]
        data["rig_fixtures"][folder.name] = files
    for path in (previous / "assets/pose.task", previous / "holdout-results.json", followup / "visibility.json"):
        data["auxiliary"][path.name] = digest(path)
    for path in sorted((followup / "clothes").glob("*/*/layer_0.json")):
        data["auxiliary"][path.relative_to(followup).as_posix()] = digest(path)
    for path in sorted((previous / "holdout-mixed-inputs").glob("*/*.png")):
        data["auxiliary"][path.relative_to(previous).as_posix()] = digest(path)
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for arg in ("previous", "followup", "fixture_index", "output"):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    result = inventory(args.previous, args.followup, args.fixture_index)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
