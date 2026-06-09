"""
Video processing module for sprite-processor.

Handles video to GIF conversion, frame extraction, and video analysis.
"""

import logging
import tempfile
from pathlib import Path

try:
    import imageio  # noqa: F401
    from moviepy.editor import VideoFileClip
    from PIL import Image
except ImportError as e:
    raise ImportError(
        "Video processing dependencies not installed. "
        "Run: pip install moviepy imageio[ffmpeg] pillow"
    ) from e
logger = logging.getLogger(__name__)


def _disposal_method(gif: Image.Image) -> int:
    method = getattr(gif, "disposal_method", None)
    if method is None:
        method = gif.info.get("disposal", 0)
    try:
        return int(method or 0)
    except (TypeError, ValueError):
        return 0


def _frame_extent(gif: Image.Image) -> tuple[int, int, int, int]:
    extent = getattr(gif, "dispose_extent", None)
    if extent:
        return extent
    w, h = gif.size
    return (0, 0, w, h)


def _select_frame_indices(
    total_frames: int, max_frames: int | None, frame_interval: int, sample_evenly: bool
) -> list[int]:
    if sample_evenly and max_frames and (max_frames > 0):
        if max_frames >= total_frames:
            return list(range(0, total_frames, frame_interval))
        evenly = [
            int(round(k * (total_frames - 1) / max(1, max_frames - 1))) for k in range(max_frames)
        ]
        return sorted(set(i for i in evenly if i % frame_interval == 0)) or [0]
    indices = list(range(0, total_frames, frame_interval))
    if max_frames is not None and max_frames > 0:
        indices = indices[:max_frames]
    return indices


def _read_composited_gif_frames(gif_path: Path) -> list[Image.Image]:
    """
    Read every frame from a GIF as a full-size composited RGBA image.

    Animated GIFs often store partial patches per frame; this applies GIF89a
    disposal/compositing so each returned frame is the full canvas.
    """
    gif_path = Path(gif_path)
    try:
        import imageio.v3 as iio

        data = iio.imread(gif_path, index=None)
        if getattr(data, "ndim", 0) == 4 and data.shape[0] > 0 and (data.shape[-1] == 4):
            frames = [Image.fromarray(data[i], mode="RGBA") for i in range(data.shape[0])]
            logger.info(f"   Read {len(frames)} RGBA frames via imageio")
            return frames
    except Exception as exc:
        logger.debug(f"   imageio GIF read unavailable, using PIL compositor: {exc}")
    backdrop = (0, 0, 0, 0)
    composited: list[Image.Image] = []
    with Image.open(gif_path) as gif:
        size = gif.size
        total = int(getattr(gif, "n_frames", 1)) or 1
        canvas = Image.new("RGBA", size, backdrop)
        saved_canvas: Image.Image | None = None
        prev_disposal = 0
        prev_extent: tuple[int, int, int, int] | None = None
        for idx in range(total):
            gif.seek(idx)
            if idx > 0 and prev_extent is not None:
                x0, y0, x1, y1 = prev_extent
                if prev_disposal == 2:
                    clear = Image.new("RGBA", (x1 - x0, y1 - y0), backdrop)
                    canvas.paste(clear, (x0, y0))
                elif prev_disposal == 3 and saved_canvas is not None:
                    canvas = saved_canvas.copy()
            current_disposal = _disposal_method(gif)
            if current_disposal == 3:
                saved_canvas = canvas.copy()
            frame = gif.convert("RGBA")
            extent = _frame_extent(gif)
            x0, y0, x1, y1 = extent
            if frame.size == size:
                canvas.paste(frame, (0, 0), frame)
            else:
                canvas.paste(frame, (x0, y0), frame)
            prev_disposal = current_disposal
            prev_extent = extent
            composited.append(canvas.copy())
    logger.info(f"   Composited {len(composited)} frames via PIL")
    return composited


def _warn_if_duplicate_frames(frames: list[Image.Image]) -> None:
    if len(frames) < 2:
        return
    first = frames[0].tobytes()
    dupes = sum(1 for frame in frames[1:] if frame.tobytes() == first)
    if dupes > 0:
        logger.warning(
            "   ⚠️ %s/%s extracted frames appear identical to frame 0. "
            "The GIF may use an unusual encoding.",
            dupes + 1,
            len(frames),
        )


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _constrain_size(w: int, h: int, max_w: int, max_h: int) -> tuple[int, int]:
    """Constrain (w,h) to fit inside (max_w,max_h) preserving aspect ratio."""
    if w <= max_w and h <= max_h:
        return (w, h)
    scale = min(max_w / float(w), max_h / float(h))
    return (max(1, int(round(w * scale))), max(1, int(round(h * scale))))


def extract_gif_frames_to_dir(
    gif_path: Path, output_dir: Path, max_frames: int | None = None, *, sample_evenly: bool = False
) -> list[Path]:
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
            raise ValueError(f"max_frames must be int, got {type(max_frames)}") from None
    frame_paths: list[Path] = []
    try:
        all_frames = _read_composited_gif_frames(gif_path)
        gif_size = all_frames[0].size if all_frames else "unknown"
        logger.info("   GIF info: %s, %s frames", gif_size, len(all_frames))
        indices = _select_frame_indices(len(all_frames), max_frames, 1, sample_evenly=sample_evenly)
        for _out_idx, frame_index in enumerate(indices):
            frame = all_frames[frame_index]
            frame_path = output_dir / f"frame_{frame_index:03d}.png"
            frame.save(frame_path, "PNG")
            frame_paths.append(frame_path)
        _warn_if_duplicate_frames([all_frames[i] for i in indices])
        logger.info(f"   ✅ Extracted {len(frame_paths)} frames to {output_dir}")
        return frame_paths
    except Exception as e:
        logger.error(f"   ❌ Error extracting GIF frames to dir: {e}")
        raise


def extract_gif_frames(
    gif_path: Path,
    max_frames: int | str | None = None,
    frame_interval: int = 1,
    *,
    sample_evenly: bool = False,
) -> list[Image.Image]:
    """
    Extract frames from GIF for spritesheet creation and return PIL Images.

    If sample_evenly=True and max_frames is provided, sample evenly across
    the GIF instead of taking the first N frames.
    """
    logger.info(f"🖼️ Extracting frames from GIF: {gif_path.name}")
    if not gif_path.exists():
        raise FileNotFoundError(f"GIF file not found: {gif_path}")
    if isinstance(max_frames, Path):
        raise ValueError("max_frames cannot be a Path. Did you pass an output_dir by position?")
    if isinstance(max_frames, str):
        if not max_frames.isdigit():
            raise ValueError(f"max_frames must be an integer string, got '{max_frames}'")
        max_frames = int(max_frames)
    try:
        all_frames = _read_composited_gif_frames(gif_path)
        total_frames = len(all_frames)
        logger.info(f"   GIF has {total_frames} frames")
        indices = _select_frame_indices(
            total_frames, max_frames, frame_interval, sample_evenly=sample_evenly
        )
        frames = [all_frames[i].copy() for i in indices]
        _warn_if_duplicate_frames(frames)
        logger.info(f"   ✅ Extracted {len(frames)} frames (in-memory)")
        return frames
    except Exception as e:
        logger.error(f"❌ Frame extraction failed: {e}")
        raise ValueError(f"Failed to extract frames: {e}") from e


def video_to_gif(
    video_path: Path | str,
    output_path: Path | str,
    fps: int = 10,
    duration: float | None = None,
    max_width: int = 480,
    max_height: int = 480,
) -> Path:
    """Convert video to GIF with custom settings."""
    video_path = Path(video_path)
    output_path = Path(output_path)
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
            if duration is not None and 0 < duration < original_duration:
                if hasattr(clip, "set_end"):
                    clip = clip.set_end(duration)
                elif hasattr(clip, "with_duration"):
                    clip = clip.with_duration(duration)
                logger.info(f"   Trimmed to: {duration:.2f}s")
            nw, nh = _constrain_size(clip.w, clip.h, max_width, max_height)
            if (nw, nh) != (clip.w, clip.h):
                clip = clip.resize(newsize=(nw, nh))
                logger.info(f"   Resized to: {nw}x{nh}")
            logger.info(f"   Writing GIF with {fps} FPS via ffmpeg...")
            clip.write_gif(str(output_path), fps=fps, program="ffmpeg")
            output_size = output_path.stat().st_size
            logger.info(f"   ✅ GIF created: {output_size / 1024:.1f} KB")
            return output_path
    except Exception as e:
        logger.error(f"❌ Video conversion failed: {e}")
        raise ValueError(f"Failed to convert video: {e}") from e


def analyze_video(video_path: Path | str, target_fps: int = 10) -> dict:
    """Analyze video properties for processing recommendations."""
    video_path = Path(video_path)
    logger.info(f"🔍 Analyzing video: {video_path.name}")
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    try:
        with VideoFileClip(str(video_path)) as clip:
            duration = float(clip.duration or 0.0)
            fps = float(clip.fps or 0.0)
            size = tuple(clip.size)
            int(round(duration * fps)) if fps > 0 else 0
            recommended_fps = min(target_fps, max(5, int(round(max(1.0, fps) / 2))))
            recommended_duration = min(5.0, duration)
            recommended_frames = int(round(recommended_duration * recommended_fps))
            analysis = {
                "duration": duration,
                "fps": recommended_fps,
                "width": size[0],
                "height": size[1],
                "frames": recommended_frames,
                "file_size": video_path.stat().st_size,
            }
            logger.info(
                "   Recommended: %s FPS, %.2fs, %s frames",
                recommended_fps,
                recommended_duration,
                recommended_frames,
            )
            return analysis
    except Exception as e:
        logger.error(f"❌ Video analysis failed: {e}")
        raise ValueError(f"Failed to analyze video: {e}") from e


def video_to_spritesheet(
    video_path: Path | str,
    output_path: Path | str,
    grid: str,
    frames: int | None = None,
    fps: int = 10,
    duration: float | None = None,
    *,
    max_width: int = 480,
    max_height: int = 480,
    sample_evenly: bool = True,
) -> Path:
    """
    Convert video directly to spritesheet by extracting frames.

    grid: like "5x2" (cols x rows).
    If 'frames' is not provided, it defaults to cols*rows.
    """
    video_path = Path(video_path)
    output_path = Path(output_path)
    logger.info(f"🎬 Converting video to spritesheet: {video_path.name}")
    try:
        cols, rows = map(int, grid.lower().split("x"))
        if cols <= 0 or rows <= 0:
            raise ValueError
    except Exception:
        raise ValueError(f"Invalid grid format: {grid}. Use format like '5x2'") from None
    target_frames = frames if frames and frames > 0 else cols * rows
    with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as temp_gif:
        temp_gif_path = Path(temp_gif.name)
    try:
        video_to_gif(
            video_path,
            temp_gif_path,
            fps=fps,
            duration=duration,
            max_width=max_width,
            max_height=max_height,
        )
        extracted_frames = extract_gif_frames(
            temp_gif_path, max_frames=target_frames, frame_interval=1, sample_evenly=sample_evenly
        )
        needed = cols * rows
        if len(extracted_frames) < needed and extracted_frames:
            last = extracted_frames[-1]
            extracted_frames.extend([last.copy() for _ in range(needed - len(extracted_frames))])
        elif len(extracted_frames) > needed:
            extracted_frames = extracted_frames[:needed]
        from .cli import _create_spritesheet

        _ensure_parent_dir(output_path)
        spritesheet_path = _create_spritesheet(extracted_frames, cols, rows, output_path)
        logger.info(f"   ✅ Spritesheet created: {spritesheet_path}")
        return spritesheet_path
    finally:
        try:
            if temp_gif_path.exists():
                temp_gif_path.unlink()
        except Exception:
            pass
