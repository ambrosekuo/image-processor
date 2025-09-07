__all__ = [
    "remove_bytes", 
    "remove_file",
    "video_to_gif",
    "video_to_spritesheet", 
    "analyze_video",
    "process_video_pipeline",
    "process_video_pipeline_all_models"
]

from rembg import remove, new_session


def remove_bytes(data: bytes, model_name: str = "isnet-general-use") -> bytes:
    """Remove background from raw image bytes and return PNG bytes with alpha.
    
    Args:
        data: Raw image bytes
        model_name: Model to use for background removal. Options:
            - 'isnet-general-use': Most advanced, best general purpose (recommended)
            - 'u2net_human_seg': Best for human/character sprites
            - 'u2net': Original model, can be aggressive
            - 'u2netp': Lighter version of u2net
            - 'u2net_cloth_seg': Good for clothing/character details
            - 'silueta': Good for silhouettes
    """
    session = new_session(model_name)
    return remove(data, session=session)


def remove_file(in_path: str, model_name: str = "isnet-general-use") -> bytes:
    """Remove background from an image path and return PNG bytes with alpha."""
    with open(in_path, "rb") as f:
        data = f.read()
    return remove_bytes(data, model_name)


# Import video and pipeline modules
from .video import video_to_gif, video_to_spritesheet, analyze_video
from .pipeline import process_video_pipeline, process_video_pipeline_all_models
