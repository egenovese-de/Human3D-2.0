"""Single-writer project persistence with atomic snapshot replacement."""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from dataclasses import replace
from threading import RLock

from .project import Photo, PhotoSet, Project

_LOCK = RLock()


class RevisionConflict(RuntimeError):
    pass


class ProjectStore:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.snapshot = self.directory / "project.json"

    def load(self) -> Project:
        data = json.loads(self.snapshot.read_text(encoding="utf-8"))
        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise ValueError("unsupported project schema")
        return Project(data["id"], data["revision"], PhotoSet(
            tuple(Photo(**p) for p in data["photos"]), data["target"]))

    def create(self) -> Project:
        with _LOCK:
            self.directory.mkdir(parents=True, exist_ok=True)
            if self.snapshot.exists():
                raise FileExistsError(self.snapshot)
            project = Project.new()
            self._write(project)
            return project

    def save(self, project: Project) -> Project:
        with _LOCK:
            current = self.load()
            if current.id != project.id or current.revision != project.revision:
                raise RevisionConflict("project identity or revision changed")
            updated = replace(project, revision=project.revision + 1)
            self._write(updated)
            return updated

    def _write(self, project: Project) -> None:
        data = {
            "schema_version": 1, "id": project.id,
            "revision": project.revision, "target": project.photos.target,
            "photos": [{"id": p.id, "digest": p.digest, "name": p.name,
                        "included": p.included} for p in project.photos.photos],
        }
        temp = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8",
                                    dir=self.directory, delete=False) as handle:
                temp = Path(handle.name)
                json.dump(data, handle, sort_keys=True, allow_nan=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.snapshot)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
