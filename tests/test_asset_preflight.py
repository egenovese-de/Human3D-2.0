import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from human3d import asset_preflight as preflight
from human3d import bootstrap, vision

class AssetPreflightTests(unittest.TestCase):
    def test_manifest_contract(self):
        root = Path(__file__).resolve().parents[1]/"DOCS"/"manifests"
        manifests = [json.loads(p.read_text(encoding="utf-8")) for p in root.glob("makehuman*.json")]
        # Compare filename and digest pairs without assuming manifest nesting.
        def pairs(node):
            if isinstance(node, dict):
                if "path" in node and "sha256" in node:
                    yield Path(node["path"]).name, node["sha256"]
                for value in node.values():
                    yield from pairs(value)
            elif isinstance(node, list):
                for value in node:
                    yield from pairs(value)
        entries = {pair for m in manifests for pair in pairs(m)}
        for name, digest in (bootstrap.ASSETS | bootstrap.MORPH_ASSETS | bootstrap.TORSO_ASSETS).items():
            self.assertIn((name,digest),entries)

    def test_missing_corrupt_and_valid_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root/"model.task"
            data = b"synthetic asset"
            digest = hashlib.sha256(data).hexdigest()
            with patch.object(preflight,"MODEL_SHA256",digest), patch.object(preflight,"ASSETS",{"base.obj":digest}), patch.object(preflight,"MORPH_ASSETS",{"limb.target":digest}), patch.object(preflight,"TORSO_ASSETS",{"torso.target":digest}), patch("socket.socket",side_effect=AssertionError("network forbidden")):
                self.assertEqual(preflight.verify_assets(model,root)["status"],"FAIL")
                for name in ("model.task","base.obj","limb.target"):
                    (root/name).write_bytes(data)
                self.assertEqual(preflight.verify_assets(model,root,full_morphs=False)["status"],"PASS")
                self.assertEqual(preflight.verify_assets(model,root)["status"],"FAIL")
                (root/"torso.target").write_bytes(data)
                self.assertEqual(preflight.verify_assets(model,root)["status"],"PASS")
                model.write_bytes(b"corrupt")
                report = preflight.verify_assets(model,root)
                self.assertEqual(report["assets"][0]["status"],"DIGEST_MISMATCH")

    def test_production_rejects_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root/"model.task"
            model.write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError,"pose_model_digest_mismatch"):
                vision.PoseLandmarker(model)
            with self.assertRaises(FileNotFoundError):
                vision.PoseLandmarker(root/"missing.task")
            (root/"base.obj").write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError,"Bootstrap asset integrity mismatch"):
                bootstrap.freeze_neutral(root,root/"output")
            self.assertFalse((root/"output").exists())
