"""
Video processing module for sprite-processor.

Handles video to GIF conversion, frame extraction, and video analysis.
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple, Union
import tempfile

try:
    # Correct import
    from moviepy.editor import VideoFileClip  # type: ignore
    from PIL import Image
    import imageio  # noqa: F401  # required transitively by moviepy for GIF/ffmpeg
except ImportError as e:
    raise ImportError(
        "Video processing dependencies not installed. "
        "Run: pip install moviepy imageio[ffmpeg] pillow"
    ) from e

logger = logging.getLogger(__name__)


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _constrain_size(w: int, h: int, max_w: int, max_h: int) -> Tuple[int, int]:
    """Constrain (w,h) to fit inside (max_w,max_h) preserving aspect ratio."""
    if w <= max_w and h <= max_h:
        return w, h
    scale = min(max_w / float(w), max_h / float(h))
    return max(1, int(round(w * scale))), max(1, int(round(h * scale)))


# ---------- Disk-extract variant (RENAMED to avoid collision) ----------
def extract_gif_frames_to_dir(
    gif_path: Path,
    output_dir: Path,
    max_frames: Optional[int] = None
) -> List[Path]:
    """
    Extract individual frames from an animated GIF to disk.
    Returns a list of written PNG paths.
    """
    logger.info(f"🎬 Extracting frames from GIF to dir: {gif_path.name}")
    output_dir.mkdir(parents=True, exist_ok=True)

    if max_frames is not None:
        try:
            max_frames = int(max_frames)
        except Exception:
            raise ValueError(f"max_frames must be int, got {type(max_frames)}")

    frame_paths: List[Path] = []
    try:
        with Image.open(gif_path) as gif:
            total_frames = int(getattr(gif, "n_frames", 1)) or 1
            logger.info(f"   GIF info: {gif.size}, {total_frames} frames")

            frame_count = 0
            for frame_index in range(total_frames):
                if max_frames is not None and frame_count >= max_frames:
                    break
                gif.seek(frame_index)
                frame = gif.convert("RGBA")
                frame_path = output_dir / f"frame_{frame_index:03d}.png"
                frame.save(frame_path, "PNG")
                frame_paths.append(frame_path)
                frame_count += 1

        logger.info(f"   ✅ Extracted {len(frame_paths)} frames to {output_dir}")
        return frame_paths

    except Exception as e:
        logger.error(f"   ❌ Error extracting GIF frames to dir: {e}")
        raise


# ---------- In-memory frames variant (kept as the canonical name) ----------
def extract_gif_frames(
    gif_path: Path,
    max_frames: Optional[Union[int, str]] = None,
    frame_interval: int = 1,
    *,
    sample_evenly: bool = False
) -> List[Image.Image]:
    """
    Extract frames from GIF for spritesheet creation and return PIL Images.

    If sample_evenly=True and max_frames is provided, sample evenly across
    the GIF instead of taking the first N frames.
    """
    logger.info(f"🖼️ Extracting frames from GIF: {gif_path.name}")

    if not gif_path.exists():
        raise FileNotFoundError(f"GIF file not found: {gif_path}")

    # Defensive: coerce max_frames to int if passed as str; reject Paths.
    if isinstance(max_frames, (Path, )):
        raise ValueError("max_frames cannot be a Path. Did you pass an output_dir by position?")
    if isinstance(max_frames, str):
        if not max_frames.isdigit():
            raise ValueError(f"max_frames must be an integer string, got '{max_frames}'")
        max_frames = int(max_frames)

    try:
        frames: List[Image.Image] = []
        with Image.open(gif_path) as img:
            total_frames = int(getattr(img, "n_frames", 1)) or 1
            logger.info(f"   GIF has {total_frames} frames")

            if sample_evenly and max_frames and max_frames > 0:
                if max_frames >= total_frames:
                    indices = list(range(0, total_frames, frame_interval))
                else:
                    # Evenly spaced indices across [0, total_frames-1]
                    evenly = [
                        int(round(k * (total_frames - 1) / max(1, (max_frames - 1))))
                        for k in range(max_frames)
                    ]
                    indices = sorted(set(i for i in evenly if i % frame_interval == 0)) or [0]
            else:
                indices = list(range(0, total_frames, frame_interval))
                if max_frames is not None and max_frames > 0:
                    indices = indices[:max_frames]

            for i, frame_idx in enumerate(indices, start=1):
                img.seek(frame_idx)
                frame = img.convert("RGBA").copy()
                frames.append(frame)

        logger.info(f"   ✅ Extracted {len(frames)} frames (in-memory)")
        return frames

    except Exception as e:
        logger.error(f"❌ Frame extraction failed: {e}")
        raise ValueError(f"Failed to extract frames: {e}") from e


def video_to_gif(
    video_path: Path,
    output_path: Path,
    fps: int = 10,
    duration: Optional[float] = None,
    max_width: int = 480,
    max_height: int = 480
) -> Path:
    """Convert video to GIF with custom settings."""
    logger.info(f"🎬 Converting video to GIF: {video_path.name}")

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    _ensure_parent_dir(output_path)

    try:
        with VideoFileClip(str(video_path)) as clip:
            original_duration = float(clip.duration or 0.0)
            original_fps = float(clip.fps or 0.0)
            ow, oh = clip.size
            logger.info(f"   Original: {ow}x{oh}, {original_fps:.1f}fps, {original_duration:.2f}s")

            # Version-proof trim: use set_end()/with_duration
            if duration is not None and 0 < duration < original_duration:
                if hasattr(clip, "set_end"):
                    clip = clip.set_end(duration)
                elif hasattr(clip, "with_duration"):
                    clip = clip.with_duration(duration)
                logger.info(f"   Trimmed to: {duration:.2f}s")

            # FIXED INDENT: resize should not be nested inside the trim block
            nw, nh = _constrain_size(clip.w, clip.h, max_width, max_height)
            if (nw, nh) != (clip.w, clip.h):
                clip = clip.resize(newsize=(nw, nh))
                logger.info(f"   Resized to: {nw}x{nh}")

            # Write GIF
            logger.info(f"   Writing GIF with {fps} FPS via ffmpeg...")
            clip.write_gif(str(output_path), fps=fps, program="ffmpeg")

            output_size = output_path.stat().st_size
            logger.info(f"   ✅ GIF created: {output_size / 1024:.1f} KB")
            return output_path

    except Exception as e:
        logger.error(f"❌ Video conversion failed: {e}")
        raise ValueError(f"Failed to convert video: {e}") from e


def analyze_video(video_path: Path) -> dict:
    """Analyze video properties for processing recommendations."""
    logger.info(f"🔍 Analyzing video: {video_path.name}")

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    try:
        with VideoFileClip(str(video_path)) as clip:
            duration = float(clip.duration or 0.0)
            fps = float(clip.fps or 0.0)
            size = tuple(clip.size)
            total_frames = int(round(duration * fps)) if fps > 0 else 0

            recommended_fps = min(10, max(5, int(round(max(1.0, fps) / 2))))
            recommended_duration = min(5.0, duration)
            recommended_frames = int(round(recommended_duration * recommended_fps))

            analysis = {
                "duration": duration,
                "fps": fps,
                "size": size,
                "total_frames": total_frames,
                "recommended_fps": recommended_fps,
                "recommended_duration": recommended_duration,
                "recommended_frames": recommended_frames,
                "file_size": video_path.stat().st_size,
            }

            logger.info(
                f"   Recommended: {recommended_fps} FPS, {recommended_duration:.2f}s, {recommended_frames} frames"
            )
            return analysis

    except Exception as e:
        logger.error(f"❌ Video analysis failed: {e}")
        raise ValueError(f"Failed to analyze video: {e}") from e


def video_to_spritesheet(
    video_path: Path,
    output_path: Path,
    grid: str,
    frames: Optional[int] = None,
    fps: int = 10,
    duration: Optional[float] = None,
    *,
    max_width: int = 480,
    max_height: int = 480,
    sample_evenly: bool = True
) -> Path:
    """
    Convert video directly to spritesheet by extracting frames.

    grid: like "5x2" (cols x rows).
    If 'frames' is not provided, it defaults to cols*rows.
    """
    logger.info(f"🎬 Converting video to spritesheet: {video_path.name}")

    # Parse grid
    try:
        cols, rows = map(int, grid.lower().split("x"))
        if cols <= 0 or rows <= 0:
            raise ValueError
    except Exception:
        raise ValueError(f"Invalid grid format: {grid}. Use format like '5x2'")

    target_frames = frames if (frames and frames > 0) else cols * rows

    # Create temporary GIF first
    with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as temp_gif:
        temp_gif_path = Path(temp_gif.name)

    try:
        # Convert video to GIF (respect max size so frames match spritesheet cell bounds better)
        video_to_gif(
            video_path,
            temp_gif_path,
            fps=fps,
            duration=duration,
            max_width=max_width,
            max_height=max_height,
        )

        # Extract frames from GIF (even sampling across the whole clip is usually best for sprites)
        extracted_frames = extract_gif_frames(
            temp_gif_path,
            max_frames=target_frames,
            frame_interval=1,
            sample_evenly=sample_evenly,
        )

        # Pad/trim to grid size
        needed = cols * rows
        if len(extracted_frames) < needed and extracted_frames:
            last = extracted_frames[-1]
            extracted_frames.extend([last.copy() for _ in range(needed - len(extracted_frames))])
        elif len(extracted_frames) > needed:
            extracted_frames = extracted_frames[:needed]

        # Create spritesheet from frames
        from .cli import _create_spritesheet  # expects (images, cols, rows, output_path) -> Path
        _ensure_parent_dir(output_path)
        spritesheet_path = _create_spritesheet(extracted_frames, cols, rows, output_path)

        logger.info(f"   ✅ Spritesheet created: {spritesheet_path}")
        return spritesheet_path

    finally:
        # Clean up temporary GIF
        try:
            if temp_gif_path.exists():
                temp_gif_path.unlink()
        except Exception:
            pass
