"""Single-writer project persistence with atomic snapshot replacement."""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from dataclasses import asdict, replace
from threading import RLock
from contextlib import contextmanager

from .project import Photo, PhotoSet, Project
from .observations import ObservationRef
from .originals import OriginalStore

_LOCK = RLock()


@contextmanager
def writer_lock(directory: Path):
    """Serialize writers across processes on local Windows/POSIX filesystems."""
    directory.mkdir(parents=True, exist_ok=True)
    with _LOCK, (directory / ".writer.lock").open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def sync_directory(directory: Path):
    """Persist directory entries on POSIX; Windows has no portable directory fsync."""
    if os.name != "nt":
        fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


class RevisionConflict(RuntimeError):
    pass


class ProjectStore:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.snapshot = self.directory / "project.json"

    def load(self) -> Project:
        data = json.loads(self.snapshot.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("invalid project snapshot")
        if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
            raise ValueError("unsupported project schema")
        return Project(data["id"], data["revision"], PhotoSet(
            tuple(Photo(**p) for p in data["photos"]), data["target"]), data.get("frozen_body_digest"),
            tuple(ObservationRef(**ref) for ref in data.get("observations", ())),
            data.get("shared_fit_digest"), tuple(data.get("shared_fit_history", ())))

    def recover_interrupted_writes(self) -> Project:
        """Discard only abandoned snapshot staging files under the writer lock."""
        with writer_lock(self.directory):
            project = self.load()
            for path in self.directory.glob(".project-write-*"):
                if path.is_file() and not path.is_symlink():
                    path.unlink()
            return project

    def create(self) -> Project:
        with writer_lock(self.directory):
            self.directory.mkdir(parents=True, exist_ok=True)
            if self.snapshot.exists():
                raise FileExistsError(self.snapshot)
            project = Project.new()
            self._write(project)
            return project

    def save(self, project: Project) -> Project:
        with writer_lock(self.directory):
            current = self.load()
            if current.id != project.id or current.revision != project.revision:
                raise RevisionConflict("project identity or revision changed")
            updated = replace(project, revision=project.revision + 1)
            self._write(updated)
            return updated

    def import_original(self, source: Path) -> tuple[Project, bool]:
        """Import exact bytes; image decoding and format validation belong to ingestion."""
        with writer_lock(self.directory):
            project = self.load()
            digest = OriginalStore(self.directory).put(source)
            photos = project.photos.add(digest, Path(source).name)
            if photos == project.photos:
                return project, False
            updated = replace(project, photos=photos, revision=project.revision + 1)
            self._write(updated)
            return updated, True

    def _write(self, project: Project) -> None:
        data = {
            "schema_version": 1, "id": project.id,
            "revision": project.revision, "target": project.photos.target,
            "frozen_body_digest": project.frozen_body_digest,
            "shared_fit_digest": project.shared_fit_digest,
            "shared_fit_history": project.shared_fit_history,
            "observations": [asdict(ref) for ref in project.observations],
            "photos": [{"id": p.id, "digest": p.digest, "name": p.name,
                        "included": p.included} for p in project.photos.photos],
        }
        temp = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8",
                                    dir=self.directory, prefix=".project-write-", delete=False) as handle:
                temp = Path(handle.name)
                json.dump(data, handle, sort_keys=True, allow_nan=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.snapshot)
            sync_directory(self.directory)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
