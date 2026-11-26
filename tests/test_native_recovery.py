import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch
from hashlib import sha256
import numpy as np
from human3d.vision import PoseLandmarker, _NativePoseLandmarker, SubjectEvidence
from human3d.observations import ObservationStore

class NativeRecovery(unittest.TestCase):
    def test_worker_failure_modes_and_retry(self):
        with TemporaryDirectory() as directory:
            model = Path(directory)/"model.task"
            model.write_bytes(b"fixture")
            photo = Path(directory)/"photo.png"
            with patch("human3d.vision.MODEL_SHA256",sha256(b"fixture").hexdigest()):
                detector = PoseLandmarker(model)
            evidence = SubjectEvidence("photo","model",(16,16),())
            def recover(command, **kwargs):
                digest = ObservationStore(Path(command[6])).write_detection(evidence)
                return CompletedProcess(command,0,digest,"")
            for failure, message in [
                (OSError("launch"),"could not start"),
                (TimeoutExpired("worker",120),"timed out"),
                (CompletedProcess([],0,"garbage",""),"invalid evidence"),
                (CompletedProcess([],0,"a"*64,""),"invalid evidence"),
                (CompletedProcess([],-6,"",""),"detector failed"),
            ]:
                with self.subTest(message=message):
                    with patch("human3d.vision.run_cancellable",side_effect=[failure] if isinstance(failure,Exception) else None,return_value=failure):
                        with self.assertRaisesRegex(RuntimeError,message):
                            detector.detect(photo,"photo")
                    with patch("human3d.vision.run_cancellable",side_effect=recover):
                        self.assertEqual(detector.detect(photo,"photo"),evidence)
            with patch("human3d.vision.run_cancellable",return_value=CompletedProcess([],1,"photo_digest_mismatch","")):
                with self.assertRaisesRegex(ValueError,"photo_digest_mismatch"):
                    detector.detect(photo,"photo")

    def test_invalid_segmentation(self):
        valid = np.array([[0.,1.],[1.,0.]],dtype=np.float32)
        for size in [(0,2),(2,0),(3,2),(2,3),(-1,2)]:
            with self.subTest(size=size):
                self.assertIsNone(_NativePoseLandmarker._mask_png(valid,(2,2),size))
        for mask in [np.full((2,2),np.nan),np.full((2,2),np.inf),np.full((2,2),-1.),np.full((2,2),2.),np.zeros((2,2)),np.ones((2,2)),np.zeros((3,2))]:
            self.assertIsNone(_NativePoseLandmarker._mask_png(mask,(2,2)))
        self.assertIsNotNone(_NativePoseLandmarker._mask_png(valid,(2,2)))
