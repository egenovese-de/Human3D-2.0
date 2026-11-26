"""Validated image ingestion; no GUI dependencies."""
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil

from PIL import Image, UnidentifiedImageError
from .project_store import ProjectStore

FORMATS = {"JPEG", "PNG", "WEBP", "TIFF", "BMP"}
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}


@dataclass(frozen=True)
class ImportResult:
    name: str
    status: str
    reason: str = ""


def import_photos(store: ProjectStore, paths: list[Path]) -> tuple[ImportResult, ...]:
    results = []
    for path in map(Path, paths):
        if path.suffix.lower() not in EXTENSIONS:
            results.append(ImportResult(path.name, "rejected", "unsupported_format"))
            continue
        try:
            with TemporaryDirectory() as temp:
                staged = Path(temp) / path.name
                shutil.copyfile(path, staged)
                with Image.open(staged) as image:
                    if image.format not in FORMATS:
                        results.append(ImportResult(path.name, "rejected", "unsupported_format"))
                        continue
                    image.verify()
                with Image.open(staged) as image:
                    image.load()
                _, added = store.import_original(staged)
                results.append(ImportResult(path.name, "accepted" if added else "duplicate"))
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
            results.append(ImportResult(path.name, "rejected", "invalid_or_unreadable"))
    return tuple(results)


def folder_inputs(directory: Path) -> list[Path]:
    return sorted((p for p in Path(directory).iterdir() if p.is_file()),
                  key=lambda p: (p.name.casefold(), p.name))
