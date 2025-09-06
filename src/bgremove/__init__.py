__all__ = ["remove_bytes", "remove_file"]

from rembg import remove


def remove_bytes(data: bytes) -> bytes:
    """Remove background from raw image bytes and return PNG bytes with alpha."""
    return remove(data)


def remove_file(in_path: str) -> bytes:
    """Remove background from an image path and return PNG bytes with alpha."""
    with open(in_path, "rb") as f:
        data = f.read()
    return remove_bytes(data)
