"""Application session boundary for project commands and capability snapshots."""
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from .project import Project
from .project_store import ProjectStore
from .orchestration import Coordinator, Job
from .ingestion import import_photos
from .originals import OriginalStore
from .vision import SubjectEvidence
from .mask_review import MaskDraft, SubjectMask


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

    def detect_target(self, detector) -> SubjectEvidence | None:
        """Run detection on the caller's worker and promote only current evidence."""
        with self._lock:
            project = self.store.load()
            self._sync(project)
            if project.photos.target is None:
                raise ValueError("no_target_photo")
            photo = next(photo for photo in project.photos.photos if photo.id == project.photos.target)
            job = self.coordinator.submit("subject_evidence")
            self.coordinator.start(job.id)
        try:
            original = OriginalStore(self.store.directory).path(photo.digest)
            evidence = detector.detect(original, photo.digest)
            with self._lock:
                self._sync(self.store.load())
                promoted = self.coordinator.finish(
                    job.id, evidence,
                    lambda result: isinstance(result, SubjectEvidence) and result.photo_digest == photo.digest,
                )
        except Exception:
            self.coordinator.fail(job.id, "subject_detection_failed")
            raise
        return evidence if promoted else None

    def apply_mask(self, draft: MaskDraft) -> SubjectMask:
        mask = draft.validate()
        with self._lock:
            self._sync(self.store.load())
            generation, _, artifacts = self.coordinator.snapshot_with_generation()
            current = artifacts.get("subject_evidence")
            if current is None or current[0] != generation or current[1] is not draft.evidence:
                raise ValueError("subject_evidence_changed")
            job = self.coordinator.submit("subject_mask")
            self.coordinator.start(job.id)
            if not self.coordinator.finish(job.id, mask, lambda result: result == mask):
                raise ValueError("mask_promotion_rejected")
            return mask
