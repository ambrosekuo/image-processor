"""
Spritesheet analysis and processing utilities.
"""

import io
import logging
import math
from pathlib import Path

from PIL import Image

from .api_utils import find_divisors

logger = logging.getLogger(__name__)


def save_rgba_png(image: Image.Image, target: Path | str | io.BytesIO) -> None:
    """Save an image as a PNG with a preserved alpha channel."""
    image.convert("RGBA").save(target, format="PNG")


def image_has_transparency(image: Image.Image, alpha_threshold: int = 250) -> bool:
    """Return True if the image contains any non-opaque pixels."""
    rgba = image.convert("RGBA")
    return any(pixel[3] < alpha_threshold for pixel in rgba.getdata())


def analyze_spritesheet_dimensions(spritesheet: Image.Image) -> dict[str, any]:
    """
    Analyze spritesheet dimensions and suggest grid layouts.

    Args:
        spritesheet: PIL Image of spritesheet

    Returns:
        Dictionary with analysis results
    """
    width, height = spritesheet.size
    width_divisors = find_divisors(width)
    height_divisors = find_divisors(height)
    suggestions = []
    for w in width_divisors[:5]:
        for h in height_divisors[:5]:
            if w * h <= 50:
                frame_width = width // w
                frame_height = height // h
                suggestions.append(
                    {
                        "grid": f"{w}x{h}",
                        "frame_size": f"{frame_width}x{frame_height}",
                        "total_frames": w * h,
                    }
                )
    suggestions.sort(key=lambda x: x["total_frames"])
    return {
        "spritesheet_size": f"{width}x{height}",
        "suggested_layouts": suggestions[:10],
        "width_divisors": width_divisors,
        "height_divisors": height_divisors,
    }


def validate_spritesheet_grid(
    spritesheet: Image.Image,
    cols: int,
    rows: int,
    frame_width: int | None = None,
    frame_height: int | None = None,
) -> tuple[int, int]:
    """
    Validate spritesheet can fit the requested grid and return frame dimensions.

    Args:
        spritesheet: PIL Image of spritesheet
        cols: Requested columns
        rows: Requested rows
        frame_width: Override frame width
        frame_height: Override frame height

    Returns:
        Tuple of (frame_width, frame_height)

    Raises:
        HTTPException: If grid doesn't fit
    """
    sw, sh = spritesheet.size
    if frame_width and frame_height:
        fw, fh = (int(frame_width), int(frame_height))
        if fw <= 0 or fh <= 0:
            raise ValueError("frameWidth and frameHeight must be > 0")
    else:
        fw = sw // cols
        fh = sh // rows
    frames_per_row = sw // fw
    frames_per_col = sh // fh
    if frames_per_row < cols:
        raise ValueError(
            f"Spritesheet width ({sw}) cannot fit {cols} frames of width {fw}. "
            f"Maximum frames per row: {frames_per_row}"
        )
    if frames_per_col < rows:
        raise ValueError(
            f"Spritesheet height ({sh}) cannot fit {rows} frames of height {fh}. "
            f"Maximum frames per column: {frames_per_col}"
        )
    return (fw, fh)


def process_spritesheet_frames(
    spritesheet: Image.Image,
    cols: int,
    rows: int,
    frame_width: int | None = None,
    frame_height: int | None = None,
    max_frames: int | None = None,
) -> list[Image.Image]:
    """
    Process spritesheet by extracting and validating frames.

    Args:
        spritesheet: PIL Image of spritesheet
        cols: Number of columns
        rows: Number of rows
        frame_width: Override frame width
        frame_height: Override frame height
        max_frames: Maximum frames to process

    Returns:
        List of extracted frame images
    """
    from .api_utils import extract_spritesheet_frames

    fw, fh = validate_spritesheet_grid(spritesheet, cols, rows, frame_width, frame_height)
    frames = extract_spritesheet_frames(spritesheet, cols, rows, fw, fh, max_frames)
    return frames


def create_spritesheet_from_frames(
    frames: list[Image.Image],
    cols: int,
    rows: int,
    frame_width: int | None = None,
    frame_height: int | None = None,
) -> Image.Image:
    """
    Create spritesheet from processed frames.

    Args:
        frames: List of processed frame images
        cols: Number of columns
        rows: Number of rows
        frame_width: Override frame width
        frame_height: Override frame height

    Returns:
        Combined spritesheet image
    """
    from .api_utils import create_spritesheet

    return create_spritesheet(frames, cols, rows, frame_width, frame_height)


def calculate_optimal_frame_size(
    spritesheet: Image.Image, target_frames: int
) -> tuple[int, int, int, int]:
    """
    Calculate optimal frame size and grid for target number of frames.

    Args:
        spritesheet: PIL Image of spritesheet
        target_frames: Desired number of frames

    Returns:
        Tuple of (frame_width, frame_height, cols, rows)
    """
    sw, sh = spritesheet.size
    cols = int(math.ceil(math.sqrt(target_frames)))
    rows = int(math.ceil(target_frames / cols))
    fw = sw // cols
    fh = sh // rows
    return (fw, fh, cols, rows)


def resize_frames_to_size(
    frames: list[Image.Image], target_width: int, target_height: int
) -> list[Image.Image]:
    """
    Resize all frames to target dimensions.

    Args:
        frames: List of frame images
        target_width: Target width
        target_height: Target height

    Returns:
        List of resized frame images
    """
    resized_frames = []
    for frame in frames:
        resized = frame.resize((target_width, target_height), Image.Resampling.LANCZOS)
        resized_frames.append(resized)
    return resized_frames
