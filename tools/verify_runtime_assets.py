"""Explicit CI-only provisioning followed by offline verification; no asset publication."""
import json
import tempfile
from pathlib import Path
from urllib.request import urlopen
from unittest.mock import patch
from human3d.bootstrap import ASSETS, MORPH_ASSETS, TORSO_ASSETS, freeze_neutral
from human3d.asset_preflight import verify_assets
from human3d.vision import PoseLandmarker

ROOT = Path(__file__).resolve().parents[1]
REV = "1f508f6083b2f823dab15de924b3bde72e08d77c"
BASE = "https://raw.githubusercontent.com/makehumancommunity/makehuman/" + REV + "/"
MODEL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"

def main():
    expected = ASSETS | MORPH_ASSETS | TORSO_ASSETS
    sources = {}
    for manifest in (ROOT/"DOCS"/"manifests").glob("makehuman*.json"):
        m = json.loads(manifest.read_text(encoding="utf-8"))
        assert m["revision"] == REV
        for item in m["files"]:
            name = Path(item["path"]).name
            if expected.get(name) == item["sha256"]:
                sources[name] = (BASE + m.get("source_prefix","") + item["path"], item["bytes"])
    assert sources.keys() == expected.keys()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        assets = root/"assets"
        assets.mkdir()
        for name,(url,size) in sources.items():
            with urlopen(url,timeout=60) as response:
                data = response.read(size+1)
            assert len(data) == size, name
            (assets/name).write_bytes(data)
        model = root/"model.task"
        with urlopen(MODEL,timeout=60) as response:
            model.write_bytes(response.read(32*1024*1024))
        with patch("socket.socket",side_effect=AssertionError("network forbidden")):
            report = verify_assets(model,assets)
            print(json.dumps(report),flush=True)
            assert report["status"] == "PASS"
            PoseLandmarker(model).close()
            digest = freeze_neutral(assets,root/"frozen",with_morphs=True)
            body = json.loads((root/"frozen"/(digest+".json")).read_text())
            assert len(body["morph_targets"]) == 14
            assert body["source_asset_digests"] == expected
            print("Actual pinned assets: PASS; frozen digest:",digest,flush=True)

if __name__ == "__main__":
    main()
