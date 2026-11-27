"""Default-deny admission for P3/P4 synthetic evidence, renders and assets."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from artifacts import verify
from bootstrap import ROOT, digest, safe
from x_p1_admission import require_inventory, negative_control

SOURCE = "e0ae4eae57347466b5757bbcdaaa7194bdd31c94"
IMAGES = {"front.jpg", "side.jpg", "threequarter.jpg"}
FIXTURES = IMAGES | {"unified.raw.json", "specialized.raw.json", "prompt-unified.txt", "prompt-specialized.txt", "evidence.schema.json"}


def stage(run, runtime, out):
    negative_control()
    verify_runtime = json.loads((runtime / "runtime_report.json").read_text())
    checks = {r["name"]: r["status"] for r in verify_runtime["checks"]}
    if verify_runtime["status"] != "PASS" or verify_runtime["source_revision"] != SOURCE:
        raise ValueError("Unverified P3/P4 runtime source")
    if any(checks.get("assets:" + g) != "PASS" for g in ("foundation", "morph02", "anatomical_torso", "p1_anatomy")):
        raise ValueError("Unverified P3/P4 assets")
    fixture = ROOT / "lab/fixtures/x-vlm"
    require_inventory(fixture, FIXTURES)
    report = json.loads((run / "metrics.json").read_text())
    if report["source_revision"] != SOURCE or len(report["p3"]) != 48 or len(report["p4"]) != 10:
        raise ValueError("Incomplete P3/P4 evidence")
    if report["image_and_prompt_hashes"] != {name: digest(fixture / name) for name in FIXTURES}:
        raise ValueError("Source evidence hash mismatch")
    assets = {}
    mesh_names = set()
    for row in report["p4"]:
        asset = row["asset"]
        mesh_names.update((f'{row["subject"]}-truth', f'{row["subject"]}-{row["mode"].lower()}'))
        assets["assets/" + asset["frozen"]] = asset["frozen_sha256"]
        for export in asset["exports"]:
            assets["assets/" + export["name"]] = export["sha256"]
    if len(assets) != 30 or any(digest(safe(run, name)) != checksum for name, checksum in assets.items()):
        raise ValueError("Asset inventory integrity failure")
    render_names = {f"{mesh}_{view}.png" for mesh in mesh_names for view in ("front", "threequarter")}
    expected = set(assets) | {"meshes.json", "metrics.json", "renders/render_report.json"} | {f"renders/{name}" for name in render_names}
    require_inventory(run, expected)
    out.mkdir(parents=True, exist_ok=False)
    files = {name: run / name for name in expected}
    files.update({f"observations/{name}": fixture / name for name in FIXTURES})
    files["runtime_report.json"] = runtime / "runtime_report.json"
    for name in ("LICENSE", "DOCS/LAB_RUNTIME_LICENSES.md", "DOCS/manifests/makehuman-v1.3.0.json",
                 "DOCS/manifests/makehuman-morph02.json", "lab/manifests/makehuman-anatomical-torso.json",
                 "lab/manifests/makehuman-p1-anatomy.json"):
        files[Path(name).name] = ROOT / name
    for name, source in files.items():
        target = safe(out, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    manifest = {
        "schema_version": 1,
        "source_revision": SOURCE,
        "lab_revision": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
        "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "scope": "CC0-1.0 MakeHuman synthetic geometry; Apache-2.0 Lab benchmark and evidence",
        "attribution": "MakeHuman Community https://github.com/makehumancommunity/makehuman",
        "retention_days": 7,
        "files": {name: {"sha256": digest(out / name), "bytes": (out / name).stat().st_size} for name in sorted(files)},
    }
    (out / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    verify(out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("run", "runtime", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    stage(args.run, args.runtime, args.output)
