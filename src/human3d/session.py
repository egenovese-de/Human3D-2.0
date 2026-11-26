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

    def _sync(self, project, *, retain_kind=None):
        dependencies = {f"photo:{p.id}": p.digest for p in project.photos.photos if p.included}
        included = {p.id for p in project.photos.photos if p.included}
        for ref in project.observations:
            if ref.photo_id in included:
                dependencies[f"detection:{ref.photo_id}"] = ref.detection
                if ref.correction:
                    dependencies[f"correction:{ref.photo_id}"] = ref.correction
        if project.shared_fit_digest:
            dependencies["shared_fit"] = project.shared_fit_digest
        if project.frozen_body_digest:
            dependencies["frozen_body"] = project.frozen_body_digest
        if project.photos.target:
            dependencies["target"] = project.photos.target
        self.coordinator.invalidate(dependencies, retain_kind=retain_kind)

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

    def include_reference(self, photo_id: str, included: bool):
        with self._lock:
            project = self.store.load()
            if photo_id == project.photos.target and not included:
                raise ValueError("Select another target before excluding this photo.")
            updated = project.with_photos(project.photos.include(photo_id, included))
            if updated != project:
                updated = self.store.save(updated)
            self._sync(updated)
            return updated

    def shared_evidence(self):
        from .fusion import fuse_observations

        with self._lock:
            return fuse_observations(self.store.load(), self.observations)

    def fit_shared(self):
        from .fitting import fit_shared
        from .frozen_body import load_frozen_body
        from .fusion import fuse_observations

        with self._lock:
            project = self.store.load()
            bootstrap = project.frozen_body_digest
            if bootstrap is None:
                raise ValueError("project_has_no_frozen_body")
            evidence = fuse_observations(project, self.observations)
            previous = project.shared_fit_digest
        body = load_frozen_body(self.store.directory / "frozen" / f"{bootstrap}.json")
        result = fit_shared(body, evidence)
        with self._lock:
            current = self.store.load()
            if (current.frozen_body_digest != bootstrap or current.shared_fit_digest != previous
                    or fuse_observations(current, self.observations).dependency_digest != evidence.dependency_digest):
                raise ValueError("shared_fit_dependencies_changed")
            digest = self.observations.write_fit(bootstrap, result)
            if digest != previous:
                self._sync(self.store.save(current.with_shared_fit(digest)))
        return result

    def current_shared_fit(self):
        from .fusion import fuse_observations

        with self._lock:
            project = self.store.load()
            if project.shared_fit_digest is None:
                return None
            bootstrap, fit = self.observations.read_fit(project.shared_fit_digest)
            if (bootstrap != project.frozen_body_digest
                    or fit.evidence_digest != fuse_observations(project, self.observations).dependency_digest):
                return None
            return fit

    def restorable_fits(self):
        with self._lock:
            project = self.store.load()
            evidence = self.shared_evidence()
            revisions = []
            for digest in project.shared_fit_history:
                if digest == project.shared_fit_digest:
                    continue
                bootstrap, fit = self.observations.read_fit(digest)
                if bootstrap == project.frozen_body_digest and fit.evidence_digest == evidence.dependency_digest:
                    revisions.append(digest)
            return tuple(revisions)

    def restore_shared_fit(self, digest: str):
        with self._lock:
            project = self.store.load()
            if digest not in self.restorable_fits():
                raise ValueError("shared_fit_revision_unavailable")
            self._sync(self.store.save(project.with_shared_fit(digest)))

    def edit_shared_control(self, name: str, value: float):
        from .fitting import edit_fit
        from .frozen_body import load_frozen_body

        with self._lock:
            project = self.store.load()
            fit = self.current_shared_fit()
            if fit is None:
                raise ValueError("no_current_shared_fit")
            bootstrap = project.frozen_body_digest
            body = load_frozen_body(self.store.directory / "frozen" / f"{bootstrap}.json")
            revised = edit_fit(body, self.shared_evidence(), fit, name, value)
            digest = self.observations.write_fit(bootstrap, revised)
            if digest != project.shared_fit_digest:
                self._sync(self.store.save(project.with_shared_fit(digest)))
            return revised

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
                if promoted:
                    self._sync(self.store.load(), retain_kind=kind)
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
            self._sync(self.store.load(), retain_kind="subject_mask")
            return mask
