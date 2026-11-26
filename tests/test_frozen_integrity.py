import unittest
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from human3d.frozen_body import load_frozen_body

class FrozenIntegrity(unittest.TestCase):
    def test_hash_valid_structure_and_corruption(self):
        body = {"schema_version":1,"kind":"frozen_body",
                "mesh":{"vertices":[[0,0,0],[1,0,0],[0,1,0]],"texcoords":[[0,0],[1,0],[0,1]],"faces":[{"group":"body","corners":[[0,0],[1,1],[2,2]]}]},
                "rig":{"joints":{"a":[0,0,0],"b":[0,1,0]},"joint_vertices":{"a":[0],"b":[2]},"bones":{"root":{"head":"a","tail":"b","parent":None}},"skin":[{"root":1.}]*3}}
        with TemporaryDirectory() as tmp:
            def write(value):
                data = json.dumps(value).encode()
                path = Path(tmp)/(hashlib.sha256(data).hexdigest()+".json")
                path.write_bytes(data)
                return path
            path = write(body)
            self.assertEqual(load_frozen_body(path),body)
            path.write_bytes(b"{}")
            with self.assertRaisesRegex(ValueError,"digest_mismatch"):
                load_frozen_body(path)
            for mutation in ("vertex","face","uv","cycle","skin","joint","morph"):
                with self.subTest(mutation=mutation):
                    bad = deepcopy(body)
                    if mutation == "vertex": bad["mesh"]["vertices"][0][0] = float("nan")
                    if mutation == "face": bad["mesh"]["faces"][0]["corners"][0][0] = -1
                    if mutation == "uv": bad["mesh"]["faces"][0]["corners"][0][1] = 3
                    if mutation == "cycle": bad["rig"]["bones"]["root"]["parent"] = "root"
                    if mutation == "skin": bad["rig"]["skin"][0] = {"root":.5}
                    if mutation == "joint": bad["rig"]["joint_vertices"]["a"] = [3]
                    if mutation == "morph": bad["morph_targets"] = {"bad":[[-1,0,0,0]]}
                    with self.assertRaisesRegex(ValueError,"invalid_frozen_body_structure"):
                        load_frozen_body(write(bad))

    def test_frozen_binding_invalidates_artifacts(self):
        from dataclasses import replace
        from human3d.session import Session
        with TemporaryDirectory() as tmp:
            session = Session(Path(tmp),create=True)
            project = session.store.load()
            project = session.store.save(replace(project,frozen_body_digest="a"*64))
            session.snapshot()
            job = session.coordinator.submit("preview")
            session.coordinator.start(job.id)
            self.assertTrue(session.coordinator.finish(job.id,"preview",lambda result: True))
            self.assertIn("preview",session.snapshot().current_artifacts)
            session.store.save(replace(project,frozen_body_digest="b"*64))
            snapshot = session.snapshot()
            self.assertNotIn("preview",snapshot.current_artifacts)
            self.assertIn("preview",snapshot.stale_artifacts)
