"""Application session boundary for project commands and capability snapshots."""
from dataclasses import dataclass, replace
from pathlib import Path
from threading import RLock
from .project import Project
from .project_store import ProjectStore
from .orchestration import Coordinator, Job
from .ingestion import import_photos
from .originals import OriginalStore
from .vision import SubjectEvidence
from .mask_review import MaskDraft, SubjectMask
from .observations import ObservationRef, ObservationStore


@dataclass(frozen=True)
class Capability:
    enabled: bool
    reason: str = ""


@dataclass(frozen=True)
class SessionSnapshot:
    project: Project
    jobs: tuple[Job, ...]
    import_photos: Capability
    select_target: Capability
    reconstruct: Capability
    current_artifacts: tuple[str, ...]
    stale_artifacts: tuple[str, ...]


class Session:
    def __init__(self, directory: Path, create=False):
        self._lock = RLock()
        self.store = ProjectStore(directory)
        self.observations = ObservationStore(self.store.directory)
        project = self.store.create() if create else self.store.load()
        self.coordinator = Coordinator(project.id)
        self._sync(project)

    def _sync(self, project):
        dependencies = {f"photo:{p.id}": p.digest for p in project.photos.photos if p.included}
        if project.photos.target:
            dependencies["target"] = project.photos.target
        self.coordinator.invalidate(dependencies)

    def snapshot(self):
        with self._lock:
            project = self.store.load()
            self._sync(project)
            generation, jobs, artifacts = self.coordinator.snapshot_with_generation()
            current = tuple(sorted(kind for kind, (revision, _) in artifacts.items() if revision == generation))
            stale = tuple(sorted(kind for kind, (revision, _) in artifacts.items() if revision != generation))
            return SessionSnapshot(project, jobs, Capability(True),
                                   Capability(bool(project.photos.photos), "" if project.photos.photos else "no_photos"),
                                   Capability(False, "engine_unavailable"), current, stale)

    def ingest(self, paths):
        with self._lock:
            results = import_photos(self.store, paths)
            self._sync(self.store.load())
            return results

    def select_target(self, photo_id):
        with self._lock:
            project = self.store.load()
            if project.photos.target != photo_id:
                project = self.store.save(project.with_photos(project.photos.select(photo_id)))
            self._sync(project)
            return project

    def read_observation(self, photo_id: str):
        with self._lock:
            ref = self.store.load().observation(photo_id)
            if ref is None:
                return None
            return self.observations.read_detection(ref), self.observations.read_correction(ref)

    def detect_target(self, detector) -> SubjectEvidence | None:
        return self._detect_photo(detector, None)

    def detect_photo(self, photo_id: str, detector) -> SubjectEvidence | None:
        return self._detect_photo(detector, photo_id)

    def _detect_photo(self, detector, photo_id):
        with self._lock:
            project = self.store.load()
            self._sync(project)
            selected = photo_id if photo_id is not None else project.photos.target
            photo = next((item for item in project.photos.photos if item.id == selected and item.included), None)
            if photo is None:
                raise ValueError("no_target_photo" if photo_id is None else "photo_unavailable")
            initial_ref = project.observation(photo.id)
            kind = "subject_evidence" if photo_id is None else f"subject_evidence:{photo.id}"
            job = self.coordinator.submit(kind)
            self.coordinator.start(job.id)
        try:
            original = OriginalStore(self.store.directory).path(photo.digest)
            evidence = detector.detect(original, photo.digest)
            with self._lock:
                current = self.store.load()
                self._sync(current)

                def publish():
                    digest = self.observations.write_detection(evidence)
                    if initial_ref is not None and initial_ref.detection == digest:
                        return
                    self.store.save(current.with_observation(ObservationRef(photo.id, photo.digest, digest)))

                promoted = self.coordinator.finish(
                    job.id, evidence,
                    lambda result: (
                        isinstance(result, SubjectEvidence) and result.photo_digest == photo.digest
                        and current.observation(photo.id) == initial_ref
                    ),
                    publish=publish,
                )
        except Exception:
            self.coordinator.fail(job.id, "subject_detection_failed")
            raise
        return evidence if promoted else None

    def apply_mask(self, draft: MaskDraft) -> SubjectMask:
        mask = draft.validate()
        with self._lock:
            project = self.store.load()
            self._sync(project)
            ref = project.observation(project.photos.target)
            if ref is None or self.observations.read_detection(ref) != draft.evidence:
                raise ValueError("subject_evidence_changed")

            def publish():
                digest = self.observations.write_correction(mask, ref)
                updated = project.with_observation(replace(ref, correction=digest))
                if updated != project:
                    self.store.save(updated)

            job = self.coordinator.submit("subject_mask")
            self.coordinator.start(job.id)
            if not self.coordinator.finish(job.id, mask, lambda result: result == mask, publish=publish):
                raise ValueError("mask_promotion_rejected")
            return mask
