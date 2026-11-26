import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import unittest
from unittest.mock import Mock, patch
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtWidgets import QApplication
from human3d.desktop import PhotosWindow
from human3d.anatomical_evidence import AnatomicalEvidence, RegionVisibility
from human3d.vision import SubjectEvidence, Landmark
from human3d.session import Session
from PIL import Image

class ProviderWiring(unittest.TestCase):
    def test_desktop_factory_native_and_optional(self):
        app = QApplication.instance() or QApplication([])
        native = Mock()
        provider = Mock()
        evidence = SubjectEvidence("photo","model",(32,32),((Landmark(.5,.5,1.,1.),)*33,))
        native.detect.return_value = evidence
        provider.observe.return_value = AnatomicalEvidence("photo","fixture","v1",0)
        with patch("human3d.desktop.PoseLandmarker",return_value=native):
            plain = PhotosWindow()
            configured = PhotosWindow(evidence_provider=provider)
            try:
                self.assertIs(plain._create_detector(Path("model")),native)
                adapter = configured._create_detector(Path("model"))
                self.assertEqual(adapter.detect(Path("photo"),"photo").anatomical,provider.observe.return_value)
                configured.session = Mock()
                configured.detect_references(["id"],Path("model"))
                configured.session.detect_photo.assert_called_once()
                self.assertEqual(configured.session.detect_photo.call_args.args[1].detect(Path("photo"),"photo").anatomical,provider.observe.return_value)
            finally:
                plain.close()
                configured.close()

    def test_provider_evidence_persists_and_reduces_fusion_regions(self):
        from human3d.anatomical_evidence import EvidenceAdapter
        with TemporaryDirectory() as directory:
            root = Path(directory)
            photo = root/"photo.png"
            Image.new("RGB",(32,32)).save(photo)
            session = Session(root/"project",create=True)
            session.ingest([photo])
            selected = session.snapshot().project.photos.photos[0]
            session.select_target(selected.id)
            native = Mock()
            native.detect.return_value = SubjectEvidence(selected.digest,"model",(32,32),((Landmark(.5,.5,1.,1.),)*33,))
            provider = Mock()
            provider.observe.return_value = AnatomicalEvidence(selected.digest,"fixture","v1",0,(RegionVisibility("left_arm",False,.95),))
            session.detect_target(EvidenceAdapter(native,provider))
            reopened = Session(root/"project")
            evidence = reopened.read_observation(selected.id)[0]
            self.assertEqual(evidence.anatomical,provider.observe.return_value)
            self.assertFalse(evidence.visible_pose(0)[13].observed)
            self.assertTrue(evidence.candidates[0][13].observed)
            self.assertEqual(reopened.shared_evidence().supporting_views("left_arm"),())
            self.assertEqual(reopened.shared_evidence().supporting_views("right_arm"),(selected.id,))
