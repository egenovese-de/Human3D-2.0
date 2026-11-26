"""Project-owned originals, addressed by SHA-256 of exact source bytes."""
import hashlib
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile


class OriginalStore:
    def __init__(self, project_directory: Path):
        self.directory = Path(project_directory) / "originals"

    def path(self, digest: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("invalid digest")
        return self.directory / digest

    def put(self, source: Path) -> str:
        self.directory.mkdir(parents=True, exist_ok=True)
        temp = None
        digest = hashlib.sha256()
        try:
            with Path(source).open("rb") as src, NamedTemporaryFile(
                dir=self.directory, delete=False
            ) as dst:
                temp = Path(dst.name)
                while chunk := src.read(1024 * 1024):
                    digest.update(chunk)
                    dst.write(chunk)
                dst.flush()
                os.fsync(dst.fileno())
            identity = digest.hexdigest()
            target = self.path(identity)
            try:
                os.link(temp, target)
            except FileExistsError:
                self.verify(identity)
            return identity
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)

    def verify(self, digest: str) -> Path:
        target = self.path(digest)
        with target.open("rb") as handle:
            actual = hashlib.file_digest(handle, "sha256").hexdigest()
        if actual != digest:
            raise ValueError("original integrity mismatch")
        return target
