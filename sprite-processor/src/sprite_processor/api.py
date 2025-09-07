from pathlib import Path
from typing import Optional, List,Tuple
import tempfile
import shutil
import logging
import time
import base64

from fastapi import FastAPI, File, HTTPException, UploadFile, Form, Request, BackgroundTasks
from fastapi.responses import Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from . import remove_bytes
from .video import video_to_gif, analyze_video
from .pipeline import process_video_pipeline, process_video_pipeline_all_models, VideoPipelineConfig
from .cli import _process_one
from PIL import Image, ImageSequence
import asyncio
import base64
import math
import os
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api = FastAPI(title="bgremove", version="0.1.0")

# Add request logging middleware
@api.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log incoming request
    logger.info(f"🌐 INCOMING REQUEST: {request.method} {request.url}")
    logger.info(f"   Headers: {dict(request.headers)}")
    logger.info(f"   Client: {request.client.host if request.client else 'unknown'}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"✅ RESPONSE: {response.status_code} - {process_time:.3f}s")
    
    return response

# Add CORS middleware
api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api.get("/health")
def health():
    return {"ok": True}


@api.post("/analyze-spritesheet")
async def analyze_spritesheet(file: UploadFile = File(...)):
    """Analyze spritesheet dimensions and suggest grid layouts"""
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    try:
        from PIL import Image
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # Load spritesheet
        spritesheet = Image.open(tmp_file_path)
        width, height = spritesheet.size
        
        # Find common divisors for suggested grid layouts
        def find_divisors(n):
            divisors = []
            for i in range(1, min(n, 20) + 1):  # Limit to reasonable grid sizes
                if n % i == 0:
                    divisors.append(i)
            return divisors
        
        width_divisors = find_divisors(width)
        height_divisors = find_divisors(height)
        
        # Generate suggested layouts
        suggestions = []
        for w in width_divisors[:5]:  # Top 5 width divisors
            for h in height_divisors[:5]:  # Top 5 height divisors
                if w * h <= 50:  # Reasonable total frame count
                    frame_width = width // w
                    frame_height = height // h
                    suggestions.append({
                        "grid": f"{w}x{h}",
                        "frame_size": f"{frame_width}x{frame_height}",
                        "total_frames": w * h
                    })
        
        # Sort by total frames
        suggestions.sort(key=lambda x: x["total_frames"])
        
        return {
            "spritesheet_size": f"{width}x{height}",
            "suggested_layouts": suggestions[:10],  # Top 10 suggestions
            "width_divisors": width_divisors,
            "height_divisors": height_divisors
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary file
        try:
            Path(tmp_file_path).unlink()
        except:
            pass


@api.post("/remove")
async def remove_endpoint(
    file: UploadFile = File(...), 
    filename: Optional[str] = None,
    model: str = Form("isnet-general-use")
):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    data = await file.read()
    try:
        cut = remove_bytes(data, model_name=model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # Return as PNG with alpha
    name = filename or Path(file.filename or "output").stem
    headers = {"Content-Disposition": f'inline; filename="{name}.png"'}
    return Response(content=cut, media_type="image/png", headers=headers)


@api.post("/remove-all-models")
async def remove_all_models_endpoint(file: UploadFile = File(...)):
    """Process image with all available models and return results"""
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    data = await file.read()
    models = [
        "isnet-general-use",
        "u2net_human_seg", 
        "u2net",
        "u2netp",
        "u2net_cloth_seg",
        "silueta"
    ]
    
    results = {}
    
    for model in models:
        try:
            processed_data = remove_bytes(data, model_name=model)
            # Convert to base64 for JSON response
            import base64
            results[model] = {
                "success": True,
                "data": base64.b64encode(processed_data).decode('utf-8'),
                "size": len(processed_data)
            }
        except Exception as e:
            results[model] = {
                "success": False,
                "error": str(e)
            }
    
    return {
        "original_filename": file.filename,
        "original_size": len(data),
        "models": results
    }


@api.post("/process/spritesheet-all-models")
async def process_spritesheet_all_models(
    file: UploadFile = File(...),
    grid: str = Form(...),
    frames: Optional[int] = Form(None),
    frameWidth: Optional[int] = Form(None),
    frameHeight: Optional[int] = Form(None)
):
    """Process a spritesheet with all available models and return results"""
    logger.info(f"🎬 SPRITESHEET ALL-MODELS REQUEST STARTED")
    logger.info(f"   File: {file.filename} ({file.size if hasattr(file, 'size') else 'unknown'} bytes)")
    logger.info(f"   Grid: {grid}")
    logger.info(f"   Frames: {frames}")
    logger.info(f"   Frame dimensions: {frameWidth}x{frameHeight}")
    
    if not file:
        logger.error("❌ No file uploaded")
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    try:
        # Parse grid (e.g., "5x2")
        if 'x' not in grid:
            logger.error("❌ Invalid grid format")
            raise HTTPException(status_code=400, detail="Grid must be in format 'colsxrows' (e.g., '5x2')")
        
        cols, rows = map(int, grid.split('x'))
        logger.info(f"   Parsed grid: {cols} columns x {rows} rows")
        
        # Save uploaded file temporarily
        logger.info("   Saving uploaded file temporarily...")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        logger.info(f"   File saved to: {tmp_file_path} ({len(content)} bytes)")
        
        # Create temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "frames"
            output_dir.mkdir()
            
            # Process spritesheet using existing CLI logic
            from PIL import Image
            
            # Load spritesheet
            spritesheet = Image.open(tmp_file_path)
            spritesheet_width, spritesheet_height = spritesheet.size
            
            # Calculate frame dimensions
            if frameWidth and frameHeight:
                frame_width = frameWidth
                frame_height = frameHeight
            else:
                # Use exact division to avoid rounding issues
                frame_width = spritesheet_width // cols
                frame_height = spritesheet_height // rows
            
            # Calculate actual frames that fit
            frames_per_row = spritesheet_width // frame_width
            frames_per_col = spritesheet_height // frame_height
            total_frames = frames_per_row * frames_per_col
            
            # Validate that we can fit the requested grid
            if frames_per_row < cols:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Spritesheet width ({spritesheet_width}) cannot fit {cols} frames of width {frame_width}. Maximum frames per row: {frames_per_row}"
                )
            if frames_per_col < rows:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Spritesheet height ({spritesheet_height}) cannot fit {rows} frames of height {frame_height}. Maximum frames per column: {frames_per_col}"
                )
            max_frames = frames or total_frames
            
            # Available models
            models = [
                "isnet-general-use",
                "u2net_human_seg", 
                "u2net",
                "u2netp",
                "u2net_cloth_seg",
                "silueta"
            ]
            
            logger.info(f"   Processing with {len(models)} models: {', '.join(models)}")
            results = {}
            
            for i, model in enumerate(models, 1):
                logger.info(f"   🔄 Processing model {i}/{len(models)}: {model}")
                try:
                    # Process frames with this model
                    processed_frames = []
                    frame_count = 0
                    
                    # Process frames
                    for row in range(frames_per_col):
                        for col in range(frames_per_row):
                            if frame_count >= max_frames:
                                break
                            
                            # Calculate crop coordinates
                            left = col * frame_width
                            top = row * frame_height
                            right = left + frame_width
                            bottom = top + frame_height
                            
                            # Crop frame
                            frame = spritesheet.crop((left, top, right, bottom))
                            
                            # Save temporary frame
                            frame_path = output_dir / f"frame_{row:03d}_{col:03d}_{model}.png"
                            frame.save(frame_path)
                            
                            # Process frame with specific model
                            try:
                                logger.info(f"   Processing frame {frame_count + 1} with model: {model}")
                                processed_path = _process_one(frame_path, output_dir / f"frame_{row:03d}_{col:03d}_{model}_processed.png", model_name=model)
                                processed_frame = Image.open(processed_path)
                                processed_frames.append(processed_frame)
                                logger.info(f"   Frame {frame_count + 1} processed successfully with {model}")
                            except Exception as e:
                                logger.error(f"Error processing frame {frame_count + 1} with {model}: {e}")
                                # Use original frame if processing fails
                                processed_frames.append(frame)
                            
                            frame_count += 1
                        
                        if frame_count >= max_frames:
                            break
                    
                    # Create combined spritesheet for this model
                    if processed_frames:
                        combined_width = frames_per_row * frame_width
                        combined_height = frames_per_col * frame_height
                        combined_image = Image.new('RGBA', (combined_width, combined_height), (0, 0, 0, 0))
                        
                        for i, frame in enumerate(processed_frames):
                            row = i // frames_per_row
                            col = i % frames_per_row
                            x = col * frame_width
                            y = row * frame_height
                            combined_image.paste(frame, (x, y))
                        
                        # Convert to bytes
                        import io
                        img_bytes = io.BytesIO()
                        combined_image.save(img_bytes, format='PNG')
                        img_bytes.seek(0)
                        
                        # Convert to base64 for JSON response
                        import base64
                        results[model] = {
                            "success": True,
                            "data": base64.b64encode(img_bytes.getvalue()).decode('utf-8'),
                            "size": len(img_bytes.getvalue()),
                            "frames_processed": len(processed_frames)
                        }
                        logger.info(f"   ✅ {model} completed successfully ({len(processed_frames)} frames, {len(img_bytes.getvalue())} bytes)")
                    else:
                        results[model] = {
                            "success": False,
                            "error": "No frames were processed successfully"
                        }
                        logger.warning(f"   ⚠️ {model} failed: No frames were processed successfully")
                        
                except Exception as e:
                    results[model] = {
                        "success": False,
                        "error": str(e)
                    }
                    logger.error(f"   ❌ {model} failed with error: {str(e)}")
            
            successful_models = sum(1 for r in results.values() if r.get("success", False))
            logger.info(f"🎉 SPRITESHEET ALL-MODELS COMPLETED: {successful_models}/{len(models)} models successful")
            
            return {
                "original_filename": file.filename,
                "original_size": len(content),
                "spritesheet_size": f"{spritesheet_width}x{spritesheet_height}",
                "grid": grid,
                "frames_processed": max_frames,
                "frame_size": f"{frame_width}x{frame_height}",
                "models": results
            }
    
    except Exception as e:
        logger.error(f"❌ SPRITESHEET ALL-MODELS FAILED: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary file
        try:
            Path(tmp_file_path).unlink()
            logger.info("   🧹 Cleaned up temporary file")
        except:
            logger.warning("   ⚠️ Failed to clean up temporary file")

def _ensure_rgba(im: Image.Image) -> Image.Image:
    """
    Convert paletted/GIF frames into RGBA properly preserving transparency.
    """
    if im.mode == "RGBA":
        return im
    if im.mode in ("P", "L", "RGB", "LA"):
        # Use a transparent background if possible
        bg = Image.new("RGBA", im.size, (0, 0, 0, 0))
        bg.paste(im, (0, 0))
        return bg
    return im.convert("RGBA")

def _parse_grid(grid: str) -> Tuple[int, int]:
    if grid.lower() == "auto":
        return (0, 0)  # sentinel for auto layout
    if "x" not in grid:
        raise HTTPException(status_code=400, detail="Grid must be 'colsxrows' (e.g., '5x2') or 'auto'.")
    cols, rows = map(int, grid.lower().split("x"))
    if cols <= 0 or rows <= 0:
        raise HTTPException(status_code=400, detail="Grid numbers must be positive integers.")
    return cols, rows

def _auto_grid(num_frames: int) -> Tuple[int, int]:
    """
    Choose a near-square grid for the given number of frames.
    """
    cols = int(math.ceil(math.sqrt(num_frames)))
    rows = int(math.ceil(num_frames / cols))
    return cols, rows

async def _maybe_process_frame(frame_path: Path, out_path: Path, model_name: str = "isnet-general-use") -> Image.Image:
    """
    Try processing a single frame with _process_one; on failure, return the original.
    """
    try:
        processed_path = await asyncio.get_running_loop().run_in_executor(
            None, _process_one, frame_path, out_path, False, model_name
        )
        with Image.open(processed_path) as im:
            return _ensure_rgba(im.copy())
    except Exception:
        with Image.open(frame_path) as im:
            return _ensure_rgba(im.copy())

@api.post("/process/spritesheet")
async def process_spritesheet(
    file: UploadFile = File(...),
    grid: str = Form("auto"),  # "auto" or "COLSxROWS" when input is an existing sheet
    frames: Optional[int] = Form(None),
    frameWidth: Optional[int] = Form(None),
    frameHeight: Optional[int] = Form(None),
    model: str = Form("isnet-general-use"),
):
    """
    Upload a GIF or an image spritesheet.
    - If GIF: extract frames, process them, and repack into a PNG spritesheet.
    - If spritesheet: slice by grid (or auto-slice based on provided frameWidth/Height), process, and repack.
    Returns base64-encoded PNG spritesheet and metadata.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    tmp_file_path: Optional[str] = None
    try:
        # Save the upload
        suffix = Path(file.filename or "").suffix.lower() or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Uploaded file is empty")
            tmp.write(content)
            tmp_file_path = tmp.name

        # Workspace
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            frames_dir = temp_dir_path / "frames"
            frames_dir.mkdir()

            input_is_gif = (file.content_type == "image/gif") or suffix == ".gif"

            extracted_frames: List[Image.Image] = []
            fw: Optional[int] = None
            fh: Optional[int] = None

            if input_is_gif:
                # --------- GIF branch: decompose frames ----------
                with Image.open(tmp_file_path) as gif:
                    # Some GIFs have varying disposal methods; convert each to RGBA canvas
                    for idx, frame in enumerate(ImageSequence.Iterator(gif)):
                        rgba = _ensure_rgba(frame.convert("RGBA"))
                        extracted_frames.append(rgba.copy())
                        if frames and len(extracted_frames) >= frames:
                            break
                if not extracted_frames:
                    raise HTTPException(status_code=400, detail="GIF has no frames")
                fw, fh = extracted_frames[0].size

            else:
                # --------- Spritesheet branch: slice by grid or frame size ----------
                cols, rows = _parse_grid(grid)
                with Image.open(tmp_file_path) as sheet:
                    sheet = _ensure_rgba(sheet.convert("RGBA"))
                    sw, sh = sheet.size

                    # Determine frame size
                    if frameWidth and frameHeight:
                        fw, fh = int(frameWidth), int(frameHeight)
                        if fw <= 0 or fh <= 0:
                            raise HTTPException(status_code=400, detail="frameWidth and frameHeight must be > 0")
                        frames_per_row = sw // fw
                        frames_per_col = sh // fh
                    else:
                        # If explicit grid provided, compute from it; if auto, try square-ish frame guess
                        if cols and rows:
                            fw = sw // cols
                            fh = sh // rows
                            frames_per_row = cols
                            frames_per_col = rows
                        else:
                            # Auto: try to infer by making square frames (fallback to 1x1)
                            # Here, we just treat the full image as a single frame if no size given.
                            fw, fh = sw, sh
                            frames_per_row = 1
                            frames_per_col = 1

                    # Validate and extract
                    if fw <= 0 or fh <= 0:
                        raise HTTPException(status_code=400, detail="Computed frame size is invalid.")
                    frames_per_row = sw // fw
                    frames_per_col = sh // fh
                    total_possible = frames_per_row * frames_per_col
                    max_take = min(frames or total_possible, total_possible)

                    count = 0
                    for r in range(frames_per_col):
                        for c in range(frames_per_row):
                            if count >= max_take:
                                break
                            left = c * fw
                            top = r * fh
                            right = left + fw
                            bottom = top + fh
                            cropped = sheet.crop((left, top, right, bottom))
                            extracted_frames.append(_ensure_rgba(cropped))
                            count += 1
                        if count >= max_take:
                            break

                if not extracted_frames:
                    raise HTTPException(status_code=500, detail="No frames could be extracted from the spritesheet.")

            # ---- Process each frame (background removal, etc.) ----
            processed_frames: List[Image.Image] = []
            for i, img in enumerate(extracted_frames):
                # Save to disk for your _process_one()
                in_frame_path = frames_dir / f"in_{i:05d}.png"
                out_frame_path = frames_dir / f"out_{i:05d}.png"
                img.save(in_frame_path)
                processed = await _maybe_process_frame(in_frame_path, out_frame_path, model)
                processed_frames.append(processed)

            # ---- Determine final grid ----
            if grid.lower() == "auto" or input_is_gif:
                cols, rows = _auto_grid(len(processed_frames))
            else:
                cols, rows = _parse_grid(grid)

            # Safety if user gave a tiny grid
            total_slots = cols * rows if cols and rows else len(processed_frames)
            if total_slots < len(processed_frames):
                # Expand to fit
                cols, rows = _auto_grid(len(processed_frames))

            # ---- Assemble combined spritesheet ----
            fw = fw or processed_frames[0].width
            fh = fh or processed_frames[0].height
            combined_w = cols * fw
            combined_h = rows * fh
            combined = Image.new("RGBA", (combined_w, combined_h), (0, 0, 0, 0))

            for i, frame in enumerate(processed_frames):
                if i >= cols * rows:
                    break
                r = i // cols
                c = i % cols
                combined.paste(frame, (c * fw, r * fh))

            # ---- Encode to base64 PNG ----
            combined_path = frames_dir / "combined_spritesheet.png"
            combined.save(combined_path)
            with open(combined_path, "rb") as f:
                b64_png = base64.b64encode(f.read()).decode("utf-8")

            return {
                "success": True,
                "spritesheet": b64_png,
                "spritesheet_mime": "image/png",
                "config": {
                    "input": file.filename,
                    "input_type": "gif" if input_is_gif else "spritesheet",
                    "grid": f"{cols}x{rows}" if cols and rows else "auto",
                    "frames": len(processed_frames),
                    "frameWidth": fw,
                    "frameHeight": fh,
                },
                "spritesheet_size": f"{combined_w}x{combined_h}",
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except Exception:
                pass



@api.post("/process/video-to-gif")
async def process_video_to_gif(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    fps: int = Form(10),
    duration: Optional[float] = Form(None),
    max_width: int = Form(480),
    max_height: int = Form(480)
):
    """Convert video to GIF with custom settings."""
    logger.info(f"🎬 VIDEO TO GIF REQUEST STARTED")
    logger.info(f"   File: {file.filename} ({file.size} bytes)")
    logger.info(f"   Settings: {fps} FPS, {duration}s duration, {max_width}x{max_height} max size")
    
    try:
        # Check if the uploaded file is already a GIF
        file_extension = Path(file.filename or "").suffix.lower()
        is_gif = file_extension == ".gif" or file.content_type == "image/gif"
        
        if is_gif:
            logger.info(f"   Input is already a GIF, returning as-is")
            # For GIF files, just return the file as-is
            content = await file.read()
            
            # Create a temporary file for the response
            with tempfile.NamedTemporaryFile(delete=False, suffix='.gif') as temp_file:
                temp_file.write(content)
                temp_file_path = Path(temp_file.name)
            
            # Schedule cleanup of temp file after response is sent
            background_tasks.add_task(lambda: temp_file_path.unlink() if temp_file_path.exists() else None)
            
            return FileResponse(
                path=temp_file_path,
                media_type="image/gif",
                filename=f"{Path(file.filename).stem}.gif"
            )
        
        # For actual video files, proceed with conversion
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = Path(temp_file.name)
        
        logger.info(f"   File saved to: {temp_file_path}")
        
        # Generate output path
        output_path = temp_file_path.with_suffix('.gif')
        
        # Convert video to GIF
        logger.info(f"   Converting video to GIF...")
        result_path = video_to_gif(
            temp_file_path, 
            output_path, 
            fps=fps, 
            duration=duration,
            max_width=max_width,
            max_height=max_height
        )
        
        logger.info(f"✅ VIDEO TO GIF COMPLETED: {result_path.stat().st_size} bytes")
        
        # Clean up input file
        temp_file_path.unlink()
        
        # Schedule cleanup of result file after response is sent
        background_tasks.add_task(lambda: result_path.unlink() if result_path.exists() else None)
        
        # Use FileResponse to avoid header conflicts
        return FileResponse(
            path=result_path,
            media_type="image/gif",
            filename=f"{Path(file.filename).stem}.gif"
        )
        
    except Exception as e:
        logger.error(f"❌ VIDEO TO GIF FAILED: {e}")
        # Clean up on error
        try:
            if 'temp_file_path' in locals() and temp_file_path.exists():
                temp_file_path.unlink()
            if 'result_path' in locals() and result_path.exists():
                result_path.unlink()
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Video processing failed: {str(e)}")


@api.post("/analyze/video")
async def analyze_video_endpoint(file: UploadFile = File(...)):
    """Analyze video and provide processing recommendations."""
    logger.info(f"🔍 VIDEO ANALYSIS REQUEST STARTED")
    logger.info(f"   File: {file.filename} ({file.size} bytes)")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = Path(temp_file.name)
        
        logger.info(f"   File saved to: {temp_file_path}")
        
        # Analyze video
        logger.info(f"   Analyzing video...")
        analysis = analyze_video(temp_file_path)
        
        # Clean up temporary file
        temp_file_path.unlink()
        
        logger.info(f"✅ VIDEO ANALYSIS COMPLETED")
        
        return {
            "filename": file.filename,
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"❌ VIDEO ANALYSIS FAILED: {e}")
        # Clean up on error
        try:
            if 'temp_file_path' in locals() and temp_file_path.exists():
                temp_file_path.unlink()
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Video analysis failed: {str(e)}")


@api.post("/process/video-pipeline")
async def process_video_pipeline_endpoint(
    file: UploadFile = File(...),
    fps: int = Form(10),
    duration: Optional[float] = Form(None),
    grid: str = Form("5x2"),
    frames: Optional[int] = Form(None),
    model: str = Form("isnet-general-use"),
    all_models: bool = Form(False),
    keep_intermediates: bool = Form(False)
):
    """Complete video processing pipeline: Video → GIF → Spritesheet → Background Removal."""
    logger.info(f"🚀 VIDEO PIPELINE REQUEST STARTED")
    logger.info(f"   File: {file.filename} ({file.size} bytes)")
    logger.info(f"   Settings: {fps} FPS, {duration}s duration, {grid} grid, {frames} frames, {model} model")
    logger.info(f"   All models: {all_models}, Keep intermediates: {keep_intermediates}")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = Path(temp_file.name)
        
        logger.info(f"   File saved to: {temp_file_path}")
        
        # Create output directory
        output_dir = Path(tempfile.mkdtemp())
        logger.info(f"   Output directory: {output_dir}")
        
        # Configure pipeline
        config = VideoPipelineConfig(
            fps=fps,
            duration=duration,
            grid=grid,
            frames=frames,
            model=model
        )
        
        # Run pipeline
        if all_models:
            logger.info(f"   Running pipeline with all models...")
            results = process_video_pipeline_all_models(temp_file_path, output_dir, config, keep_intermediates)
            
            # Prepare response data
            response_data = {
                "success": True,
                "filename": file.filename,
                "gif_path": str(results['gif_path']) if results['gif_path'] else None,
                "spritesheet_path": str(results['spritesheet_path']) if results['spritesheet_path'] else None,
                "model_results": {}
            }
            
            # Read model results
            for model_name, result in results['model_results'].items():
                if result['success'] and result['path'] and result['path'].exists():
                    with open(result['path'], "rb") as f:
                        content = f.read()
                    response_data['model_results'][model_name] = {
                        "success": True,
                        "data": base64.b64encode(content).decode('utf-8'),
                        "size": len(content)
                    }
                else:
                    response_data['model_results'][model_name] = {
                        "success": False,
                        "error": result.get('error', 'Unknown error')
                    }
            
            logger.info(f"✅ VIDEO PIPELINE COMPLETED: {len(response_data['model_results'])} models processed")
            
        else:
            logger.info(f"   Running pipeline with single model...")
            results = process_video_pipeline(temp_file_path, output_dir, config, keep_intermediates)
            
            # Read result files
            gif_data = None
            spritesheet_data = None
            processed_data = None
            
            if results['gif_path'] and results['gif_path'].exists():
                with open(results['gif_path'], "rb") as f:
                    gif_data = base64.b64encode(f.read()).decode('utf-8')
            
            if results['spritesheet_path'] and results['spritesheet_path'].exists():
                with open(results['spritesheet_path'], "rb") as f:
                    spritesheet_data = base64.b64encode(f.read()).decode('utf-8')
            
            if results['processed_path'] and results['processed_path'].exists():
                with open(results['processed_path'], "rb") as f:
                    processed_data = base64.b64encode(f.read()).decode('utf-8')
            
            response_data = {
                "success": True,
                "filename": file.filename,
                "gif_data": gif_data,
                "spritesheet_data": spritesheet_data,
                "processed_data": processed_data
            }
            
            logger.info(f"✅ VIDEO PIPELINE COMPLETED")
        
        # Clean up temporary files
        temp_file_path.unlink()
        if not keep_intermediates:
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)
        
        return response_data
        
    except Exception as e:
        logger.error(f"❌ VIDEO PIPELINE FAILED: {e}")
        # Clean up on error
        try:
            if 'temp_file_path' in locals() and temp_file_path.exists():
                temp_file_path.unlink()
            if 'output_dir' in locals() and output_dir.exists():
                import shutil
                shutil.rmtree(output_dir, ignore_errors=True)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Video pipeline failed: {str(e)}")


from fastapi import APIRouter, File, Form, HTTPException, UploadFile
import logging, tempfile, base64, math
from pathlib import Path

@api.post("/process/gif-to-spritesheet")
async def process_gif_to_spritesheet(
    file: UploadFile = File(...),
    grid: str = Form(...),
    frames: Optional[int] = Form(None),
    frameWidth: Optional[int] = Form(None),
    frameHeight: Optional[int] = Form(None),
):
    """Convert an animated GIF to a spritesheet with background removal"""
    logger.info("🎬 GIF TO SPRITESHEET REQUEST STARTED")
    logger.info(f"   File: {getattr(file, 'filename', 'unknown')} "
                f"({getattr(file, 'size', 'unknown')} bytes)")
    logger.info(f"   Grid: {grid}")
    logger.info(f"   Frames (raw): {frames}")

    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Parse grid (e.g., "5x2")
    try:
        cols, rows = map(int, grid.lower().strip().split("x"))
        if cols <= 0 or rows <= 0:
            raise ValueError
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Grid must be in format 'colsxrows' (e.g., '5x2')",
        )
    logger.info(f"   Parsed grid: {cols} columns x {rows} rows")

    # Coerce frames to int if provided (e.g., if it arrives as a string from Form)
    if frames is not None:
        try:
            frames = int(frames)
            if frames <= 0:
                frames = None
        except Exception:
            frames = None
    logger.info(f"   Frames (normalized): {frames}")

    # Save uploaded GIF temporarily
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".gif") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = Path(tmp_file.name)
        logger.info(f"   GIF saved to: {tmp_file_path} ({len(content)} bytes)")
    except Exception as e:
        logger.error(f"   ❌ Failed saving upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to read uploaded file")

    try:
        # Create temp output dir
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "frames"
            output_dir.mkdir(parents=True, exist_ok=True)

            # ✅ Use the disk-extract helper and keyword args
            from .video import extract_gif_frames_to_dir  # <-- IMPORTANT
            logger.info("   Extracting frames from GIF to disk...")
            frame_paths = extract_gif_frames_to_dir(
                gif_path=tmp_file_path,
                output_dir=output_dir,
                max_frames=frames,
            )

            if not frame_paths:
                raise HTTPException(status_code=400, detail="No frames could be extracted from the GIF")

            logger.info(f"   Extracted {len(frame_paths)} frames")

            # Process each frame with background removal
            logger.info("   Processing frames with background removal...")
            processed_frames: list[Image.Image] = []

            for i, frame_path in enumerate(frame_paths):
                try:
                    logger.info(f"   Processing frame {i + 1}/{len(frame_paths)}: {frame_path.name}")
                    processed_path = _process_one(frame_path, output_dir / f"processed_{frame_path.name}")
                    processed_frames.append(Image.open(processed_path).convert("RGBA"))
                except Exception as e:
                    logger.error(f"   Error processing frame {i + 1}: {e}")
                    processed_frames.append(Image.open(frame_path).convert("RGBA"))

            if not processed_frames:
                raise HTTPException(status_code=500, detail="No frames were processed successfully")

            # Create spritesheet from processed frames
            frame_w, frame_h = processed_frames[0].size
            # Allow override if the client supplied exact cell size
            if frameWidth and frameHeight:
                frame_w, frame_h = int(frameWidth), int(frameHeight)
                processed_frames = [im.resize((frame_w, frame_h)) for im in processed_frames]

            frames_per_row = min(cols, len(processed_frames))
            frames_per_col = math.ceil(len(processed_frames) / frames_per_row)
            sheet_w = frames_per_row * frame_w
            sheet_h = frames_per_col * frame_h
            logger.info(f"   Spritesheet dimensions: {sheet_w}x{sheet_h}")

            sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))
            for idx, im in enumerate(processed_frames):
                r = idx // frames_per_row
                c = idx % frames_per_row
                sheet.paste(im, (c * frame_w, r * frame_h))

            combined_path = output_dir / "gif_spritesheet.png"
            sheet.save(combined_path)

            if not combined_path.exists():
                raise HTTPException(status_code=500, detail="Failed to create spritesheet")

            with open(combined_path, "rb") as f:
                b = f.read()
            spritesheet_base64 = base64.b64encode(b).decode("utf-8")

            logger.info(f"   ✅ GIF TO SPRITESHEET COMPLETED: {len(b)} bytes")
            return {
                "success": True,
                "spritesheet": spritesheet_base64,
                "config": {
                    "grid": grid,
                    "frames": len(processed_frames),
                    "frameWidth": frame_w,
                    "frameHeight": frame_h,
                },
                "frames_processed": len(processed_frames),
                "spritesheet_size": f"{sheet_w}x{sheet_h}",
                "gif_frames": len(frame_paths),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ GIF TO SPRITESHEET FAILED: {e}")
        raise HTTPException(status_code=500, detail=f"GIF to spritesheet conversion failed: {str(e)}")
    finally:
        try:
            if 'tmp_file_path' in locals() and tmp_file_path.exists():
                tmp_file_path.unlink()
        except Exception:
            pass


def serve(host: str = "127.0.0.1", port: int = 8000):
    uvicorn.run(api, host=host, port=port)
