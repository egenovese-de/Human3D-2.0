"""Stage the P1 publication bundle using the Lab artifact manifest format."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

from artifacts import verify
from bootstrap import ROOT, digest

SOURCE = "e0ae4eae57347466b5757bbcdaaa7194bdd31c94"
SUBJECTS = ("dev01", "dev02", "hold01", "hold02")
RETENTION = 7


def inventory(root):
    files = set()
    for path in root.rglob("*"):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError(f"Invalid artifact input: {path}")
        if path.is_file():
            files.add(path.relative_to(root).as_posix())
    return files


def require_inventory(root, expected):
    actual = inventory(root)
    if actual != expected:
        raise ValueError(f"Unexpected output inventory in {root}: extra={sorted(actual - expected)}, missing={sorted(expected - actual)}")


def stage(root, runtime, out):
    runtime_file = runtime / "runtime_report.json"
    verification = json.loads(runtime_file.read_text())
    if verification["status"] != "PASS" or verification["source_revision"] != SOURCE:
        raise ValueError("P1 requires the verified pinned application source")
    checks = {row["name"]: row["status"] for row in verification["checks"]}
    for group in ("foundation", "anatomical_torso", "p1_anatomy"):
        if checks.get(f"assets:{group}") != "PASS":
            raise ValueError(f"Unverified asset group: {group}")

    pilot = root / "x-p1"
    metrics = json.loads((pilot / "metrics.json").read_text())
    if metrics["source_revision"] != SOURCE:
        raise ValueError("Pilot source revision mismatch")
    assets = set()
    for row in metrics["persistence"]:
        fp = f'{row["frozen_sha256"]}.json'
        usd = f'{row["subject"]}.usdz'
        if row["subject"] not in SUBJECTS or len(fp) != 69 or not all(c in "0123456789abcdef" for c in fp[:-5]):
            raise ValueError("Invalid persisted asset record")
        if digest(pilot / "assets" / fp) != row["frozen_sha256"] or digest(pilot / "assets" / usd) != row["usdz_sha256"]:
            raise ValueError("Persisted asset checksum mismatch")
        assets.update((fp, usd))
    if len(assets) != 8:
        raise ValueError("Expected four distinct frozen bodies and four USDZ files")
    renders = {"render_report.json"} | {
        f"{subject}_{variant}_{view}.png"
        for subject in ("hold01", "hold02")
        for variant in ("expanded_truth", "macro_only_expanded", "weight_muscle_expanded", "expanded_expanded")
        for view in ("front", "side", "threequarter")
    }
    editable = {"editable.json", *(f"{s}.blend" for s in SUBJECTS)}
    require_inventory(pilot / "assets", assets)
    require_inventory(root / "x-p1-renders", renders)
    require_inventory(root / "x-p1-editable", editable)

    out.mkdir(parents=True, exist_ok=False)
    publish = {"x-p1/metrics.json", "x-p1-editable/editable.json"}
    publish.update(f"x-p1/assets/{f}" for f in assets)
    publish.update(f"x-p1-renders/{f}" for f in renders)
    for name in sorted(publish):
        src = root / name
        if src.is_symlink() or not src.is_file():
            raise ValueError(f"Invalid publication source: {name}")
        dest = out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    shutil.copyfile(runtime_file, out / "runtime_report.json")
    shutil.copyfile(ROOT / "LICENSE", out / "LICENSE")
    for name in ("makehuman-v1.3.0.json", "makehuman-anatomical-torso.json", "makehuman-p1-anatomy.json"):
        paths = [ROOT / parent / name for parent in ("DOCS/manifests", "lab/manifests")]
        shutil.copyfile(next(p for p in paths if p.is_file()), out / name)
    manifest = {
        "schema_version": 1,
        "scope": "MakeHuman CC0-1.0 derived geometry and synthetic renders; repository Apache-2.0 procedural code",
        "attribution": "MakeHuman Community, https://github.com/makehumancommunity/makehuman",
        "retention_days": RETENTION,
        "source_revision": SOURCE,
        "lab_revision": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "files": {name: {"sha256": digest(out / name), "bytes": (out / name).stat().st_size} for name in sorted(inventory(out))},
    }
    (out / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    verify(out)


def negative_control():
    with TemporaryDirectory() as d:
        root = Path(d)
        (root / "unauthorized.task").write_bytes(b"negative control")
        try:
            require_inventory(root, set())
        except ValueError as exc:
            if "unauthorized.task" in str(exc):
                print("X_P1_ADMISSION_NEGATIVE_PASS")
                return
            raise
    raise RuntimeError("Unexpected artifact was accepted")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    negative_control()
    stage(args.root, args.runtime, args.output)
