"""Local subject candidates in normalized, EXIF-oriented image coordinates."""
from dataclasses import dataclass, replace
from hashlib import sha256
from io import BytesIO
from math import atan2, degrees, hypot, isfinite
from pathlib import Path
import subprocess
import sys
from threading import Event
from time import monotonic
from tempfile import TemporaryDirectory

from PIL import Image, ImageOps

from .anatomical_evidence import AnatomicalEvidence, apply_visibility

# Nose, shoulders, hips, knees and ankles in MediaPipe pose order.
TORSO_ANCHORS = (11, 12, 23, 24)
FULL_BODY_ANCHORS = (0, 11, 12, 23, 24, 25, 26, 27, 28)
MIN_ANCHOR_CONFIDENCE = 0.8

MODEL_SHA256 = "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a"
MAX_INFERENCE_EDGE = 2048
MASK_ROW_ALIGNMENT = 16


def _inference_image(image: Image.Image) -> tuple[Image.Image, tuple[int, int]]:
    image.thumbnail((MAX_INFERENCE_EDGE, MAX_INFERENCE_EDGE), Image.Resampling.LANCZOS)
    width, height = image.size
    # MediaPipe 0.10.33 aborts while copying padded float mask rows.
    aligned_width = ((width + MASK_ROW_ALIGNMENT - 1) // MASK_ROW_ALIGNMENT) * MASK_ROW_ALIGNMENT
    if aligned_width == width:
        return image, image.size
    padded = Image.new("RGB", (aligned_width, height))
    padded.paste(image)
    return padded, image.size


@dataclass(frozen=True)
class Landmark:
    x: float
    y: float
    visibility: float | None
    presence: float | None

    @property
    def observed(self) -> bool:
        return (
            0 <= self.x <= 1 and 0 <= self.y <= 1
            and self.visibility is not None and MIN_ANCHOR_CONFIDENCE <= self.visibility <= 1
            and self.presence is not None and MIN_ANCHOR_CONFIDENCE <= self.presence <= 1
        )


def estimate_world_yaw(pose, world):
    """Resolve front/back ambiguity using signed transverse torso axes."""
    if len(pose) != 33 or len(world) != 33:
        return None
    axes = []
    for left, right in ((11, 12), (23, 24)):
        if not (pose[left].observed and pose[right].observed):
            continue
        x = world[left][0] - world[right][0]
        z = world[left][2] - world[right][2]
        length = hypot(x, z)
        if isfinite(length) and length >= 0.05:
            axes.append(complex(x, z) / length)
    consensus = sum(axes)
    if len(axes) < 2 or abs(consensus) / len(axes) < 0.85:
        return None
    return degrees(atan2(consensus.imag, consensus.real))


@dataclass(frozen=True)
class VisionSuitability:
    mask_reason: str | None
    landmark_reason: str | None
    pose_reason: str | None


@dataclass(frozen=True)
class SubjectEvidence:
    photo_digest: str
    model_digest: str
    image_size: tuple[int, int]
    candidates: tuple[tuple[Landmark, ...], ...]
    masks: tuple[bytes | None, ...] = ()
    world_landmarks: tuple[tuple[tuple[float, float, float], ...], ...] = ()
    anatomical: AnatomicalEvidence | None = None

    def __post_init__(self):
        if self.anatomical is not None and (
            self.anatomical.photo_digest != self.photo_digest
            or self.anatomical.candidate >= len(self.candidates)
        ):
            raise ValueError("provider_evidence_binding_mismatch")

    def visible_pose(self, candidate: int):
        pose = self.candidates[candidate]
        world = self.world_landmarks[candidate] if candidate < len(self.world_landmarks) else ()
        yaw = estimate_world_yaw(pose, world)
        if yaw is not None and abs(yaw) > 100:
            pose = tuple(replace(point, visibility=0.0) if i <= 10 else point
                         for i, point in enumerate(pose))
        evidence = self.anatomical
        return apply_visibility(pose, evidence if evidence and evidence.candidate == candidate else None)

    @property
    def review_reason(self) -> str | None:
        if not self.candidates:
            return "no_subject_detected"
        if len(self.candidates) > 1:
            return "multiple_candidates"
        pose, = self.candidates
        if len(pose) != 33 or not all(pose[index].observed for index in FULL_BODY_ANCHORS):
            return "insufficient_full_body_evidence"
        return None


    def suitability(self, candidate: int) -> VisionSuitability:
        """Evaluate mask, torso-anchor and full-pose evidence independently."""
        if not 0 <= candidate < len(self.candidates):
            raise ValueError("invalid_subject_candidate")
        if len(self.candidates) > 1:
            return VisionSuitability("multiple_candidates", "multiple_candidates", "multiple_candidates")
        pose = self.visible_pose(candidate)
        landmarks = None if len(pose) == 33 and all(pose[i].observed for i in TORSO_ANCHORS) else (
            "insufficient_torso_evidence"
        )
        return VisionSuitability(self._mask_reason(candidate), landmarks, self.review_reason)

    def _mask_reason(self, candidate):
        mask = self.masks[candidate] if candidate < len(self.masks) else None
        if mask is None:
            return "mask_missing"
        try:
            with Image.open(BytesIO(mask)) as source:
                if source.size != self.image_size:
                    return "invalid_mask_geometry"
                image = source.convert("L")
                counts = image.histogram()
                bounds = image.getbbox()
        except (OSError, ValueError):
            return "invalid_mask_geometry"
        if not counts[0] or not counts[255] or any(counts[1:255]):
            return "invalid_mask_geometry"
        left, top, right, bottom = bounds
        width, height = self.image_size
        if left == 0 or top == 0 or right == width or bottom == height:
            return "mask_touches_frame"
        return None


def _unsupported_torso_form(pose):
    if len(pose) != 33:
        return False
    distal = [pose[index] for index in (13, 14, 15, 16, 25, 26, 27, 28)]
    return all(.02 < point.x < .98 and .02 < point.y < .98 and point.visibility is not None
               and point.visibility < .7 for point in distal)


def run_cancellable(command, *, capture_output=True, text=True, timeout=120, cancel=None):
    deadline = monotonic() + timeout
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text) as process:
        try:
            while True:
                if cancel is not None and cancel.is_set():
                    raise RuntimeError("Subject detection cancelled.")
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, timeout)
                try:
                    stdout, stderr = process.communicate(timeout=min(.1, remaining))
                    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
                except subprocess.TimeoutExpired:
                    continue
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()


class PoseLandmarker:
    """Run native inference in a disposable process before publishing evidence."""

    def __init__(self, model_path: Path, *, segmentation: bool = False):
        if sha256(model_path.read_bytes()).hexdigest() != MODEL_SHA256:
            raise ValueError("pose_model_digest_mismatch")
        self._model_path = model_path.resolve()
        self._segmentation = segmentation
        self.cancel_event = Event()

    def detect(self, original_path: Path, photo_digest: str) -> SubjectEvidence:
        from .observations import ObservationRef, ObservationStore

        with TemporaryDirectory(prefix="human3d-vision-") as directory:
            command = [sys.executable, "-m", "human3d.vision_worker", str(self._model_path),
                       str(original_path.resolve()), photo_digest, directory]
            if self._segmentation:
                command.append("--segmentation")
            try:
                result = run_cancellable(command, capture_output=True, text=True, timeout=120, cancel=self.cancel_event)
            except subprocess.TimeoutExpired as error:
                raise RuntimeError("Subject detection timed out. Retry this photo.") from error
            except OSError as error:
                raise RuntimeError("Subject detector could not start. Retry this photo.") from error
            if result.returncode:
                if result.stdout.strip() == "photo_digest_mismatch":
                    raise ValueError("photo_digest_mismatch")
                raise RuntimeError(f"Subject detector failed (exit {result.returncode}). Retry this photo.")
            try:
                return ObservationStore(Path(directory)).read_detection(
                    ObservationRef("", photo_digest, result.stdout.strip())
                )
            except (OSError, ValueError, KeyError, TypeError) as error:
                raise RuntimeError("Subject detector returned invalid evidence. Retry this photo.") from error

    def close(self):
        self.cancel_event.set()


class _NativePoseLandmarker:
    """Use the explicitly provisioned MediaPipe Lite v1 model on CPU."""

    def __init__(self, model_path: Path, *, segmentation: bool = False):
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
            output_segmentation_masks=segmentation,
        )
        self._segmentation = segmentation
        self._detector = tasks.vision.PoseLandmarker.create_from_options(options)

    def detect(self, original_path: Path, photo_digest: str) -> SubjectEvidence:
        with original_path.open("rb") as source:
            if sha256(source.read()).hexdigest() != photo_digest:
                raise ValueError("photo_digest_mismatch")
            source.seek(0)
            with Image.open(source) as photo:
                image = ImageOps.exif_transpose(photo).convert("RGB")
        original_size = image.size
        inference, content_size = _inference_image(image)
        x_scale = inference.width / content_size[0]
        result = self._detector.detect(self._image(image_format=self._format, data=self._array(inference)))
        candidates = tuple(
            tuple(Landmark(point.x * x_scale, point.y, point.visibility, point.presence) for point in pose)
            for pose in result.pose_landmarks
        )
        masks = ()
        if self._segmentation:
            raw_masks = result.segmentation_masks or ()
            if len(raw_masks) != len(candidates):
                masks = (None,) * len(candidates)
            else:
                masks = tuple(
                    self._mask_png(mask.numpy_view(), inference.size, content_size, original_size)
                    if mask.is_contiguous() else None
                    for mask in raw_masks
                )
        world = tuple(tuple((point.x, point.y, point.z) for point in pose)
                      for pose in result.pose_world_landmarks)
        if self._segmentation:
            # An in-frame torso with no reliable distal evidence is typical of
            # torso forms. Retain cropped candidates and surviving alternatives.
            retained = tuple(index for index, pose in enumerate(candidates)
                             if not _unsupported_torso_form(pose))
            candidates = tuple(candidates[index] for index in retained)
            masks = tuple(masks[index] for index in retained)
            world = tuple(world[index] for index in retained) if len(world) == len(result.pose_landmarks) else ()
        return SubjectEvidence(photo_digest, MODEL_SHA256, original_size, candidates, masks, world)

    @staticmethod
    def _mask_png(probabilities, image_size: tuple[int, int], content_size=None, original_size=None) -> bytes | None:
        import numpy as np

        if probabilities.shape == (*image_size[::-1], 1):
            probabilities = probabilities[:, :, 0]
        if probabilities.shape != image_size[::-1]:
            return None
        width, height = content_size or image_size
        if not (0 < width <= image_size[0] and 0 < height <= image_size[1]):
            return None
        probabilities = probabilities[:height, :width]
        if not np.isfinite(probabilities).all() or probabilities.min() < 0 or probabilities.max() > 1:
            return None
        if original_size is not None and original_size != (width, height):
            probabilities = np.asarray(
                Image.fromarray(probabilities).resize(original_size, Image.Resampling.BILINEAR)
            )
        foreground = probabilities >= 0.5
        if not foreground.any() or foreground.all():
            return None
        buffer = BytesIO()
        Image.fromarray(foreground.astype("uint8") * 255).save(buffer, format="PNG")
        return buffer.getvalue()

    def close(self):
        self._detector.close()
