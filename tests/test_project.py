import hashlib
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
