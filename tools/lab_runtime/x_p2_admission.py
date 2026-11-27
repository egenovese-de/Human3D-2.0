"""Publish only the P2 synthetic geometry evidence and runtime provenance."""

import argparse
import json
from pathlib import Path
import os
import shutil
import subprocess

from artifacts import verify
from bootstrap import ROOT, digest
from x_p1_admission import require_inventory, negative_control

SOURCE = "e0ae4eae57347466b5757bbcdaaa7194bdd31c94"
FILES = ("metrics.json", "meshes.json", "intersections.json")
ASSETS = ("DOCS/manifests/makehuman-v1.3.0.json", "lab/manifests/makehuman-anatomical-torso.json",
          "lab/manifests/makehuman-p1-anatomy.json", "DOCS/LAB_RUNTIME_LICENSES.md", "LICENSE")


def stage(source, runtime, destination):
    negative_control()
    require_inventory(source, set(FILES))
    verified = json.loads((runtime / "runtime_report.json").read_text())
    checks = {row["name"]: row["status"] for row in verified["checks"]}
    if verified["status"] != "PASS" or verified["source_revision"] != SOURCE:
        raise ValueError("P2 requires verified application source")
    for group in ("foundation", "anatomical_torso", "p1_anatomy"):
        if checks.get(f"assets:{group}") != "PASS":
            raise ValueError(f"Unverified asset group: {group}")
    metrics = json.loads((source / "metrics.json").read_text())
    intersections = json.loads((source / "intersections.json").read_text())
    if metrics["source_revision"] != SOURCE or len(metrics["rows"]) != 36 or len(intersections) != 40:
        raise ValueError("Incomplete P2 evidence")

    destination.mkdir(parents=True, exist_ok=False)
    for name in FILES:
        shutil.copyfile(source / name, destination / name)
    shutil.copyfile(runtime / "runtime_report.json", destination / "runtime_report.json")
    for name in ASSETS:
        shutil.copyfile(ROOT / name, destination / Path(name).name)
    manifest = {
        "schema_version": 1,
        "scope": "MakeHuman CC0-1.0 derived synthetic geometry, Apache-2.0 benchmark",
        "attribution": "MakeHuman Community, https://github.com/makehumancommunity/makehuman",
        "retention_days": 7,
        "source_revision": SOURCE,
        "lab_revision": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "files": {p.name: {"sha256": digest(p), "bytes": p.stat().st_size}
                  for p in sorted(destination.iterdir())},
    }
    (destination / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    verify(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    stage(args.input, args.runtime, args.output)
