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
            from human3d.frozen_body import load_frozen_body
            body = load_frozen_body(root/"frozen"/(digest+".json"))
            print("Canonical frozen structure: PASS",flush=True)
            from human3d.frozen_body import deform_vertices, morph_controls
            from human3d.native_rig import validate_rebind
            from copy import deepcopy
            original = deepcopy(body)
            frozen_path = root/"frozen"/(digest+".json")
            original_bytes = frozen_path.read_bytes()
            controls = {name: .125 for name in morph_controls(body)}
            vertices = deform_vertices(body, controls)
            assert len(vertices) == len(body["mesh"]["vertices"])
            assert vertices != tuple(map(tuple, body["mesh"]["vertices"]))
            validate_rebind(body, vertices)
            assert body == original
            assert freeze_neutral(assets,root/"frozen",with_morphs=True) == digest
            assert frozen_path.read_bytes() == original_bytes
            assert load_frozen_body(frozen_path) == original
            print("Canonical post-freeze deformation/rebind and repeat freeze immutability: PASS",flush=True)
            assert len(body["morph_targets"]) == 14
            assert body["source_asset_digests"] == expected
            from human3d.texture_bake import _hidden_vertices
            from human3d.anatomical_evidence import REGION_LANDMARKS
            rig = body["rig"]
            assert not _hidden_vertices(rig, ())
            regions = {name: _hidden_vertices(rig, (name,)) for name in REGION_LANDMARKS}
            for name, vertices in regions.items():
                assert vertices, ("empty canonical region", name)
                assert all(0 <= i < len(rig["skin"]) for i in vertices)
            for left, right in (("left_arm","right_arm"),("left_leg","right_leg")):
                assert not regions[left] & regions[right]
            print("Canonical hidden region mapping: PASS", json.dumps({name:len(vertices) for name,vertices in regions.items()},sort_keys=True),flush=True)
            print("Actual pinned assets: PASS; frozen digest:",digest,flush=True)

if __name__ == "__main__":
    main()
