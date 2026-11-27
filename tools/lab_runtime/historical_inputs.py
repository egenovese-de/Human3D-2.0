"""Fail closed on missing or changed historical inputs; never download or publish them."""
import json
from pathlib import Path
from bootstrap import ROOT, safe, digest

def verify_group(workspace, group, directory):
    inventory = ROOT / "DOCS/q/finalization/input-hashes.json"
    rows = json.loads(inventory.read_text())[group]
    if not rows:
        raise ValueError("empty historical inventory")
    verified = {}
    for fixture, files in rows.items():
        for name, expected in files.items():
            rel = f"{directory}/{fixture}/{name}"
            path = safe(workspace, rel)
            if not path.is_file() or digest(path) != expected:
                raise ValueError("missing or changed historical input: " + rel)
            verified[rel] = expected
    return {"inventory_sha256":digest(inventory), "files":verified}


def verify_holdout(workspace):
    return verify_group(workspace, "holdout", "holdout")

def verify_rig(workspace):
    return verify_group(workspace, "rig_fixtures", "rig-fixtures")
