from pathlib import Path
from typing import Optional, List
import tempfile
import shutil
import logging
import time
import base64

from fastapi import FastAPI, File, HTTPException, UploadFile, Form, Request
from fastapi.responses import Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from . import remove_bytes
from .video import video_to_gif, analyze_video
from .pipeline import process_video_pipeline, process_video_pipeline_all_models, VideoPipelineConfig
from .cli import _process_one

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


@api.post("/process/spritesheet")
async def process_spritesheet(
    file: UploadFile = File(...),
    grid: str = Form(...),
    frames: Optional[int] = Form(None),
    frameWidth: Optional[int] = Form(None),
    frameHeight: Optional[int] = Form(None)
):
    """Process a spritesheet with background removal"""
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    try:
        # Parse grid (e.g., "5x2")
        if 'x' not in grid:
            raise HTTPException(status_code=400, detail="Grid must be in format 'colsxrows' (e.g., '5x2')")
        
        cols, rows = map(int, grid.split('x'))
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
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
                    frame_path = output_dir / f"frame_{row:03d}_{col:03d}.png"
                    frame.save(frame_path)
                    
                    # Process frame with default model
                    try:
                        processed_path = _process_one(frame_path, output_dir / f"frame_{row:03d}_{col:03d}_processed.png")
                        processed_frame = Image.open(processed_path)
                        processed_frames.append(processed_frame)
                    except Exception as e:
                        print(f"Error processing frame {frame_count + 1}: {e}")
                        # Use original frame if processing fails
                        processed_frames.append(frame)
                    
                    frame_count += 1
                
                if frame_count >= max_frames:
                    break
            
            # Create combined spritesheet
            if processed_frames:
                # Use the actual grid dimensions that fit
                combined_width = frames_per_row * frame_width
                combined_height = frames_per_col * frame_height
                combined_image = Image.new('RGBA', (combined_width, combined_height), (0, 0, 0, 0))
                
                for i, frame in enumerate(processed_frames):
                    row = i // frames_per_row
                    col = i % frames_per_row
                    x = col * frame_width
                    y = row * frame_height
                    combined_image.paste(frame, (x, y))
                
                # Save combined spritesheet
                combined_path = output_dir / "combined_spritesheet.png"
                combined_image.save(combined_path)
                
                # Verify the file was created
                if not combined_path.exists():
                    raise HTTPException(status_code=500, detail="Failed to create combined spritesheet")
                
                # Read the file content and return as response
                with open(combined_path, "rb") as f:
                    content = f.read()
                
                return Response(
                    content=content,
                    media_type="image/png",
                    headers={"Content-Disposition": f'inline; filename="processed_spritesheet_{grid}.png"'}
                )
            else:
                raise HTTPException(status_code=500, detail="No frames were processed successfully")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary file
        try:
            Path(tmp_file_path).unlink()
        except:
            pass


@api.post("/process/video-to-gif")
async def process_video_to_gif(
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
        
        # Read the result file
        with open(result_path, "rb") as f:
            gif_content = f.read()
        
        # Clean up temporary files
        temp_file_path.unlink()
        result_path.unlink()
        
        logger.info(f"✅ VIDEO TO GIF COMPLETED: {len(gif_content)} bytes")
        
        return Response(
            content=gif_content,
            media_type="image/gif",
            headers={
                "Content-Disposition": f"attachment; filename={Path(file.filename).stem}.gif"
            }
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


def serve(host: str = "127.0.0.1", port: int = 8000):
    uvicorn.run(api, host=host, port=port)
