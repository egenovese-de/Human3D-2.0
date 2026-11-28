"""Download pinned application assets during setup and verify them offline."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from urllib.request import urlopen
from zipfile import ZipFile

from human3d.asset_preflight import verify_assets
from human3d.bootstrap import ASSETS, MORPH_ASSETS, TORSO_ASSETS
from human3d.vision import MODEL_SHA256

ROOT = Path(__file__).resolve().parents[1]


def provision(destination, *, experimental=True):
    expected = ASSETS | MORPH_ASSETS | TORSO_ASSETS
    found = {}
    for manifest in (ROOT / "DOCS" / "manifests").glob("makehuman*.json"):
        data = json.loads(manifest.read_text(encoding="utf-8"))
        base = "https://raw.githubusercontent.com/makehumancommunity/makehuman/" + data["revision"] + "/"
        for item in data["files"]:
            name = Path(item["path"]).name
            if expected.get(name) == item["sha256"]:
                found[name] = (base + data.get("source_prefix", "") + item["path"], item["bytes"])
    if found.keys() != expected.keys():
        raise ValueError("Runtime asset manifests do not match the application.")
    model = json.loads((ROOT / "DOCS/manifests/m7-pose-model.json").read_text(encoding="utf-8"))
    if model["sha256"] != MODEL_SHA256:
        raise ValueError("Pose model manifest does not match the application.")
    assets = destination / "makehuman"
    for name, (url, size) in found.items():
        download(assets / name, url, size, expected[name])
    download(destination / "pose.task", model["url"], model["bytes"], MODEL_SHA256)
    report = verify_assets(destination / "pose.task", assets)
    if report["status"] != "PASS":
        raise ValueError(json.dumps(report))
    print(f"Verified {len(report['assets'])} runtime assets.")
    if experimental:
        provision_native(destination)


def provision_native(destination):
    registry = ROOT / "DOCS/manifests/m7-g1-native.json"
    # Git may expand canonical text to CRLF in an existing Windows checkout.
    canonical = registry.read_bytes().replace(b"\r\n", b"\n")
    doc = json.loads(canonical)
    archive = json.loads((ROOT / "DOCS/manifests/m7-g1-archive.json").read_text(encoding="utf-8"))
    if sha256(canonical).hexdigest() != archive["registry_sha256"] or doc["upstream"] != archive["revision"]:
        raise ValueError("Native registry integrity failure.")
    native = destination / "native"

    def verified(path, size, digest):
        return path.is_file() and path.stat().st_size == size and sha256(path.read_bytes()).hexdigest() == digest

    needed = [(name, digest, size) for name, digest, size in doc["files"]
              if not verified(native / name, size, digest)]
    if needed:
        with TemporaryDirectory(dir=destination) as scratch:
            archive_path = Path(scratch) / "makehuman.zip"
            download(archive_path, archive["url"], archive["bytes"], archive["sha256"])
            with ZipFile(archive_path) as bundle:
                for name, digest, size in needed:
                    relative = Path(name)
                    if relative.is_absolute() or ".." in relative.parts or relative.suffix != ".target":
                        raise ValueError("Unexpected native registry path.")
                    member = archive["prefix"] + name
                    if bundle.getinfo(member).file_size != size:
                        raise ValueError(f"Native target size mismatch: {name}")
                    data = bundle.read(member)
                    if sha256(data).hexdigest() != digest:
                        raise ValueError(f"Native target hash mismatch: {name}")
                    path = native / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
    (destination / "native-registry.json").write_bytes(canonical)
    print(f"Verified {len(doc['files'])} pinned G1 morph targets.")


def download(path, url, size, digest):
    if path.is_file() and path.stat().st_size == size and sha256(path.read_bytes()).hexdigest() == digest:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=60) as response:
        data = response.read(size + 1)
    if len(data) != size or sha256(data).hexdigest() != digest:
        raise ValueError(f"Download verification failed for {path.name}.")
    with NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--baseline-only", action="store_true")
    scope.add_argument("--experimental-only", action="store_true")
    args = parser.parse_args()
    if args.experimental_only:
        args.destination.mkdir(parents=True, exist_ok=True)
        provision_native(args.destination)
    else:
        provision(args.destination, experimental=not args.baseline_only)
