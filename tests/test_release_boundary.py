"""Protect the distinction between historical Lab renders and release assets."""
import os
from pathlib import Path
import runpy
import subprocess
from tempfile import TemporaryDirectory
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "check_release_boundary.py"


class ReleaseBoundaryTests(unittest.TestCase):
    def git(self, root, *args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True, stderr=subprocess.DEVNULL).strip()

    def test_exact_lab_blob_is_denied_when_release_can_reach_it(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.git(root, "init", "-b", "main")
            self.git(root, "config", "user.name", "Boundary fixture")
            self.git(root, "config", "user.email", "boundary@example.invalid")
            self.git(root, "commit", "--allow-empty", "-m", "release base")
            self.git(root, "switch", "-c", "lab/render")
            path = "DOCS/q/fixture.png"
            asset = root / path
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"fixture")
            self.git(root, "add", path)
            self.git(root, "commit", "-m", "Lab render")
            blob_id = self.git(root, "rev-parse", f"HEAD:{path}")
            self.git(root, "switch", "main")

            module = runpy.run_path(str(SCRIPT))
            module["Q_RENDER_BLOBS"][path] = blob_id
            old_directory = Path.cwd()
            try:
                os.chdir(root)
                self.assertEqual(module["_audit_history"](), 2)
                self.git(root, "branch", "production", "lab/render")
                with self.assertRaisesRegex(SystemExit, "Prohibited asset path"):
                    module["_audit_history"]()
                self.git(root, "branch", "-D", "production")
                self.git(root, "switch", "lab/render")
                asset.write_bytes(b"replacement bytes")
                self.git(root, "add", path)
                self.git(root, "commit", "-m", "Changed render")
                with self.assertRaisesRegex(SystemExit, "Prohibited asset path"):
                    module["_audit_history"]()
            finally:
                os.chdir(old_directory)
