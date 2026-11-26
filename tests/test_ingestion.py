import tempfile
import unittest
from pathlib import Path
from io import BytesIO
from PIL import Image
from human3d.ingestion import import_photos, folder_inputs
from human3d.project_store import ProjectStore
from human3d.originals import OriginalStore
from human3d.thumbnails import thumbnail


class IngestionTests(unittest.TestCase):
    def test_mixed_folder(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            inputs = root / "inputs"
            inputs.mkdir()
            for i in range(3):
                Image.new("RGB", (320, 160), (i * 80, 0, 0)).save(inputs / f"{i}.png")
            (inputs / "duplicate.png").write_bytes((inputs / "0.png").read_bytes())
            (inputs / "broken.png").write_bytes(b"not an image")
            (inputs / "unsupported.txt").write_text("text")
            store = ProjectStore(root / "project")
            store.create()
            results = import_photos(store, folder_inputs(inputs))
            self.assertEqual([r.status for r in results].count("accepted"), 3)
            self.assertEqual([r.status for r in results].count("duplicate"), 1)
            self.assertEqual([r.status for r in results].count("rejected"), 2)
            project = store.load()
            self.assertEqual(len(project.photos.photos), 3)
            original = OriginalStore(store.directory)
            digest = project.photos.photos[0].digest
            with Image.open(BytesIO(thumbnail(original, digest))) as preview:
                self.assertEqual(preview.size, (160, 80))
            self.assertEqual(original.verify(digest).read_bytes(), (inputs / "0.png").read_bytes())
