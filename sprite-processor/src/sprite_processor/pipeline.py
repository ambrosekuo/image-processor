"""
Pipeline module for sprite-processor.

Handles end-to-end workflows: Video → GIF → Spritesheet → Background Removal
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
import tempfile
import shutil

from .video import video_to_gif, extract_gif_frames, analyze_video

logger = logging.getLogger(__name__)


class VideoPipelineConfig:
    """Configuration for video processing pipeline."""
    
    def __init__(
        self,
        fps: int = 10,
        duration: Optional[float] = None,
        grid: str = "5x2",
        frames: Optional[int] = None,
        model: str = "isnet-general-use",
        max_width: int = 480,
        max_height: int = 480
    ):
        self.fps = fps
        self.duration = duration
        self.grid = grid
        self.frames = frames
        self.model = model
        self.max_width = max_width
        self.max_height = max_height


def process_video_pipeline(
    video_path: Path,
    output_dir: Path,
    config: VideoPipelineConfig,
    keep_intermediates: bool = False
) -> Dict[str, Any]:
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
    logger.info(f"🚀 Starting video pipeline: {video_path.name}")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate output filenames
    base_name = video_path.stem
    gif_path = output_dir / f"{base_name}.gif"
    spritesheet_path = output_dir / f"{base_name}_spritesheet.png"
    processed_path = output_dir / f"{base_name}_processed.png"
    
    results = {
        'video_path': video_path,
        'gif_path': None,
        'spritesheet_path': None,
        'processed_path': None,
        'intermediate_files': []
    }
    
    try:
        # Step 1: Video to GIF
        logger.info("📹 Step 1: Converting video to GIF...")
        video_to_gif(
            video_path, 
            gif_path, 
            fps=config.fps, 
            duration=config.duration,
            max_width=config.max_width,
            max_height=config.max_height
        )
        results['gif_path'] = gif_path
        results['intermediate_files'].append(gif_path)
        
        # Step 2: GIF to Spritesheet
        logger.info("🖼️ Step 2: Creating spritesheet from GIF...")
        
        # Parse grid
        try:
            cols, rows = map(int, config.grid.split('x'))
        except ValueError:
            raise ValueError(f"Invalid grid format: {config.grid}. Use format like '5x2'")
        
        # Extract frames from GIF
        frames = extract_gif_frames(gif_path, max_frames=config.frames)
        
        # Create spritesheet
        from .cli import _create_spritesheet
        _create_spritesheet(frames, cols, rows, spritesheet_path)
        results['spritesheet_path'] = spritesheet_path
        results['intermediate_files'].append(spritesheet_path)
        
        # Step 3: Background Removal
        logger.info("🎨 Step 3: Removing background from spritesheet...")
        from .cli import _process_one
        _process_one(spritesheet_path, processed_path, model_name=config.model)
        results['processed_path'] = processed_path
        
        # Clean up intermediate files if requested
        if not keep_intermediates:
            logger.info("🧹 Cleaning up intermediate files...")
            for file_path in results['intermediate_files']:
                if file_path.exists():
                    file_path.unlink()
            results['intermediate_files'] = []
        
        logger.info("✅ Pipeline completed successfully!")
        return results
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        # Clean up on failure
        for file_path in results['intermediate_files']:
            if file_path.exists():
                file_path.unlink()
        raise


def process_video_pipeline_all_models(
    video_path: Path,
    output_dir: Path,
    config: VideoPipelineConfig,
    keep_intermediates: bool = False
) -> Dict[str, Any]:
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
    logger.info(f"🚀 Starting video pipeline (all models): {video_path.name}")
    
    # Available models
    models = [
        "isnet-general-use",
        "u2net_human_seg", 
        "u2net",
        "u2netp",
        "u2net_cloth_seg",
        "silueta"
    ]
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate output filenames
    base_name = video_path.stem
    gif_path = output_dir / f"{base_name}.gif"
    spritesheet_path = output_dir / f"{base_name}_spritesheet.png"
    
    results = {
        'video_path': video_path,
        'gif_path': None,
        'spritesheet_path': None,
        'model_results': {},
        'intermediate_files': []
    }
    
    try:
        # Step 1: Video to GIF
        logger.info("📹 Step 1: Converting video to GIF...")
        video_to_gif(
            video_path, 
            gif_path, 
            fps=config.fps, 
            duration=config.duration,
            max_width=config.max_width,
            max_height=config.max_height
        )
        results['gif_path'] = gif_path
        results['intermediate_files'].append(gif_path)
        
        # Step 2: GIF to Spritesheet
        logger.info("🖼️ Step 2: Creating spritesheet from GIF...")
        
        # Parse grid
        try:
            cols, rows = map(int, config.grid.split('x'))
        except ValueError:
            raise ValueError(f"Invalid grid format: {config.grid}. Use format like '5x2'")
        
        # Extract frames from GIF
        frames = extract_gif_frames(gif_path, max_frames=config.frames)
        
        # Create spritesheet
        from .cli import _create_spritesheet
        _create_spritesheet(frames, cols, rows, spritesheet_path)
        results['spritesheet_path'] = spritesheet_path
        results['intermediate_files'].append(spritesheet_path)
        
        # Step 3: Background Removal with All Models
        logger.info("🎨 Step 3: Processing with all models...")
        
        for i, model in enumerate(models, 1):
            logger.info(f"   🔄 Processing with model {i}/{len(models)}: {model}")
            
            try:
                from .cli import _process_one
                processed_path = output_dir / f"{base_name}_{model}_processed.png"
                _process_one(spritesheet_path, processed_path, model_name=model)
                
                results['model_results'][model] = {
                    'path': processed_path,
                    'success': True,
                    'size': processed_path.stat().st_size
                }
                
                logger.info(f"   ✅ {model} completed successfully")
                
            except Exception as e:
                logger.error(f"   ❌ {model} failed: {e}")
                results['model_results'][model] = {
                    'path': None,
                    'success': False,
                    'error': str(e)
                }
        
        # Clean up intermediate files if requested
        if not keep_intermediates:
            logger.info("🧹 Cleaning up intermediate files...")
            for file_path in results['intermediate_files']:
                if file_path.exists():
                    file_path.unlink()
            results['intermediate_files'] = []
        
        successful_models = sum(1 for r in results['model_results'].values() if r['success'])
        logger.info(f"✅ Pipeline completed! {successful_models}/{len(models)} models successful")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        # Clean up on failure
        for file_path in results['intermediate_files']:
            if file_path.exists():
                file_path.unlink()
        raise


def analyze_video_for_pipeline(video_path: Path) -> Dict[str, Any]:
    """
    Analyze video and provide recommendations for pipeline processing.
    
    Args:
        video_path: Path to video file
        
    Returns:
        Dictionary with analysis and recommendations
    """
    logger.info(f"🔍 Analyzing video for pipeline: {video_path.name}")
    
    # Get basic video analysis
    analysis = analyze_video(video_path)
    
    # Add pipeline-specific recommendations
    duration = analysis['duration']
    fps = analysis['fps']
    size = analysis['size']
    
    # Recommend grid based on video characteristics
    if duration <= 2:
        recommended_grid = "3x2"  # 6 frames
    elif duration <= 4:
        recommended_grid = "4x2"  # 8 frames
    else:
        recommended_grid = "5x2"  # 10 frames
    
    # Recommend processing settings
    recommendations = {
        'fps': analysis['recommended_fps'],
        'duration': analysis['recommended_duration'],
        'grid': recommended_grid,
        'frames': analysis['recommended_frames'],
        'max_width': min(480, size[0]),
        'max_height': min(480, size[1]),
        'estimated_processing_time': f"{analysis['recommended_frames'] * 6 * 2:.0f} seconds"  # 6 models, ~2s per frame
    }
    
    return {
        'video_analysis': analysis,
        'recommendations': recommendations
    }
