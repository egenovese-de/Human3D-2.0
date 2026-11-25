"""Content-addressed photo observations. Project snapshots bind active revisions."""
import base64
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile

from .mask_review import SubjectMask
from .vision import Landmark, SubjectEvidence


@dataclass(frozen=True)
class ObservationRef:
    photo_id: str
    photo_digest: str
    detection: str
    correction: str | None = None


class ObservationStore:
    def __init__(self, project_directory: Path):
        self.directory = project_directory / "observations"

    def _path(self, digest: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("invalid_observation_digest")
        return self.directory / (digest + ".json")

    def _write(self, kind: str, payload: dict) -> str:
        data = json.dumps({"schema_version": 1, "kind": kind, "payload": payload},
                          sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        digest = sha256(data).hexdigest()
        destination = self._path(digest)
        self.directory.mkdir(parents=True, exist_ok=True)
        temp = None
        try:
            with NamedTemporaryFile(dir=self.directory, delete=False) as handle:
                temp = Path(handle.name)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temp, destination)
            except FileExistsError:
                if destination.read_bytes() != data:
                    raise ValueError("observation_integrity_mismatch")
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
        return digest

    def _read(self, digest: str, kind: str) -> dict:
        data = self._path(digest).read_bytes()
        if sha256(data).hexdigest() != digest:
            raise ValueError("observation_integrity_mismatch")
        document = json.loads(data)
        if document["schema_version"] != 1 or document["kind"] != kind:
            raise ValueError("unsupported_observation_artifact")
        return document["payload"]

    def write_detection(self, value: SubjectEvidence) -> str:
        payload = asdict(value)
        payload["masks"] = [_encode(mask) if mask is not None else None for mask in value.masks]
        return self._write("subject_detection", payload)

    def read_detection(self, ref: ObservationRef) -> SubjectEvidence:
        payload = self._read(ref.detection, "subject_detection")
        if payload["photo_digest"] != ref.photo_digest:
            raise ValueError("observation_photo_mismatch")
        return SubjectEvidence(
            ref.photo_digest, payload["model_digest"], tuple(payload["image_size"]),
            tuple(tuple(Landmark(**point) for point in pose) for pose in payload["candidates"]),
            tuple(_decode(mask) if mask is not None else None for mask in payload["masks"]),
            tuple(tuple(tuple(point) for point in pose) for pose in payload.get("world_landmarks", ())),
        )

    def write_correction(self, value: SubjectMask, ref: ObservationRef) -> str:
        if value.photo_digest != ref.photo_digest:
            raise ValueError("observation_photo_mismatch")
        return self._write("subject_mask", {"photo_digest": value.photo_digest,
                          "detection": ref.detection, "candidate": value.candidate,
                          "png": _encode(value.png)})

    def read_correction(self, ref: ObservationRef) -> SubjectMask | None:
        if ref.correction is None:
            return None
        payload = self._read(ref.correction, "subject_mask")
        if payload["photo_digest"] != ref.photo_digest or payload["detection"] != ref.detection:
            raise ValueError("observation_dependency_mismatch")
        return SubjectMask(ref.photo_digest, payload["candidate"], _decode(payload["png"]))

    def write_fit(self, bootstrap: str, value) -> str:
        payload = {"bootstrap": bootstrap, "evidence_digest": value.evidence_digest,
                   "fit": asdict(value.fit), "scores": value.scores, "alignments": {}}
        for key, alignment in value.alignments.items():
            camera = alignment.camera
            payload["alignments"][key] = {
                "yaw": camera.yaw_degrees, "similarity": [camera.similarity.real, camera.similarity.imag],
                "origin": [camera.origin.real, camera.origin.imag],
                "torso_rms_pixels": alignment.torso_rms_pixels, "limb_angles": alignment.limb_angles,
                "limb_depth_ratios": alignment.limb_depth_ratios,
            }
        return self._write("shared_fit", payload)

    def read_fit(self, digest: str):
        from .alignment import Alignment, Camera
        from .fitting import Fit, SharedFit

        payload = self._read(digest, "shared_fit")
        alignments = {
            key: Alignment(Camera(value["yaw"], complex(*value["similarity"]), complex(*value["origin"])),
                           value["torso_rms_pixels"], value["limb_angles"], value.get("limb_depth_ratios", {}))
            for key, value in payload["alignments"].items()
        }
        return payload["bootstrap"], SharedFit(Fit(**payload["fit"]), alignments,
                                                payload["evidence_digest"], payload["scores"])


def _encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _decode(value: str) -> bytes:
    return base64.b64decode(value, validate=True)
