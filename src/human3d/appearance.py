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
    hair_candidate: np.ndarray | None = None
    hidden_regions: frozenset[str] = frozenset()


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
    hair = np.zeros_like(foreground)
    if skin.any() and pose[2].observed and pose[5].observed:
        eye_x = (pose[2].x + pose[5].x) * photo.width / 2
        eye_y = (pose[2].y + pose[5].y) * photo.height / 2
        eye_span = abs(pose[2].x - pose[5].x) * photo.width
        y, x = np.ogrid[:photo.height, :photo.width]
        scalp = (abs(x - eye_x) <= 1.25 * eye_span) & (y <= eye_y) & (y >= eye_y - 2 * eye_span)
        skin_light = np.median(rgb[skin].mean(axis=1))
        hair = foreground & ~skin & scalp & (rgb.mean(axis=2) < .70 * skin_light)
    external = view.detection.anatomical
    hidden = frozenset(item.region for item in external.regions if not item.visible and item.confidence >= .8
                       and external.candidate == view.candidate) if external else frozenset()
    return AppearanceView(rgb, foreground, skin, alignment, hair, hidden)
