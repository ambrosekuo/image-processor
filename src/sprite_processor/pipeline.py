"""
Pipeline module for sprite-processor.

Handles end-to-end workflows: Video → GIF → Spritesheet → Background Removal
"""

import logging
from pathlib import Path
from typing import Any

from .video import analyze_video, extract_gif_frames, video_to_gif

logger = logging.getLogger(__name__)


class VideoPipelineConfig:
    """Configuration for video processing pipeline."""

    def __init__(
        self,
        fps: int = 10,
        duration: float | None = None,
        grid: str = "5x2",
        frames: int | None = None,
        model: str = "isnet-general-use",
        max_width: int = 480,
        max_height: int = 480,
    ):
        self.fps = fps
        self.duration = duration
        self.grid = grid
        self.frames = frames
        self.model = model
        self.max_width = max_width
        self.max_height = max_height


def process_video_pipeline(
    video_path: Path | str,
    output_dir: Path | str,
    config: VideoPipelineConfig,
    keep_intermediates: bool = False,
) -> dict[str, Any]:
    """
    Complete pipeline: Video → GIF → Spritesheet → Background Removal

    Args:
        video_path: Path to input video file
        output_dir: Directory for output files
        config: Pipeline configuration
        keep_intermediates: Whether to keep intermediate files

    Returns:
        Dictionary with paths to all generated files
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    logger.info(f"🚀 Starting video pipeline: {video_path.name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = video_path.stem
    gif_path = output_dir / f"{base_name}.gif"
    spritesheet_path = output_dir / f"{base_name}_spritesheet.png"
    processed_path = output_dir / f"{base_name}_processed.png"
    results = {
        "video_path": video_path,
        "gif_path": None,
        "spritesheet_path": None,
        "processed_path": None,
        "intermediate_files": [],
    }
    try:
        logger.info("📹 Step 1: Converting video to GIF...")
        video_to_gif(
            video_path,
            gif_path,
            fps=config.fps,
            duration=config.duration,
            max_width=config.max_width,
            max_height=config.max_height,
        )
        results["gif_path"] = gif_path
        results["intermediate_files"].append(gif_path)
        logger.info("🖼️ Step 2: Creating spritesheet from GIF...")
        try:
            cols, rows = map(int, config.grid.split("x"))
        except ValueError:
            raise ValueError(f"Invalid grid format: {config.grid}. Use format like '5x2'") from None
        frames = extract_gif_frames(gif_path, max_frames=config.frames)
        from .cli import _create_spritesheet

        _create_spritesheet(frames, cols, rows, spritesheet_path)
        results["spritesheet_path"] = spritesheet_path
        results["intermediate_files"].append(spritesheet_path)
        logger.info("🎨 Step 3: Removing background from spritesheet...")
        from .cli import _process_one

        _process_one(spritesheet_path, processed_path, model_name=config.model)
        results["processed_path"] = processed_path
        if not keep_intermediates:
            logger.info("🧹 Cleaning up intermediate files...")
            for file_path in results["intermediate_files"]:
                if file_path.exists():
                    file_path.unlink()
            results["intermediate_files"] = []
        logger.info("✅ Pipeline completed successfully!")
        return results
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        for file_path in results["intermediate_files"]:
            if file_path.exists():
                file_path.unlink()
        raise


def process_video_pipeline_all_models(
    video_path: Path | str,
    output_dir: Path | str,
    config: VideoPipelineConfig,
    keep_intermediates: bool = False,
) -> dict[str, Any]:
    """
    Complete pipeline with all background removal models for comparison.

    Args:
        video_path: Path to input video file
        output_dir: Directory for output files
        config: Pipeline configuration
        keep_intermediates: Whether to keep intermediate files

    Returns:
        Dictionary with paths to all generated files and model results
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    logger.info(f"🚀 Starting video pipeline (all models): {video_path.name}")
    models = [
        "isnet-general-use",
        "isnet-anime",
        "bria-rmbg-1.4",
        "u2net_human_seg",
        "u2net",
        "u2netp",
        "u2net_cloth_seg",
        "silueta",
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = video_path.stem
    gif_path = output_dir / f"{base_name}.gif"
    spritesheet_path = output_dir / f"{base_name}_spritesheet.png"
    results = {
        "video_path": video_path,
        "gif_path": None,
        "spritesheet_path": None,
        "model_results": {},
        "intermediate_files": [],
    }
    try:
        logger.info("📹 Step 1: Converting video to GIF...")
        video_to_gif(
            video_path,
            gif_path,
            fps=config.fps,
            duration=config.duration,
            max_width=config.max_width,
            max_height=config.max_height,
        )
        results["gif_path"] = gif_path
        results["intermediate_files"].append(gif_path)
        logger.info("🖼️ Step 2: Creating spritesheet from GIF...")
        try:
            cols, rows = map(int, config.grid.split("x"))
        except ValueError:
            raise ValueError(f"Invalid grid format: {config.grid}. Use format like '5x2'") from None
        frames = extract_gif_frames(gif_path, max_frames=config.frames)
        from .cli import _create_spritesheet

        _create_spritesheet(frames, cols, rows, spritesheet_path)
        results["spritesheet_path"] = spritesheet_path
        results["intermediate_files"].append(spritesheet_path)
        logger.info("🎨 Step 3: Processing with all models...")
        for i, model in enumerate(models, 1):
            logger.info(f"   🔄 Processing with model {i}/{len(models)}: {model}")
            try:
                from .cli import _process_one

                processed_path = output_dir / f"{base_name}_{model}_processed.png"
                _process_one(spritesheet_path, processed_path, model_name=model)
                results["model_results"][model] = {
                    "path": processed_path,
                    "success": True,
                    "size": processed_path.stat().st_size,
                }
                logger.info(f"   ✅ {model} completed successfully")
            except Exception as e:
                logger.error(f"   ❌ {model} failed: {e}")
                results["model_results"][model] = {"path": None, "success": False, "error": str(e)}
        if not keep_intermediates:
            logger.info("🧹 Cleaning up intermediate files...")
            for file_path in results["intermediate_files"]:
                if file_path.exists():
                    file_path.unlink()
            results["intermediate_files"] = []
        successful_models = sum(1 for r in results["model_results"].values() if r["success"])
        logger.info(f"✅ Pipeline completed! {successful_models}/{len(models)} models successful")
        return results
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        for file_path in results["intermediate_files"]:
            if file_path.exists():
                file_path.unlink()
        raise


def analyze_video_for_pipeline(video_path: Path) -> dict[str, Any]:
    """
    Analyze video and provide recommendations for pipeline processing.

    Args:
        video_path: Path to video file

    Returns:
        Dictionary with analysis and recommendations
    """
    logger.info(f"🔍 Analyzing video for pipeline: {video_path.name}")
    analysis = analyze_video(video_path)
    duration = analysis["duration"]
    analysis["fps"]
    size = analysis["size"]
    if duration <= 2:
        recommended_grid = "3x2"
    elif duration <= 4:
        recommended_grid = "4x2"
    else:
        recommended_grid = "5x2"
    recommendations = {
        "fps": analysis["recommended_fps"],
        "duration": analysis["recommended_duration"],
        "grid": recommended_grid,
        "frames": analysis["recommended_frames"],
        "max_width": min(480, size[0]),
        "max_height": min(480, size[1]),
        "estimated_processing_time": f"{analysis['recommended_frames'] * 6 * 2:.0f} seconds",
    }
    return {"video_analysis": analysis, "recommendations": recommendations}
