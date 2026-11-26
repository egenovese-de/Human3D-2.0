"""Typed, photo-bound orientation and visibility evidence from external providers."""
from dataclasses import dataclass, replace
from math import isfinite
import logging
import re
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


MEASUREMENT_UNITS = {
    "proportion": ("ratio",),
    "circumference": ("m", "ratio"),
    "volume_proxy": ("ratio",),
    "morphology": ("ratio",),
    "asymmetry": ("m", "ratio"),
    "visibility": ("fraction",),
}
MEASUREMENT_FRAMES = ("photo", "canonical", "subject_local")


def _finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False


@dataclass(frozen=True)
class QuantitativeObservation:
    photo_digest: str
    candidate: int
    region: str
    kind: str
    definition: str
    frame: str
    units: str
    source_family: str
    value: float | None = None
    interval: tuple[float, float] | None = None
    uncertainty: float | None = None
    visibility: float | None = None
    calibration_ref: str | None = None

    def __post_init__(self):
        if (not isinstance(self.photo_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", self.photo_digest)
                or type(self.candidate) is not int or self.candidate < 0):
            raise ValueError("invalid_quantitative_binding")
        if (not isinstance(self.region, str) or self.region not in REGION_LANDMARKS
                or self.frame not in MEASUREMENT_FRAMES
                or not isinstance(self.definition, str)
                or not re.fullmatch(r"[a-z][a-z0-9_.-]*@v[1-9][0-9]*", self.definition)
                or not isinstance(self.source_family, str) or not self.source_family.strip()):
            raise ValueError("invalid_quantitative_semantics")
        if not isinstance(self.kind, str) or self.units not in MEASUREMENT_UNITS.get(self.kind, ()):
            raise ValueError("invalid_quantitative_units")
        if self.value is not None and self.interval is not None:
            raise ValueError("ambiguous_quantitative_value")
        if self.interval is not None and (not isinstance(self.interval, tuple) or len(self.interval) != 2):
            raise ValueError("invalid_quantitative_interval")
        values = self.interval if self.interval is not None else (self.value,) if self.value is not None else ()
        if not all(_finite_number(value) for value in values) or (len(values) == 2 and values[0] > values[1]):
            raise ValueError("invalid_quantitative_value")
        if self.kind == "visibility" and any(not 0 <= value <= 1 for value in values):
            raise ValueError("invalid_quantitative_visibility")
        if self.kind in {"proportion", "circumference", "volume_proxy"} and any(value <= 0 for value in values):
            raise ValueError("invalid_quantitative_range")
        if self.visibility is not None and (not _finite_number(self.visibility) or not 0 <= self.visibility <= 1):
            raise ValueError("invalid_quantitative_visibility")
        if self.uncertainty is not None and (not _finite_number(self.uncertainty) or self.uncertainty < 0):
            raise ValueError("invalid_quantitative_uncertainty")
        if self.calibration_ref is not None and (not isinstance(self.calibration_ref, str)
                                                 or not self.calibration_ref.strip()):
            raise ValueError("invalid_quantitative_calibration")
        if values and self.units == "m" and (self.calibration_ref is None or self.uncertainty is None
                                              or self.uncertainty <= 0 or self.frame == "photo"):
            raise ValueError("metric_evidence_requires_calibration")

    @classmethod
    def from_record(cls, record):
        interval = record.get("interval")
        if interval is not None and not isinstance(interval, (list, tuple)):
            raise ValueError("invalid_quantitative_interval")
        return cls(**(record | {"interval": tuple(interval) if interval is not None else None}))


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
    observations: tuple[QuantitativeObservation, ...] = ()

    def __post_init__(self):
        if (type(self.schema_version) is not int or self.schema_version not in (1, 2)
                or not isinstance(self.provider, str) or not self.provider.strip()
                or not isinstance(self.model, str) or not self.model.strip()):
            raise ValueError("invalid_anatomical_evidence_provenance")
        if type(self.candidate) is not int or self.candidate < 0:
            raise ValueError("invalid_anatomical_evidence_candidate")
        if (not isinstance(self.observations, tuple) or (self.schema_version == 1 and self.observations)
                or any(not isinstance(item, QuantitativeObservation) for item in self.observations)):
            raise ValueError("invalid_quantitative_observations")
        if any((item.photo_digest, item.candidate) != (self.photo_digest, self.candidate)
               for item in self.observations):
            raise ValueError("provider_evidence_binding_mismatch")
        if self.schema_version == 2 and (not isinstance(self.photo_digest, str)
                                         or not re.fullmatch(r"[0-9a-f]{64}", self.photo_digest)):
            raise ValueError("invalid_quantitative_binding")
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
        return cls(**(value | {
            "regions": tuple(RegionVisibility(**item) for item in value.get("regions", ())),
            "observations": tuple(QuantitativeObservation.from_record(item) for item in value.get("observations", ())),
        }))

    def as_v2(self):
        """Upgrade a legacy record in memory without changing stored observations."""
        return self if self.schema_version == 2 else replace(self, schema_version=2)


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
        try:
            evidence = self._provider.observe(original_path, photo_digest, 0)
            if evidence is None:
                return detection
            if not isinstance(evidence, AnatomicalEvidence) or evidence.photo_digest != photo_digest or evidence.candidate != 0:
                raise ValueError("provider_evidence_binding_mismatch")
        except Exception as error:
            logging.getLogger(__name__).warning("Optional anatomical provider unavailable (%s); using native evidence", type(error).__name__)
            return detection
        return replace(detection, anatomical=evidence)

    @property
    def cancel_event(self):
        return getattr(self._detector, "cancel_event", None)

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
