from pathlib import Path
from typing import Optional, List
import tempfile
import shutil

from fastapi import FastAPI, File, HTTPException, UploadFile, Form
from fastapi.responses import Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from . import remove_bytes
from .cli import _process_one

api = FastAPI(title="bgremove", version="0.1.0")

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


@api.post("/remove")
async def remove_endpoint(file: UploadFile = File(...), filename: Optional[str] = None):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    data = await file.read()
    try:
        cut = remove_bytes(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # Return as PNG with alpha
    name = filename or Path(file.filename or "output").stem
    headers = {"Content-Disposition": f'inline; filename="{name}.png"'}
    return Response(content=cut, media_type="image/png", headers=headers)


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
                frame_width = spritesheet_width // cols
                frame_height = spritesheet_height // rows
            
            # Validate dimensions
            if spritesheet_width % frame_width != 0:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Spritesheet width ({spritesheet_width}) is not divisible by frame width ({frame_width})"
                )
            if spritesheet_height % frame_height != 0:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Spritesheet height ({spritesheet_height}) is not divisible by frame height ({frame_height})"
                )
            
            frames_per_row = spritesheet_width // frame_width
            total_frames = frames_per_row * (spritesheet_height // frame_height)
            max_frames = frames or total_frames
            
            processed_frames = []
            frame_count = 0
            
            # Process frames
            for row in range(spritesheet_height // frame_height):
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
                    
                    # Process frame
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
                combined_width = cols * frame_width
                combined_height = rows * frame_height
                combined_image = Image.new('RGBA', (combined_width, combined_height), (0, 0, 0, 0))
                
                for i, frame in enumerate(processed_frames):
                    row = i // cols
                    col = i % cols
                    x = col * frame_width
                    y = row * frame_height
                    combined_image.paste(frame, (x, y))
                
                # Save combined spritesheet
                combined_path = output_dir / "combined_spritesheet.png"
                combined_image.save(combined_path)
                
                # Return the combined spritesheet
                return FileResponse(
                    path=str(combined_path),
                    media_type="image/png",
                    filename=f"processed_spritesheet_{grid}.png"
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


def serve(host: str = "127.0.0.1", port: int = 8000):
    uvicorn.run(api, host=host, port=port)
