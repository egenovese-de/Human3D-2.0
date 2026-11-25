import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from human3d.project import PhotoSet
from human3d.project_store import ProjectStore, RevisionConflict
from human3d.originals import OriginalStore


class ProjectTests(unittest.TestCase):
    def test_photo_set(self):
        first = PhotoSet().add("a" * 64, "a.png")
        second = first.add("b" * 64, "b.png")
        self.assertEqual(second.add("a" * 64, "duplicate.png"), second)
        self.assertEqual(len(first.photos), 1)
        target = second.photos[1].id
        selected = second.select(target)
        self.assertEqual(selected.target, target)
        with self.assertRaises(ValueError):
            selected.include(target, False)
        excluded = selected.include(first.target, False)
        with self.assertRaises(ValueError):
            excluded.select(first.target)

    def test_roundtrip_conflict_and_failed_replace(self):
        with tempfile.TemporaryDirectory() as root:
            store = ProjectStore(Path(root))
            project = store.create()
            edited = project.with_photos(project.photos.add("a" * 64, "a.png"))
            saved = store.save(edited)
            self.assertEqual(store.load(), saved)
            self.assertEqual(saved.revision, 1)
            with self.assertRaises(RevisionConflict):
                store.save(edited)
            before = store.snapshot.read_bytes()
            with patch("human3d.project_store.os.replace", side_effect=OSError):
                with self.assertRaises(OSError):
                    store.save(saved)
            self.assertEqual(store.snapshot.read_bytes(), before)
            self.assertEqual({p.name for p in Path(root).iterdir()}, {"project.json", ".writer.lock"})
            store.snapshot.write_text('{"schema_version": 99}', encoding="utf-8")
            with self.assertRaises(ValueError):
                store.load()

    def test_originals(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "input.bin"
            source.write_bytes(b"original bytes")
            store = OriginalStore(Path(root) / "project")
            digest = store.put(source)
            self.assertEqual(digest, hashlib.sha256(b"original bytes").hexdigest())
            self.assertEqual(store.put(source), digest)
            source.write_bytes(b"changed")
            self.assertEqual(store.verify(digest).read_bytes(), b"original bytes")
            store.path(digest).write_bytes(b"corrupt")
            with self.assertRaises(ValueError):
                store.verify(digest)

    def test_concurrent_writers(self):
        with tempfile.TemporaryDirectory() as root:
            store = ProjectStore(Path(root))
            store.create()
            script = """
import sys
from pathlib import Path
from human3d.project_store import ProjectStore, RevisionConflict
from human3d.project import Project
store = ProjectStore(Path(sys.argv[1]))
project = Project(sys.argv[2])
try:
    store.save(project)
except RevisionConflict:
    sys.exit(3)
"""
            args = [sys.executable, "-c", script, root, store.load().id]
            processes = [subprocess.Popen(args) for _ in range(2)]
            try:
                results = sorted(p.wait(timeout=30) for p in processes)
                self.assertEqual(results, [0, 3])
                self.assertEqual(store.load().revision, 1)
            finally:
                for p in processes:
                    if p.poll() is None:
                        p.kill()
                        p.wait()

    def test_persistent_import(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source = root / "input.bin"
            source.write_bytes(b"first original")
            store = ProjectStore(root / "project")
            store.create()
            saved, added = store.import_original(source)
            self.assertTrue(added)
            self.assertEqual(saved.revision, 1)
            self.assertEqual(store.import_original(source), (saved, False))
            source.write_bytes(b"second original")
            with patch("human3d.project_store.os.replace", side_effect=OSError):
                with self.assertRaises(OSError):
                    store.import_original(source)
            self.assertEqual(store.load(), saved)
            updated, added = store.import_original(source)
            self.assertTrue(added)
            self.assertEqual(updated.revision, 2)
            source.unlink()
            reopened = ProjectStore(root / "project").load()
            self.assertEqual(reopened, updated)
            originals = OriginalStore(root / "project")
            self.assertEqual(originals.verify(reopened.photos.photos[0].digest).read_bytes(),
                             b"first original")
            self.assertEqual(originals.verify(reopened.photos.photos[1].digest).read_bytes(),
                             b"second original")
