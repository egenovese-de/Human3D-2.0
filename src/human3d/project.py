"""Immutable project state; persistence and ingestion are separate boundaries."""
from dataclasses import dataclass, replace
from uuid import UUID, uuid4
import re


@dataclass(frozen=True)
class Photo:
    id: str
    digest: str
    name: str
    included: bool = True

    def __post_init__(self):
        UUID(self.id)
        if not re.fullmatch(r"[0-9a-f]{64}", self.digest):
            raise ValueError("invalid photo digest")
        if not self.name or type(self.included) is not bool:
            raise ValueError("invalid photo metadata")


@dataclass(frozen=True)
class PhotoSet:
    photos: tuple[Photo, ...] = ()
    target: str | None = None

    def __post_init__(self):
        if len({p.id for p in self.photos}) != len(self.photos):
            raise ValueError("duplicate photo id")
        if len({p.digest for p in self.photos}) != len(self.photos):
            raise ValueError("duplicate photo content")
        included = {p.id for p in self.photos if p.included}
        if self.photos and self.target not in included:
            raise ValueError("target must reference included photo")
        if not self.photos and self.target is not None:
            raise ValueError("empty photo set cannot have target")

    def add(self, digest: str, name: str) -> "PhotoSet":
        if any(p.digest == digest for p in self.photos):
            return self
        photo = Photo(str(uuid4()), digest, name)
        return PhotoSet(self.photos + (photo,), self.target or photo.id)

    def select(self, photo_id: str) -> "PhotoSet":
        return replace(self, target=photo_id)

    def include(self, photo_id: str, included: bool) -> "PhotoSet":
        if not any(p.id == photo_id for p in self.photos):
            raise ValueError("unknown photo")
        photos = tuple(replace(p, included=included) if p.id == photo_id else p
                       for p in self.photos)
        return PhotoSet(photos, self.target)


@dataclass(frozen=True)
class Project:
    id: str
    revision: int = 0
    photos: PhotoSet = PhotoSet()

    def __post_init__(self):
        UUID(self.id)
        if type(self.revision) is not int or self.revision < 0:
            raise ValueError("invalid revision")

    @classmethod
    def new(cls) -> "Project":
        return cls(str(uuid4()))

    def with_photos(self, photos: PhotoSet) -> "Project":
        return replace(self, photos=photos)
