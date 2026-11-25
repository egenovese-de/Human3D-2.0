"""Application session boundary for project commands and capability snapshots."""
from dataclasses import dataclass
from pathlib import Path
from .project import Project
from .project_store import ProjectStore
from .orchestration import Coordinator, Job
from .ingestion import import_photos


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
        project = self.store.load()
        self._sync(project)
        generation, jobs, artifacts = self.coordinator.snapshot_with_generation()
        current = tuple(sorted(kind for kind, (revision, _) in artifacts.items() if revision == generation))
        stale = tuple(sorted(kind for kind, (revision, _) in artifacts.items() if revision != generation))
        return SessionSnapshot(project, jobs, Capability(True),
                               Capability(bool(project.photos.photos), "" if project.photos.photos else "no_photos"),
                               Capability(False, "engine_unavailable"), current, stale)

    def ingest(self, paths):
        results = import_photos(self.store, paths)
        self._sync(self.store.load())
        return results

    def select_target(self, photo_id):
        project = self.store.load()
        if project.photos.target != photo_id:
            project = self.store.save(project.with_photos(project.photos.select(photo_id)))
        self._sync(project)
        return project
