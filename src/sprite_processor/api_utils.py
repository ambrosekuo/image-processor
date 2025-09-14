"""
API utility functions for common operations.
"""
import base64
import logging
import math
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageSequence

logger = logging.getLogger(__name__)

# Available models for processing
AVAILABLE_MODELS = [
    "isnet-general-use",
    "u2net_human_seg", 
    "u2net",
    "u2netp",
    "u2net_cloth_seg",
    "silueta",
]


class TempFileManager:
    """Context manager for handling temporary files with automatic cleanup."""
    
    def __init__(self, suffix: str = ".tmp", delete: bool = True):
        self.suffix = suffix
        self.delete = delete
        self.temp_file_path: Optional[Path] = None
    
    def __enter__(self) -> Path:
        self.temp_file = tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=self.suffix
        )
        self.temp_file_path = Path(self.temp_file.name)
        return self.temp_file_path
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_file:
            self.temp_file.close()
        if self.delete and self.temp_file_path and self.temp_file_path.exists():
            try:
                self.temp_file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {self.temp_file_path}: {e}")


async def save_uploaded_file(
    file: UploadFile, 
    suffix: Optional[str] = None
) -> Path:
    """
    Save uploaded file to temporary location and return path.
    
    Args:
        file: Uploaded file
        suffix: File suffix (defaults to file extension)
        
    Returns:
        Path to temporary file
        
    Raises:
        HTTPException: If file is empty or save fails
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    
    # Determine suffix
    if suffix is None:
        suffix = Path(file.filename or "").suffix.lower() or ".bin"
    
    with TempFileManager(suffix=suffix) as temp_path:
        temp_path.write_bytes(content)
        return temp_path


def ensure_rgba(image: Image.Image) -> Image.Image:
    """
    Convert image to RGBA format, preserving transparency.
    
    Args:
        image: PIL Image to convert
        
    Returns:
        RGBA converted image
    """
    if image.mode == "RGBA":
        return image
    
    if image.mode in ("P", "L", "RGB", "LA"):
        # Use transparent background
        bg = Image.new("RGBA", image.size, (0, 0, 0, 0))
        bg.paste(image, (0, 0))
        return bg
    
    return image.convert("RGBA")


def parse_grid(grid: str) -> Tuple[int, int]:
    """
    Parse grid string into columns and rows.
    
    Args:
        grid: Grid string in format "colsxrows" or "auto"
        
    Returns:
        Tuple of (columns, rows)
        
    Raises:
        HTTPException: If grid format is invalid
    """
    if grid.lower() == "auto":
        return (0, 0)  # Sentinel for auto layout
    
    if "x" not in grid:
        raise HTTPException(
            status_code=400, 
            detail="Grid must be 'colsxrows' (e.g., '5x2') or 'auto'."
        )
    
    try:
        cols, rows = map(int, grid.lower().split("x"))
        if cols <= 0 or rows <= 0:
            raise ValueError("Grid numbers must be positive")
        return cols, rows
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Grid numbers must be positive integers."
        )


def calculate_auto_grid(num_frames: int) -> Tuple[int, int]:
    """
    Calculate near-square grid for given number of frames.
    
    Args:
        num_frames: Number of frames to arrange
        
    Returns:
        Tuple of (columns, rows)
    """
    cols = int(math.ceil(math.sqrt(num_frames)))
    rows = int(math.ceil(num_frames / cols))
    return cols, rows


def find_divisors(n: int, max_divisor: int = 20) -> List[int]:
    """
    Find divisors of a number up to a maximum.
    
    Args:
        n: Number to find divisors for
        max_divisor: Maximum divisor to consider
        
    Returns:
        List of divisors
    """
    divisors = []
    for i in range(1, min(n, max_divisor) + 1):
        if n % i == 0:
            divisors.append(i)
    return divisors


def extract_gif_frames(
    gif_path: Path, 
    max_frames: Optional[int] = None
) -> List[Image.Image]:
    """
    Extract frames from GIF file.
    
    Args:
        gif_path: Path to GIF file
        max_frames: Maximum number of frames to extract
        
    Returns:
        List of PIL Images
        
    Raises:
        HTTPException: If GIF has no frames
    """
    frames = []
    
    with Image.open(gif_path) as gif:
        for idx, frame in enumerate(ImageSequence.Iterator(gif)):
            rgba_frame = ensure_rgba(frame.convert("RGBA"))
            frames.append(rgba_frame.copy())
            
            if max_frames and len(frames) >= max_frames:
                break
    
    if not frames:
        raise HTTPException(status_code=400, detail="GIF has no frames")
    
    return frames


def extract_spritesheet_frames(
    spritesheet: Image.Image,
    cols: int,
    rows: int,
    frame_width: Optional[int] = None,
    frame_height: Optional[int] = None,
    max_frames: Optional[int] = None
) -> List[Image.Image]:
    """
    Extract frames from spritesheet image.
    
    Args:
        spritesheet: Spritesheet PIL Image
        cols: Number of columns
        rows: Number of rows
        frame_width: Override frame width
        frame_height: Override frame height
        max_frames: Maximum frames to extract
        
    Returns:
        List of extracted frame images
    """
    sw, sh = spritesheet.size
    
    # Calculate frame dimensions
    if frame_width and frame_height:
        fw, fh = int(frame_width), int(frame_height)
        if fw <= 0 or fh <= 0:
            raise HTTPException(
                status_code=400, 
                detail="frameWidth and frameHeight must be > 0"
            )
    else:
        fw = sw // cols
        fh = sh // rows
    
    if fw <= 0 or fh <= 0:
        raise HTTPException(
            status_code=400, 
            detail="Computed frame size is invalid."
        )
    
    frames_per_row = sw // fw
    frames_per_col = sh // fh
    total_possible = frames_per_row * frames_per_col
    max_take = min(max_frames or total_possible, total_possible)
    
    frames = []
    count = 0
    
    for r in range(frames_per_col):
        for c in range(frames_per_row):
            if count >= max_take:
                break
                
            left = c * fw
            top = r * fh
            right = left + fw
            bottom = top + fh
            
            cropped = spritesheet.crop((left, top, right, bottom))
            frames.append(ensure_rgba(cropped))
            count += 1
            
        if count >= max_take:
            break
    
    if not frames:
        raise HTTPException(
            status_code=500, 
            detail="No frames could be extracted from the spritesheet."
        )
    
    return frames


def create_spritesheet(
    frames: List[Image.Image],
    cols: int,
    rows: int,
    frame_width: Optional[int] = None,
    frame_height: Optional[int] = None
) -> Image.Image:
    """
    Create spritesheet from list of frames.
    
    Args:
        frames: List of PIL Images
        cols: Number of columns
        rows: Number of rows
        frame_width: Override frame width
        frame_height: Override frame height
        
    Returns:
        Combined spritesheet image
    """
    if not frames:
        raise ValueError("No frames provided")
    
    # Use first frame dimensions if not specified
    fw = frame_width or frames[0].width
    fh = frame_height or frames[0].height
    
    # Calculate spritesheet dimensions
    total_slots = cols * rows if cols and rows else len(frames)
    if total_slots < len(frames):
        # Auto-calculate grid if too small
        cols, rows = calculate_auto_grid(len(frames))
    
    combined_w = cols * fw
    combined_h = rows * fh
    combined = Image.new("RGBA", (combined_w, combined_h), (0, 0, 0, 0))
    
    for i, frame in enumerate(frames):
        if i >= cols * rows:
            break
            
        r = i // cols
        c = i % cols
        combined.paste(frame, (c * fw, r * fh))
    
    return combined


def encode_image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """
    Encode PIL Image to base64 string.
    
    Args:
        image: PIL Image to encode
        format: Image format (PNG, JPEG, etc.)
        
    Returns:
        Base64 encoded string
    """
    import io
    
    img_bytes = io.BytesIO()
    image.save(img_bytes, format=format)
    img_bytes.seek(0)
    
    return base64.b64encode(img_bytes.getvalue()).decode("utf-8")


def encode_file_to_base64(file_path: Path) -> str:
    """
    Encode file to base64 string.
    
    Args:
        file_path: Path to file
        
    Returns:
        Base64 encoded string
    """
    with open(file_path, "rb") as f:
        content = f.read()
    return base64.b64encode(content).decode("utf-8")


def create_success_response(
    data: Dict[str, Any],
    filename: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create standardized success response.
    
    Args:
        data: Response data
        filename: Original filename
        **kwargs: Additional response fields
        
    Returns:
        Standardized response dictionary
    """
    response = {
        "success": True,
        **data
    }
    
    if filename:
        response["filename"] = filename
    
    response.update(kwargs)
    return response


def create_error_response(
    error: str,
    status_code: int = 500,
    **kwargs
) -> HTTPException:
    """
    Create standardized error response.
    
    Args:
        error: Error message
        status_code: HTTP status code
        **kwargs: Additional error fields
        
    Returns:
        HTTPException with error details
    """
    detail = {"error": error}
    detail.update(kwargs)
    return HTTPException(status_code=status_code, detail=detail)


def cleanup_temp_files(*file_paths: Path) -> None:
    """
    Clean up temporary files.
    
    Args:
        *file_paths: Paths to files to delete
    """
    for file_path in file_paths:
        if file_path and file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to clean up {file_path}: {e}")


def cleanup_temp_dirs(*dir_paths: Path) -> None:
    """
    Clean up temporary directories.
    
    Args:
        *dir_paths: Paths to directories to delete
    """
    import shutil
    
    for dir_path in dir_paths:
        if dir_path and dir_path.exists():
            try:
                shutil.rmtree(dir_path, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to clean up {dir_path}: {e}")

