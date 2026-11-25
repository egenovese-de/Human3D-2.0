"""Local appearance sampling from oriented photos and reviewed silhouettes."""
from dataclasses import dataclass
from io import BytesIO

import numpy as np
from PIL import Image, ImageOps

from .originals import OriginalStore


@dataclass(frozen=True)
class AppearanceView:
    rgb: np.ndarray
    foreground: np.ndarray
    skin_candidate: np.ndarray
    alignment: object


def prepare_view(originals: OriginalStore, view, alignment, *, limit=640):
    """Label conservative skin-color candidates using visible face samples."""
    path = originals.verify(view.ref.photo_digest)
    with Image.open(path) as source:
        photo = ImageOps.exif_transpose(source).convert("RGB")
    with Image.open(BytesIO(view.mask.png)) as source:
        mask = source.convert("L")
    if mask.size != photo.size or photo.size != view.detection.image_size:
        raise ValueError("appearance_image_coordinate_mismatch")
    photo.thumbnail((limit, limit), Image.Resampling.LANCZOS)
    rgb = np.asarray(photo)
    foreground = np.asarray(mask.resize(photo.size, Image.Resampling.NEAREST)) > 0
    max_channel = rgb.max(axis=2).astype(float)
    total = rgb.sum(axis=2)
    chroma = rgb / np.maximum(total[:, :, None], 1)
    samples = []
    pose = view.detection.visible_pose(view.candidate)
    if abs(alignment.camera.yaw_degrees) <= 30:
        for index in (0, 2, 5):
            landmark = pose[index]
            if not landmark.observed:
                continue
            x = min(photo.width - 1, int(landmark.x * photo.width))
            y = min(photo.height - 1, int(landmark.y * photo.height))
            if foreground[y, x]:
                samples.append(chroma[y, x])
    skin = np.zeros_like(foreground)
    if len(samples) >= 2:
        reference = np.median(samples, axis=0)
        if np.max(np.linalg.norm(np.asarray(samples) - reference, axis=1)) <= 0.11:
            skin = foreground & (max_channel >= 36) & (np.linalg.norm(chroma - reference, axis=2) < 0.07)
    return AppearanceView(rgb, foreground, skin, alignment)
