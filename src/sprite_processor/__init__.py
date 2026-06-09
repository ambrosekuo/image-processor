__all__ = [
    "remove_bytes",
    "remove_file",
    "video_to_gif",
    "video_to_spritesheet",
    "analyze_video",
    "process_video_pipeline",
    "process_video_pipeline_all_models",
]
from rembg import new_session, remove

from .bria_processor import remove_background_bria


def remove_bytes(data: bytes, model_name: str = "isnet-general-use") -> bytes:
    """Remove background from raw image bytes and return PNG bytes with alpha.

    Args:
        data: Raw image bytes
        model_name: Model to use for background removal. Options:
            - 'isnet-general-use': Most advanced, best general purpose (recommended)
            - 'isnet-anime': Optimized for anime/manga characters, less aggressive
            - 'bria-rmbg-1.4': BRIA RMBG-1.4, high-quality, good for fine details
            - 'u2net_human_seg': Best for human/character sprites
            - 'u2net': Original model, can be aggressive
            - 'u2netp': Lighter version of u2net
            - 'u2net_cloth_seg': Good for clothing/character details
            - 'silueta': Good for silhouettes
    """
    if model_name == "bria-rmbg-1.4":
        return remove_background_bria(data)
    session = new_session(model_name)
    return remove(data, session=session)


def remove_file(in_path: str, model_name: str = "isnet-general-use") -> bytes:
    """Remove background from an image path and return PNG bytes with alpha."""
    with open(in_path, "rb") as f:
        data = f.read()
    return remove_bytes(data, model_name)


from .pipeline import (  # noqa: E402
    process_video_pipeline,
    process_video_pipeline_all_models,
)
from .video import analyze_video, video_to_gif, video_to_spritesheet  # noqa: E402
