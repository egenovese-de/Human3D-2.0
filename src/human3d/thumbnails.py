"""Read-only thumbnail generation from project-owned originals."""
from io import BytesIO
from PIL import Image, ImageOps
from .originals import OriginalStore


def thumbnail(store: OriginalStore, digest: str, size: int = 160) -> bytes:
    if not 16 <= size <= 1024:
        raise ValueError("invalid thumbnail size")
    with Image.open(store.verify(digest)) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        output = BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()
