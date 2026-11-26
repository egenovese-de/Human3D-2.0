"""Verify pinned CC0 assets without persisting downloaded bytes."""
import hashlib
import json
from pathlib import Path, PurePosixPath
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
REV = "1f508f6083b2f823dab15de924b3bde72e08d77c"
BASE = "https://raw.githubusercontent.com/makehumancommunity/makehuman/" + REV + "/"

def main():
    count = 0
    for name in ("makehuman-v1.3.0.json", "makehuman-morph02.json"):
        manifest = json.loads((ROOT / "DOCS" / "manifests" / name).read_text())
        if manifest["revision"] != REV:
            raise ValueError("Unexpected revision")
        for item in manifest["files"]:
            path = manifest.get("source_prefix", "") + item["path"]
            parts = PurePosixPath(path).parts
            if not parts or ".." in parts or path.startswith("/") or any(c in path for c in "?#\\"):
                raise ValueError("Invalid asset path")
            with urlopen(BASE + path, timeout=60) as response:
                data = response.read(item["bytes"] + 1)
            if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError("Integrity mismatch: " + path)
            count += 1
    print(f"PASS: {count} manifest entries verified")

if __name__ == "__main__":
    main()
