"""Local subject candidates in normalized, EXIF-oriented image coordinates."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from PIL import Image, ImageOps

MODEL_SHA256 = "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a"


@dataclass(frozen=True)
class Landmark:
    x: float
    y: float
    visibility: float | None
    presence: float | None


@dataclass(frozen=True)
class SubjectEvidence:
    photo_digest: str
    model_digest: str
    image_size: tuple[int, int]
    candidates: tuple[tuple[Landmark, ...], ...]


class PoseLandmarker:
    """Use the explicitly provisioned MediaPipe Lite v1 model on CPU."""

    def __init__(self, model_path: Path):
        model = model_path.read_bytes()
        if sha256(model).hexdigest() != MODEL_SHA256:
            raise ValueError("pose_model_digest_mismatch")
        from mediapipe import Image as MediaPipeImage, ImageFormat, tasks
        import numpy as np

        self._array = np.asarray
        self._image = MediaPipeImage
        self._format = ImageFormat.SRGB
        options = tasks.vision.PoseLandmarkerOptions(
            base_options=tasks.BaseOptions(model_asset_buffer=model),
            num_poses=4,
        )
        self._detector = tasks.vision.PoseLandmarker.create_from_options(options)

    def detect(self, original_path: Path, photo_digest: str) -> SubjectEvidence:
        with original_path.open("rb") as source:
            if sha256(source.read()).hexdigest() != photo_digest:
                raise ValueError("photo_digest_mismatch")
            source.seek(0)
            with Image.open(source) as photo:
                image = ImageOps.exif_transpose(photo).convert("RGB")
        result = self._detector.detect(self._image(image_format=self._format, data=self._array(image)))
        candidates = tuple(
            tuple(Landmark(point.x, point.y, point.visibility, point.presence) for point in pose)
            for pose in result.pose_landmarks
        )
        return SubjectEvidence(photo_digest, MODEL_SHA256, image.size, candidates)

    def close(self):
        self._detector.close()
