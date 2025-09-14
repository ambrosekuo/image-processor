"""
Model processing utilities for background removal.
"""
import asyncio
import base64
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image

from . import remove_bytes
from .api_utils import AVAILABLE_MODELS, ensure_rgba
from .cli import _process_one

logger = logging.getLogger(__name__)


async def process_single_model(
    image_data: bytes,
    model_name: str
) -> Dict[str, any]:
    """
    Process image with a single model.
    
    Args:
        image_data: Image data as bytes
        model_name: Name of model to use
        
    Returns:
        Dictionary with processing results
    """
    try:
        processed_data = remove_bytes(image_data, model_name=model_name)
        
        return {
            "success": True,
            "data": base64.b64encode(processed_data).decode("utf-8"),
            "size": len(processed_data),
        }
    except Exception as e:
        logger.error(f"Model {model_name} failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def process_all_models(
    image_data: bytes,
    models: Optional[List[str]] = None
) -> Dict[str, Dict[str, any]]:
    """
    Process image with all available models.
    
    Args:
        image_data: Image data as bytes
        models: List of models to use (defaults to all available)
        
    Returns:
        Dictionary with results for each model
    """
    if models is None:
        models = AVAILABLE_MODELS
    
    results = {}
    
    for model in models:
        logger.info(f"Processing with model: {model}")
        result = await process_single_model(image_data, model)
        results[model] = result
    
    return results


async def process_frame_with_model(
    frame_path: Path,
    output_path: Path,
    model_name: str = "isnet-general-use"
) -> Image.Image:
    """
    Process a single frame with background removal.
    
    Args:
        frame_path: Path to input frame
        output_path: Path to save processed frame
        model_name: Model to use for processing
        
    Returns:
        Processed frame as PIL Image
    """
    try:
        processed_path = await asyncio.get_running_loop().run_in_executor(
            None, _process_one, frame_path, output_path, False, model_name
        )
        with Image.open(processed_path) as im:
            return ensure_rgba(im.copy())
    except Exception as e:
        logger.warning(f"Frame processing failed with {model_name}: {e}")
        # Return original frame if processing fails
        with Image.open(frame_path) as im:
            return ensure_rgba(im.copy())


def process_spritesheet_with_model(
    spritesheet: Image.Image,
    cols: int,
    rows: int,
    model_name: str,
    frame_width: Optional[int] = None,
    frame_height: Optional[int] = None,
    max_frames: Optional[int] = None
) -> Tuple[List[Image.Image], Dict[str, any]]:
    """
    Process entire spritesheet with a single model.
    
    Args:
        spritesheet: PIL Image of spritesheet
        cols: Number of columns
        rows: Number of rows
        model_name: Model to use for processing
        frame_width: Override frame width
        frame_height: Override frame height
        max_frames: Maximum frames to process
        
    Returns:
        Tuple of (processed_frames, metadata)
    """
    from .spritesheet_utils import process_spritesheet_frames
    
    # Extract frames
    frames = process_spritesheet_frames(
        spritesheet, cols, rows, frame_width, frame_height, max_frames
    )
    
    # Process each frame
    processed_frames = []
    for i, frame in enumerate(frames):
        try:
            # Save frame temporarily
            temp_frame_path = Path(f"temp_frame_{i}.png")
            frame.save(temp_frame_path)
            
            # Process frame
            processed_frame = process_frame_with_model(
                temp_frame_path, 
                Path(f"temp_processed_{i}.png"),
                model_name
            )
            processed_frames.append(processed_frame)
            
            # Clean up temp files
            temp_frame_path.unlink(missing_ok=True)
            Path(f"temp_processed_{i}.png").unlink(missing_ok=True)
            
        except Exception as e:
            logger.error(f"Failed to process frame {i}: {e}")
            processed_frames.append(frame)  # Use original frame
    
    metadata = {
        "frames_processed": len(processed_frames),
        "model_used": model_name,
        "total_frames": len(frames)
    }
    
    return processed_frames, metadata


async def process_spritesheet_all_models(
    spritesheet: Image.Image,
    cols: int,
    rows: int,
    frame_width: Optional[int] = None,
    frame_height: Optional[int] = None,
    max_frames: Optional[int] = None,
    models: Optional[List[str]] = None
) -> Dict[str, Dict[str, any]]:
    """
    Process spritesheet with all available models.
    
    Args:
        spritesheet: PIL Image of spritesheet
        cols: Number of columns
        rows: Number of rows
        frame_width: Override frame width
        frame_height: Override frame height
        max_frames: Maximum frames to process
        models: List of models to use
        
    Returns:
        Dictionary with results for each model
    """
    if models is None:
        models = AVAILABLE_MODELS
    
    from .spritesheet_utils import process_spritesheet_frames, create_spritesheet_from_frames
    
    # Extract frames once
    frames = process_spritesheet_frames(
        spritesheet, cols, rows, frame_width, frame_height, max_frames
    )
    
    results = {}
    
    for model in models:
        logger.info(f"Processing spritesheet with model: {model}")
        try:
            # Process frames with this model
            processed_frames = []
            for i, frame in enumerate(frames):
                try:
                    # Save frame temporarily
                    temp_frame_path = Path(f"temp_frame_{model}_{i}.png")
                    frame.save(temp_frame_path)
                    
                    # Process frame
                    processed_frame = await process_frame_with_model(
                        temp_frame_path,
                        Path(f"temp_processed_{model}_{i}.png"),
                        model
                    )
                    processed_frames.append(processed_frame)
                    
                    # Clean up temp files
                    temp_frame_path.unlink(missing_ok=True)
                    Path(f"temp_processed_{model}_{i}.png").unlink(missing_ok=True)
                    
                except Exception as e:
                    logger.error(f"Failed to process frame {i} with {model}: {e}")
                    processed_frames.append(frame)  # Use original frame
            
            if processed_frames:
                # Create combined spritesheet for this model
                combined_spritesheet = create_spritesheet_from_frames(
                    processed_frames, cols, rows, frame_width, frame_height
                )
                
                # Convert to base64
                from .api_utils import encode_image_to_base64
                spritesheet_data = encode_image_to_base64(combined_spritesheet)
                
                results[model] = {
                    "success": True,
                    "data": spritesheet_data,
                    "size": len(spritesheet_data),
                    "frames_processed": len(processed_frames),
                }
            else:
                results[model] = {
                    "success": False,
                    "error": "No frames were processed successfully"
                }
                
        except Exception as e:
            logger.error(f"Model {model} failed: {e}")
            results[model] = {
                "success": False,
                "error": str(e)
            }
    
    return results
