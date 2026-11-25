"""Typed, photo-bound orientation and visibility evidence from external providers."""
from dataclasses import dataclass, replace
from math import isfinite
from pathlib import Path
from typing import Protocol

REGION_LANDMARKS = {
    "face": tuple(range(11)),
    "torso": (11, 12, 23, 24),
    "left_arm": (13, 15, 17, 19, 21),
    "right_arm": (14, 16, 18, 20, 22),
    "left_leg": (25, 27, 29, 31),
    "right_leg": (26, 28, 30, 32),
}


@dataclass(frozen=True)
class RegionVisibility:
    region: str
    visible: bool
    confidence: float

    def __post_init__(self):
        if self.region not in REGION_LANDMARKS or type(self.visible) is not bool:
            raise ValueError("invalid_region_visibility")
        if not isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("invalid_region_confidence")


@dataclass(frozen=True)
class AnatomicalEvidence:
    photo_digest: str
    provider: str
    model: str
    candidate: int
    regions: tuple[RegionVisibility, ...] = ()
    yaw: float | None = None
    yaw_confidence: float = 0.0
    schema_version: int = 1

    def __post_init__(self):
        if self.schema_version != 1 or not self.provider.strip() or not self.model.strip():
            raise ValueError("invalid_anatomical_evidence_provenance")
        if type(self.candidate) is not int or self.candidate < 0:
            raise ValueError("invalid_anatomical_evidence_candidate")
        if len({item.region for item in self.regions}) != len(self.regions):
            raise ValueError("duplicate_anatomical_region")
        if self.yaw is not None and (not isfinite(self.yaw) or not -180 <= self.yaw <= 180):
            raise ValueError("invalid_provider_yaw")
        if not isfinite(self.yaw_confidence) or not 0 <= self.yaw_confidence <= 1:
            raise ValueError("invalid_provider_yaw_confidence")
        if self.yaw is None and self.yaw_confidence:
            raise ValueError("provider_yaw_confidence_without_yaw")

    @classmethod
    def from_record(cls, value: dict):
        return cls(**(value | {"regions": tuple(RegionVisibility(**item) for item in value.get("regions", ()))}))


class EvidenceProvider(Protocol):
    def observe(self, photo: Path, photo_digest: str, candidate: int) -> AnatomicalEvidence | None: ...


class EvidenceAdapter:
    """Attach typed external evidence without replacing detector measurements."""

    def __init__(self, detector, provider: EvidenceProvider):
        self._detector = detector
        self._provider = provider

    def detect(self, original_path: Path, photo_digest: str):
        detection = self._detector.detect(original_path, photo_digest)
        if len(detection.candidates) != 1:
            return detection
        evidence = self._provider.observe(original_path, photo_digest, 0)
        if evidence is None:
            return detection
        if evidence.photo_digest != photo_digest or evidence.candidate != 0:
            raise ValueError("provider_evidence_binding_mismatch")
        return replace(detection, anatomical=evidence)

    def close(self):
        self._detector.close()


def apply_visibility(pose, evidence: AnatomicalEvidence | None):
    if evidence is None:
        return pose
    hidden = {i for item in evidence.regions if not item.visible and item.confidence >= .8
              for i in REGION_LANDMARKS[item.region]}
    return tuple(replace(point, visibility=0.0) if i in hidden else point
                 for i, point in enumerate(pose))


def yaw_conflicts(external: AnatomicalEvidence, detector_yaw: float | None):
    return (
        detector_yaw is not None and external.yaw is not None and external.yaw_confidence >= .8
        and abs((external.yaw - detector_yaw + 180) % 360 - 180) > 45
    )
