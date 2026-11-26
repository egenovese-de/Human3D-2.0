"""Offline asset preflight; never downloads or modifies assets."""
import argparse
import hashlib
import json
from pathlib import Path
from .bootstrap import ASSETS, MORPH_ASSETS, TORSO_ASSETS
from .vision import MODEL_SHA256

def verify_assets(model: Path, directory: Path, *, full_morphs=True):
    expected = ASSETS | MORPH_ASSETS
    if full_morphs or any((directory / n).exists() for n in TORSO_ASSETS):
        expected |= TORSO_ASSETS
    entries = [("model", model, MODEL_SHA256)]
    entries.extend((name, directory / name, digest) for name, digest in expected.items())
    results = []
    for name, path, digest in entries:
        try:
            with path.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            status = "PASS" if actual == digest else "DIGEST_MISMATCH"
        except FileNotFoundError:
            status = "MISSING"
        except OSError:
            status = "UNREADABLE"
        results.append({"asset": name, "status": status})
    return {"status": "PASS" if all(r["status"] == "PASS" for r in results) else "FAIL",
            "assets": results, "full_morphs_required": full_morphs}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--legacy-morphs", action="store_true",
                        help="Allow all six torso targets to be absent, matching legacy freeze behavior")
    args = parser.parse_args()
    report = verify_assets(args.model, args.assets, full_morphs=not args.legacy_morphs)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
