"""
Refactored FastAPI application with cleaner, more maintainable code.
"""
import logging
import tempfile
import time
from pathlib import Path

import uvicorn
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from PIL import Image

from . import remove_bytes
from .api_utils import (
    AVAILABLE_MODELS,
    TempFileManager,
    calculate_auto_grid,
    cleanup_temp_dirs,
    cleanup_temp_files,
    create_error_response,
    create_success_response,
    encode_file_to_base64,
    encode_image_to_base64,
    parse_grid,
    save_uploaded_file,
)
from .model_utils import process_all_models, process_single_model
from .pipeline import (
    VideoPipelineConfig,
    process_video_pipeline,
    process_video_pipeline_all_models,
)
from .spritesheet_utils import analyze_spritesheet_dimensions
from .video import analyze_video, video_to_gif

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api = FastAPI(title="bgremove", version="0.1.0")


# Add request logging middleware
@api.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    logger.info(f"🌐 INCOMING REQUEST: {request.method} {request.url}")
    logger.info(f"   Headers: {dict(request.headers)}")
    logger.info(f"   Client: {request.client.host if request.client else 'unknown'}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"✅ RESPONSE: {response.status_code} - {process_time:.3f}s")
    
    return response


# Add CORS middleware
api.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api.get("/health")
def health():
    """Health check endpoint."""
    return {"ok": True}


@api.post("/analyze-spritesheet")
async def analyze_spritesheet_endpoint(file: UploadFile = File(...)):
    """Analyze spritesheet dimensions and suggest grid layouts."""
    temp_file_path = None
    try:
        # Save uploaded file
        temp_file_path = await save_uploaded_file(file, suffix=".png")
        
        # Load and analyze spritesheet
        with Image.open(temp_file_path) as spritesheet:
            analysis = analyze_spritesheet_dimensions(spritesheet)
        
        return create_success_response(analysis)
        
    except Exception as e:
        logger.error(f"Spritesheet analysis failed: {e}")
        raise create_error_response(str(e))
    finally:
        cleanup_temp_files(temp_file_path)


@api.post("/remove")
async def remove_endpoint(
    file: UploadFile = File(...),
    filename: str | None = None,
    model: str = Form("isnet-general-use"),
):
    """Remove background from uploaded image."""
    try:
        # Read file data
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="No file uploaded")
        
        # Process with background removal
        processed_data = remove_bytes(data, model_name=model)
        
        # Return as PNG with alpha
        name = filename or Path(file.filename or "output").stem
        headers = {"Content-Disposition": f'inline; filename="{name}.png"'}
        return Response(content=processed_data, media_type="image/png", headers=headers)
        
    except Exception as e:
        logger.error(f"Background removal failed: {e}")
        raise create_error_response(str(e))


@api.post("/remove-all-models")
async def remove_all_models_endpoint(file: UploadFile = File(...)):
    """Process image with all available models and return results."""
    try:
        # Read file data
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="No file uploaded")
        
        # Process with all models
        results = await process_all_models(data)
        
        return create_success_response({
            "original_filename": file.filename,
            "original_size": len(data),
            "models": results
        })
        
    except Exception as e:
        logger.error(f"Multi-model processing failed: {e}")
        raise create_error_response(str(e))


@api.post("/process/spritesheet")
async def process_spritesheet_endpoint(
    file: UploadFile = File(...),
    grid: str = Form("auto"),
    frames: int | None = Form(None),
    frameWidth: int | None = Form(None),
    frameHeight: int | None = Form(None),
    model: str = Form("isnet-general-use"),
):
    """
    Process spritesheet or GIF with background removal.
    
    - If GIF: extract frames, process them, and repack into a PNG spritesheet.
    - If spritesheet: slice by grid, process, and repack.
    """
    temp_file_path = None
    try:
        # Save uploaded file
        suffix = Path(file.filename or "").suffix.lower() or ".bin"
        temp_file_path = await save_uploaded_file(file, suffix=suffix)
        
        # Determine if input is GIF
        input_is_gif = (file.content_type == "image/gif") or suffix == ".gif"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            frames_dir = temp_dir_path / "frames"
            frames_dir.mkdir()
            
            if input_is_gif:
                # Process GIF
                from .api_utils import extract_gif_frames
                from .model_utils import process_frame_with_model
                
                # Extract frames
                extracted_frames = extract_gif_frames(temp_file_path, max_frames=frames)
                fw, fh = extracted_frames[0].size
                
                # Process each frame
                processed_frames = []
                for i, frame in enumerate(extracted_frames):
                    in_frame_path = frames_dir / f"in_{i:05d}.png"
                    out_frame_path = frames_dir / f"out_{i:05d}.png"
                    frame.save(in_frame_path)
                    
                    processed = await process_frame_with_model(
                        in_frame_path, out_frame_path, model
                    )
                    processed_frames.append(processed)
                
                # Determine final grid
                cols, rows = calculate_auto_grid(len(processed_frames))
                
            else:
                # Process spritesheet
                from .spritesheet_utils import process_spritesheet_frames
                
                # Parse grid
                cols, rows = parse_grid(grid)
                
                with Image.open(temp_file_path) as spritesheet:
                    # Extract frames
                    extracted_frames = process_spritesheet_frames(
                        spritesheet, cols, rows, frameWidth, frameHeight, frames
                    )
                    fw, fh = extracted_frames[0].size
                
                # Process each frame
                processed_frames = []
                for i, frame in enumerate(extracted_frames):
                    in_frame_path = frames_dir / f"in_{i:05d}.png"
                    out_frame_path = frames_dir / f"out_{i:05d}.png"
                    frame.save(in_frame_path)
                    
                    processed = await process_frame_with_model(
                        in_frame_path, out_frame_path, model
                    )
                    processed_frames.append(processed)
                
                # Use provided grid or auto-calculate
                if grid.lower() == "auto":
                    cols, rows = calculate_auto_grid(len(processed_frames))
            
            # Create final spritesheet
            from .api_utils import create_spritesheet
            combined = create_spritesheet(processed_frames, cols, rows, fw, fh)
            
            # Encode to base64
            spritesheet_data = encode_image_to_base64(combined)
            
            return create_success_response({
                "spritesheet": spritesheet_data,
                "spritesheet_mime": "image/png",
                "config": {
                    "input": file.filename,
                    "input_type": "gif" if input_is_gif else "spritesheet",
                    "grid": f"{cols}x{rows}" if cols and rows else "auto",
                    "frames": len(processed_frames),
                    "frameWidth": fw,
                    "frameHeight": fh,
                },
                "spritesheet_size": f"{combined.width}x{combined.height}",
            })
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Spritesheet processing failed: {e}")
        raise create_error_response(str(e))
    finally:
        cleanup_temp_files(temp_file_path)


@api.post("/process/spritesheet-all-models")
async def process_spritesheet_all_models_endpoint(
    file: UploadFile = File(...),
    grid: str = Form(...),
    frames: int | None = Form(None),
    frameWidth: int | None = Form(None),
    frameHeight: int | None = Form(None),
):
    """Process a spritesheet with all available models and return results."""
    temp_file_path = None
    try:
        # Save uploaded file
        temp_file_path = await save_uploaded_file(file, suffix=".png")
        
        # Parse grid
        cols, rows = parse_grid(grid)
        
        # Load spritesheet
        with Image.open(temp_file_path) as spritesheet:
            # Process with all models
            from .model_utils import process_spritesheet_all_models
            
            results = await process_spritesheet_all_models(
                spritesheet, cols, rows, frameWidth, frameHeight, frames
            )
        
        return create_success_response({
            "original_filename": file.filename,
            "original_size": temp_file_path.stat().st_size,
            "spritesheet_size": f"{spritesheet.width}x{spritesheet.height}",
            "grid": grid,
            "frames_processed": frames or (cols * rows),
            "frame_size": f"{spritesheet.width // cols}x{spritesheet.height // rows}",
            "models": results,
        })
        
    except Exception as e:
        logger.error(f"Multi-model spritesheet processing failed: {e}")
        raise create_error_response(str(e))
    finally:
        cleanup_temp_files(temp_file_path)


@api.post("/process/video-to-gif")
async def process_video_to_gif_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    fps: int = Form(10),
    duration: float | None = Form(None),
    max_width: int = Form(480),
    max_height: int = Form(480),
):
    """Convert video to GIF with custom settings."""
    temp_file_path = None
    result_path = None
    
    try:
        # Check if already a GIF
        file_extension = Path(file.filename or "").suffix.lower()
        is_gif = file_extension == ".gif" or file.content_type == "image/gif"
        
        if is_gif:
            # Return GIF as-is
            content = await file.read()
            with TempFileManager(suffix=".gif") as temp_gif:
                temp_gif.write_bytes(content)
                result_path = temp_gif
        else:
            # Convert video to GIF
            temp_file_path = await save_uploaded_file(file)
            result_path = temp_file_path.with_suffix(".gif")
            
            video_to_gif(
                temp_file_path,
                result_path,
                fps=fps,
                duration=duration,
                max_width=max_width,
                max_height=max_height,
            )
        
        # Schedule cleanup
        background_tasks.add_task(
            lambda: result_path.unlink() if result_path and result_path.exists() else None
        )
        
        return FileResponse(
            path=result_path,
            media_type="image/gif",
            filename=f"{Path(file.filename).stem}.gif"
        )
        
    except Exception as e:
        logger.error(f"Video to GIF conversion failed: {e}")
        cleanup_temp_files(temp_file_path, result_path)
        raise create_error_response(f"Video processing failed: {str(e)}")


@api.post("/analyze/video")
async def analyze_video_endpoint(file: UploadFile = File(...)):
    """Analyze video and provide processing recommendations."""
    temp_file_path = None
    try:
        # Save uploaded file
        temp_file_path = await save_uploaded_file(file)
        
        # Analyze video
        analysis = analyze_video(temp_file_path)
        
        return create_success_response({
            "filename": file.filename,
            "analysis": analysis
        })
        
    except Exception as e:
        logger.error(f"Video analysis failed: {e}")
        raise create_error_response(f"Video analysis failed: {str(e)}")
    finally:
        cleanup_temp_files(temp_file_path)


@api.post("/process/video-pipeline")
async def process_video_pipeline_endpoint(
    file: UploadFile = File(...),
    fps: int = Form(10),
    duration: float | None = Form(None),
    grid: str = Form("5x2"),
    frames: int | None = Form(None),
    model: str = Form("isnet-general-use"),
    all_models: bool = Form(False),
    keep_intermediates: bool = Form(False),
):
    """Complete video processing pipeline: Video → GIF → Spritesheet → Background Removal."""
    temp_file_path = None
    output_dir = None
    
    try:
        # Save uploaded file
        temp_file_path = await save_uploaded_file(file)
        
        # Create output directory
        output_dir = Path(tempfile.mkdtemp())
        
        # Configure pipeline
        config = VideoPipelineConfig(
            fps=fps, duration=duration, grid=grid, frames=frames, model=model
        )
        
        # Run pipeline
        if all_models:
            results = process_video_pipeline_all_models(
                temp_file_path, output_dir, config, keep_intermediates
            )
            
            # Prepare response data
            response_data = {
                "gif_path": str(results["gif_path"]) if results["gif_path"] else None,
                "spritesheet_path": str(results["spritesheet_path"]) if results["spritesheet_path"] else None,
                "model_results": {},
            }
            
            # Read model results
            for model_name, result in results["model_results"].items():
                if result["success"] and result["path"] and result["path"].exists():
                    content = encode_file_to_base64(result["path"])
                    response_data["model_results"][model_name] = {
                        "success": True,
                        "data": content,
                        "size": len(content),
                    }
                else:
                    response_data["model_results"][model_name] = {
                        "success": False,
                        "error": result.get("error", "Unknown error"),
                    }
        else:
            results = process_video_pipeline(temp_file_path, output_dir, config, keep_intermediates)
            
            # Read result files
            gif_data = None
            spritesheet_data = None
            processed_data = None
            
            if results["gif_path"] and results["gif_path"].exists():
                gif_data = encode_file_to_base64(results["gif_path"])
            
            if results["spritesheet_path"] and results["spritesheet_path"].exists():
                spritesheet_data = encode_file_to_base64(results["spritesheet_path"])
            
            if results["processed_path"] and results["processed_path"].exists():
                processed_data = encode_file_to_base64(results["processed_path"])
            
            response_data = {
                "gif_data": gif_data,
                "spritesheet_data": spritesheet_data,
                "processed_data": processed_data,
            }
        
        return create_success_response(response_data, filename=file.filename)
        
    except Exception as e:
        logger.error(f"Video pipeline failed: {e}")
        raise create_error_response(f"Video pipeline failed: {str(e)}")
    finally:
        cleanup_temp_files(temp_file_path)
        if not keep_intermediates:
            cleanup_temp_dirs(output_dir)


@api.post("/process/gif-to-spritesheet")
async def process_gif_to_spritesheet_endpoint(
    file: UploadFile = File(...),
    grid: str = Form(...),
    frames: int | None = Form(None),
    frameWidth: int | None = Form(None),
    frameHeight: int | None = Form(None),
):
    """Convert an animated GIF to a spritesheet with background removal."""
    temp_file_path = None
    try:
        # Save uploaded file
        temp_file_path = await save_uploaded_file(file, suffix=".gif")
        
        # Parse grid
        cols, rows = parse_grid(grid)
        
        # Normalize frames parameter
        if frames is not None:
            try:
                frames = int(frames)
                if frames <= 0:
                    frames = None
            except (ValueError, TypeError):
                frames = None
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "frames"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract frames
            from .video import extract_gif_frames_to_dir
            frame_paths = extract_gif_frames_to_dir(
                gif_path=temp_file_path,
                output_dir=output_dir,
                max_frames=frames,
            )
            
            if not frame_paths:
                raise HTTPException(
                    status_code=400, 
                    detail="No frames could be extracted from the GIF"
                )
            
            # Process each frame
            from .model_utils import process_frame_with_model
            processed_frames = []
            
            for i, frame_path in enumerate(frame_paths):
                try:
                    processed_path = output_dir / f"processed_{frame_path.name}"
                    processed_frame = await process_frame_with_model(
                        frame_path, processed_path
                    )
                    processed_frames.append(processed_frame)
                except Exception as e:
                    logger.error(f"Error processing frame {i + 1}: {e}")
                    processed_frames.append(Image.open(frame_path).convert("RGBA"))
            
            if not processed_frames:
                raise HTTPException(
                    status_code=500, 
                    detail="No frames were processed successfully"
                )
            
            # Create spritesheet
            frame_w, frame_h = processed_frames[0].size
            if frameWidth and frameHeight:
                frame_w, frame_h = int(frameWidth), int(frameHeight)
                processed_frames = [im.resize((frame_w, frame_h)) for im in processed_frames]
            
            from .api_utils import create_spritesheet
            sheet = create_spritesheet(processed_frames, cols, rows, frame_w, frame_h)
            
            # Encode to base64
            spritesheet_data = encode_image_to_base64(sheet)
            
            return create_success_response({
                "spritesheet": spritesheet_data,
                "config": {
                    "grid": grid,
                    "frames": len(processed_frames),
                    "frameWidth": frame_w,
                    "frameHeight": frame_h,
                },
                "frames_processed": len(processed_frames),
                "spritesheet_size": f"{sheet.width}x{sheet.height}",
                "gif_frames": len(frame_paths),
            })
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GIF to spritesheet conversion failed: {e}")
        raise create_error_response(f"GIF to spritesheet conversion failed: {str(e)}")
    finally:
        cleanup_temp_files(temp_file_path)


def serve(host: str = "127.0.0.1", port: int = 8002):
    """Start the API server."""
    uvicorn.run(api, host=host, port=port)
