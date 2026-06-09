import asyncio
import base64
import logging
import math
import os
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
from .cli import _process_one
from .pipeline import (
    VideoPipelineConfig,
    process_video_pipeline,
    process_video_pipeline_all_models,
)
from .spritesheet_utils import image_has_transparency, save_rgba_png
from .video import analyze_video, video_to_gif

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
api = FastAPI(title="bgremove", version="0.1.0")


@api.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"🌐 INCOMING REQUEST: {request.method} {request.url}")
    logger.info(f"   Headers: {dict(request.headers)}")
    logger.info(f"   Client: {(request.client.host if request.client else 'unknown')}")
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"✅ RESPONSE: {response.status_code} - {process_time:.3f}s")
    return response


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
    return {"ok": True}


@api.post("/analyze-spritesheet")
async def analyze_spritesheet(file: UploadFile = File(...)):
    """
    Detect sprites on alpha or white background, infer (cols x rows), tile size,
    and return per-frame boxes. Robust to big gutters and non-uniform padding.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    import math
    import tempfile
    from pathlib import Path

    import numpy as np
    from PIL import Image

    MIN_BLOB_AREA = 32 * 32
    MIN_TILE = 16
    MAX_FRAMES = 512
    WHITE_THR = 245
    EDGE_THR = 12
    ROW_JOIN_FACTOR = 0.7
    COL_JOIN_FACTOR = 0.7
    tmp_file_path: str | None = None
    img: Image.Image | None = None

    def cleanup():
        try:
            if img:
                img.close()
        except Exception:
            pass
        try:
            if tmp_file_path:
                Path(tmp_file_path).unlink(missing_ok=True)
        except Exception:
            pass

    def to_mask_rgba(a: np.ndarray, rgb: np.ndarray) -> np.ndarray:
        """
        Foreground mask that works with alpha OR white bg:
          - alpha > 8 is foreground
          - OR pixel is not almost-white
          - OR strong edge magnitude
        """
        h, w = a.shape
        r, g, b = (
            rgb[..., 0].astype(np.float32),
            rgb[..., 1].astype(np.float32),
            rgb[..., 2].astype(np.float32),
        )
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        not_white = lum < WHITE_THR
        dx = np.zeros_like(lum)
        dy = np.zeros_like(lum)
        dx[:, 1:-1] = np.abs(lum[:, 2:] - lum[:, :-2]) * 0.5
        dy[1:-1, :] = np.abs(lum[2:, :] - lum[:-2, :]) * 0.5
        edge_mag = dx + dy
        has_edge = edge_mag > EDGE_THR
        mask = (a > 8) | not_white | has_edge
        return mask.astype(np.uint8)

    def find_components(mask: np.ndarray) -> list[tuple[int, int, int, int]]:
        """
        Return list of bounding boxes (x,y,w,h) for connected components.
        Uses OpenCV if available; otherwise a NumPy flood-fill.
        """
        try:
            import cv2

            kernel = np.ones((3, 3), np.uint8)
            m = cv2.morphologyEx(mask * 255, cv2.MORPH_OPEN, kernel, iterations=1)
            cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            boxes = []
            for c in cnts:
                x, y, w, h = cv2.boundingRect(c)
                if w * h >= MIN_BLOB_AREA:
                    boxes.append((int(x), int(y), int(w), int(h)))
            return boxes
        except Exception:
            h, w = mask.shape
            vis = np.zeros_like(mask, dtype=np.uint8)
            boxes = []
            for yy in range(h):
                for xx in range(w):
                    if mask[yy, xx] == 0 or vis[yy, xx]:
                        continue
                    q = [(xx, yy)]
                    vis[yy, xx] = 1
                    minx = miny = 10**9
                    maxx = maxy = -1
                    sz = 0
                    while q:
                        x, y = q.pop()
                        sz += 1
                        if x < minx:
                            minx = x
                        if x > maxx:
                            maxx = x
                        if y < miny:
                            miny = y
                        if y > maxy:
                            maxy = y
                        if x > 0 and mask[y, x - 1] and (not vis[y, x - 1]):
                            vis[y, x - 1] = 1
                            q.append((x - 1, y))
                        if x < w - 1 and mask[y, x + 1] and (not vis[y, x + 1]):
                            vis[y, x + 1] = 1
                            q.append((x + 1, y))
                        if y > 0 and mask[y - 1, x] and (not vis[y - 1, x]):
                            vis[y - 1, x] = 1
                            q.append((x, y - 1))
                        if y < h - 1 and mask[y + 1, x] and (not vis[y + 1, x]):
                            vis[y + 1, x] = 1
                            q.append((x, y + 1))
                    bw = maxx - minx + 1
                    bh = maxy - miny + 1
                    if bw * bh >= MIN_BLOB_AREA:
                        boxes.append((minx, miny, bw, bh))
            return boxes

    def group_sorted(vals: list[float], thresh: float) -> list[list[float]]:
        """
        Greedy 1D clustering: split when gap > thresh.
        vals must be sorted.
        """
        if not vals:
            return []
        groups = [[vals[0]]]
        for v in vals[1:]:
            if abs(v - groups[-1][-1]) <= thresh:
                groups[-1].append(v)
            else:
                groups.append([v])
        return groups

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            data = await file.read()
            tmp.write(data)
            tmp_file_path = tmp.name
        img = Image.open(tmp_file_path).convert("RGBA")
        W, H = img.size
        arr = np.array(img)
        a = arr[..., 3]
        rgb = arr[..., :3]
        mask = to_mask_rgba(a, rgb)
        ys, xs = np.where(mask > 0)
        if len(xs) == 0:
            cleanup()
            raise HTTPException(status_code=422, detail="No foreground detected.")
        left, right = (int(xs.min()), int(xs.max()) + 1)
        top, bottom = (int(ys.min()), int(ys.max()) + 1)
        core_mask = mask[top:bottom, left:right]
        CW, CH = (core_mask.shape[1], core_mask.shape[0])
        boxes = find_components(core_mask)
        boxes = [(x + left, y + top, w, h) for x, y, w, h in boxes]
        if not boxes:
            cleanup()
            raise HTTPException(status_code=422, detail="No sprites detected.")
        centers = [(x + w / 2.0, y + h / 2.0) for x, y, w, h in boxes]
        widths = [w for _, _, w, _ in boxes]
        heights = [h for _, _, _, h in boxes]
        med_w = float(np.median(widths))
        med_h = float(np.median(heights))
        if med_w < MIN_TILE or med_h < MIN_TILE:
            boxes = [b for b in boxes if b[2] >= MIN_TILE and b[3] >= MIN_TILE]
            if not boxes:
                cleanup()
                raise HTTPException(status_code=422, detail="Detected tiles are too small.")
        ys_sorted = sorted([c[1] for c in centers])
        row_thresh = max(4.0, ROW_JOIN_FACTOR * med_h)
        row_groups_y = group_sorted(ys_sorted, row_thresh)
        row_centers = [float(np.mean(g)) for g in row_groups_y]

        def nearest_row_idx(yc: float) -> int:
            return int(np.argmin([abs(yc - rc) for rc in row_centers]))

        per_row: dict[int, list[tuple[float, tuple[int, int, int, int]]]] = {}
        for c, b in zip(centers, boxes, strict=False):
            r = nearest_row_idx(c[1])
            per_row.setdefault(r, []).append((c[0], b))
        col_counts = []
        col_steps = []
        normalized_rows: list[list[tuple[int, int, int, int]]] = []
        for r in sorted(per_row.keys()):
            row = sorted(per_row[r], key=lambda t: t[0])
            normalized_rows.append([t[1] for t in row])
            xs = [t[0] for t in row]
            if len(xs) >= 2:
                steps = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
                col_steps.extend(steps)
            col_counts.append(len(row))
        rows = len(per_row)
        cols = int(np.median(col_counts)) if col_counts else len(normalized_rows[0])
        if rows * cols < len(boxes) * 0.7:
            xs_all = sorted([c[0] for c in centers])
            col_thresh = max(4.0, COL_JOIN_FACTOR * med_w)
            col_groups_x = group_sorted(xs_all, col_thresh)
            cols = max(cols, int(round(np.median([len(g) for g in col_groups_x]))))
        pitch_x = float(np.median(col_steps)) if col_steps else med_w * 1.2
        row_centers_sorted = sorted(row_centers)
        row_gaps = [
            row_centers_sorted[i + 1] - row_centers_sorted[i]
            for i in range(len(row_centers_sorted) - 1)
        ]
        pitch_y = float(np.median(row_gaps)) if row_gaps else med_h * 1.2
        tile_w = int(round(max(med_w, MIN_TILE)))
        tile_h = int(round(max(med_h, MIN_TILE)))
        total = rows * cols
        if total > MAX_FRAMES:
            scale = math.sqrt(total / MAX_FRAMES)
            rows = max(1, int(round(rows / scale)))
            cols = max(1, int(round(cols / scale)))
            total = rows * cols
        size_spread = (
            np.std(widths) / (np.mean(widths) + 1e-06)
            + np.std(heights) / (np.mean(heights) + 1e-06)
        ) * 0.5
        pitch_spread = (np.std(col_steps) / (np.mean(col_steps) + 1e-06) if col_steps else 0.5) + (
            np.std(row_gaps) / (np.mean(row_gaps) + 1e-06) if row_gaps else 0.5
        )
        size_term = max(0.0, 1.0 - min(1.0, size_spread))
        pitch_term = max(0.0, 1.0 - min(1.0, pitch_spread))
        fill_term = min(1.0, len(boxes) / max(1, rows * cols))
        confidence = round(0.15 + 0.45 * size_term + 0.25 * pitch_term + 0.15 * fill_term, 3)
        out_boxes = []
        for r in sorted(per_row.keys()):
            row = sorted(per_row[r], key=lambda t: t[0])
            out_boxes.extend([tuple(map(int, b)) for _, b in row])
        result = {
            "spritesheet_size": f"{W}x{H}",
            "best_guess": {
                "grid": f"{cols}x{rows}",
                "frame_size": f"{tile_w}x{tile_h}",
                "total_frames": int(rows * cols),
                "detected_sprites": len(boxes),
                "confidence": float(min(1.0, max(0.0, confidence))),
            },
            "diagnostics": {
                "content_crop": {"x": int(left), "y": int(top), "w": int(CW), "h": int(CH)},
                "median_bbox": {"w": tile_w, "h": tile_h},
                "median_pitch": {"x": int(round(pitch_x)), "y": int(round(pitch_y))},
                "rows_detected": rows,
                "cols_detected": cols,
            },
            "boxes_row_major": out_boxes[:MAX_FRAMES],
        }
        return result
    except HTTPException:
        cleanup()
        raise
    except Exception as e:
        cleanup()
        raise HTTPException(status_code=500, detail=str(e)) from None
    finally:
        cleanup()


@api.post("/remove")
async def remove_endpoint(
    file: UploadFile = File(...),
    filename: str | None = None,
    model: str = Form("isnet-general-use"),
):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    data = await file.read()
    try:
        cut = remove_bytes(data, model_name=model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
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
        "isnet-anime",
        "bria-rmbg-1.4",
        "u2net_human_seg",
        "u2net",
        "u2netp",
        "u2net_cloth_seg",
        "silueta",
    ]
    results = {}
    for model in models:
        try:
            processed_data = remove_bytes(data, model_name=model)
            import base64

            results[model] = {
                "success": True,
                "data": base64.b64encode(processed_data).decode("utf-8"),
                "size": len(processed_data),
            }
        except Exception as e:
            results[model] = {"success": False, "error": str(e)}
    return {"original_filename": file.filename, "original_size": len(data), "models": results}


def _ensure_rgba(im: Image.Image) -> Image.Image:
    """Convert an image to RGBA, preserving transparency."""
    if im.mode == "RGBA":
        return im
    return im.convert("RGBA")


def _parse_grid(grid: str) -> tuple[int, int]:
    if grid.lower() == "auto":
        return (0, 0)
    if "x" not in grid:
        raise HTTPException(
            status_code=400, detail="Grid must be 'colsxrows' (e.g., '5x2') or 'auto'."
        )
    cols, rows = map(int, grid.lower().split("x"))
    if cols <= 0 or rows <= 0:
        raise HTTPException(status_code=400, detail="Grid numbers must be positive integers.")
    return (cols, rows)


def _auto_grid(num_frames: int) -> tuple[int, int]:
    """Choose a near-square grid for the given number of frames."""
    cols = int(math.ceil(math.sqrt(num_frames)))
    rows = int(math.ceil(num_frames / cols))
    return (cols, rows)


def _extract_gif_frames(
    path: Path, max_frames: int | None = None, sample_evenly: bool = True
) -> list[Image.Image]:
    """Extract animation frames from a GIF, optionally sampling evenly."""
    from .video import extract_gif_frames

    frames = extract_gif_frames(
        path, max_frames=max_frames, sample_evenly=sample_evenly and max_frames is not None
    )
    return [_ensure_rgba(f) for f in frames]


@api.post("/process/spritesheet-all-models")
async def process_spritesheet_all_models(
    file: UploadFile = File(...),
    grid: str = Form(...),
    frames: int | None = Form(None),
    frameWidth: int | None = Form(None),
    frameHeight: int | None = Form(None),
    remove_background: bool = Form(True),
    sample_evenly: bool = Form(True),
):
    """Process a spritesheet or animated GIF with all available models."""
    logger.info("🎬 SPRITESHEET ALL-MODELS REQUEST STARTED")
    logger.info(
        f"   File: {file.filename} ({(file.size if hasattr(file, 'size') else 'unknown')} bytes)"
    )
    logger.info(f"   Grid: {grid}")
    logger.info(f"   Frames: {frames}")
    logger.info(f"   Frame dimensions: {frameWidth}x{frameHeight}")
    logger.info(f"   Remove background: {remove_background}, Sample evenly: {sample_evenly}")
    if not file:
        logger.error("❌ No file uploaded")
        raise HTTPException(status_code=400, detail="No file uploaded")
    tmp_file_path: str | None = None
    try:
        suffix = Path(file.filename or "").suffix.lower() or ".bin"
        input_is_gif = file.content_type == "image/gif" or suffix == ".gif"
        logger.info("   Saving uploaded file temporarily...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        logger.info(f"   File saved to: {tmp_file_path} ({len(content)} bytes)")
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "frames"
            output_dir.mkdir()
            extracted_frames: list[Image.Image] = []
            output_grid = grid
            if input_is_gif:
                logger.info("   Input is GIF — extracting animation frames")
                extracted_frames = _extract_gif_frames(
                    Path(tmp_file_path), max_frames=frames, sample_evenly=sample_evenly
                )
                if not extracted_frames:
                    raise HTTPException(status_code=400, detail="GIF has no frames")
                frame_width, frame_height = extracted_frames[0].size
                if frameWidth and frameHeight:
                    frame_width, frame_height = (int(frameWidth), int(frameHeight))
                    extracted_frames = [
                        im.resize((frame_width, frame_height)) for im in extracted_frames
                    ]
                max_frames = len(extracted_frames)
                if grid == "auto":
                    cols, rows = _auto_grid(max_frames)
                    output_grid = f"{cols}x{rows}"
                else:
                    cols, rows = _parse_grid(grid)
                    output_grid = grid
                frames_per_row = cols
                frames_per_col = rows
                spritesheet_width = cols * frame_width
                spritesheet_height = rows * frame_height
                logger.info(
                    "   Extracted %s GIF frames, layout %s, cell %sx%s",
                    max_frames,
                    output_grid,
                    frame_width,
                    frame_height,
                )
            else:
                if grid == "auto":
                    cols, rows = (5, 2)
                    output_grid = f"{cols}x{rows}"
                    logger.info(f"   Using auto-detected grid: {cols}x{rows}")
                else:
                    cols, rows = _parse_grid(grid)
                logger.info(f"   Parsed grid: {cols} columns x {rows} rows")
                with Image.open(tmp_file_path) as spritesheet:
                    spritesheet_width, spritesheet_height = spritesheet.size
                    if frameWidth and frameHeight:
                        frame_width = frameWidth
                        frame_height = frameHeight
                    else:
                        frame_width = spritesheet_width // cols
                        frame_height = spritesheet_height // rows
                    frames_per_row = spritesheet_width // frame_width
                    frames_per_col = spritesheet_height // frame_height
                    total_frames = frames_per_row * frames_per_col
                    if frames_per_row < cols:
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"Spritesheet width ({spritesheet_width}) cannot fit "
                                f"{cols} frames of width {frame_width}. "
                                f"Maximum frames per row: {frames_per_row}"
                            ),
                        )
                    if frames_per_col < rows:
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"Spritesheet height ({spritesheet_height}) cannot fit "
                                f"{rows} frames of height {frame_height}. "
                                f"Maximum frames per column: {frames_per_col}"
                            ),
                        )
                    max_frames = frames or total_frames
                    frame_count = 0
                    for row in range(frames_per_col):
                        for col in range(frames_per_row):
                            if frame_count >= max_frames:
                                break
                            left = col * frame_width
                            top = row * frame_height
                            frame = spritesheet.crop(
                                (left, top, left + frame_width, top + frame_height)
                            )
                            extracted_frames.append(_ensure_rgba(frame))
                            frame_count += 1
                        if frame_count >= max_frames:
                            break
            models = [
                "isnet-general-use",
                "u2net_human_seg",
                "u2net",
                "u2netp",
                "u2net_cloth_seg",
                "silueta",
            ]
            logger.info(f"   Processing with {len(models)} models: {', '.join(models)}")
            results = {}
            for i, model in enumerate(models, 1):
                logger.info(f"   🔄 Processing model {i}/{len(models)}: {model}")
                try:
                    processed_frames = []
                    for frame_idx, frame in enumerate(extracted_frames):
                        frame_path = output_dir / f"frame_{frame_idx:05d}_{model}.png"
                        frame.save(frame_path)
                        try:
                            if remove_background:
                                logger.info(
                                    "   Removing background for frame %s/%s with model: %s",
                                    frame_idx + 1,
                                    len(extracted_frames),
                                    model,
                                )
                                processed_path = _process_one(
                                    frame_path,
                                    output_dir / f"frame_{frame_idx:05d}_{model}_processed.png",
                                    model_name=model,
                                )
                                with Image.open(processed_path) as processed_frame:
                                    processed_frames.append(processed_frame.copy())
                            else:
                                logger.info(
                                    "   Packing frame %s/%s (no background removal)",
                                    frame_idx + 1,
                                    len(extracted_frames),
                                )
                                processed_frames.append(frame.copy())
                            logger.info(f"   Frame {frame_idx + 1} done for {model}")
                        except Exception as e:
                            logger.error(
                                f"Error processing frame {frame_idx + 1} with {model}: {e}"
                            )
                            processed_frames.append(frame.copy())
                    if processed_frames:
                        pack_cols = frames_per_row if not input_is_gif else cols
                        pack_rows = int(math.ceil(len(processed_frames) / pack_cols))
                        combined_width = pack_cols * frame_width
                        combined_height = pack_rows * frame_height
                        combined_image = Image.new(
                            "RGBA", (combined_width, combined_height), (0, 0, 0, 0)
                        )
                        for idx, proc_frame in enumerate(processed_frames):
                            row = idx // pack_cols
                            col = idx % pack_cols
                            combined_image.paste(
                                proc_frame, (col * frame_width, row * frame_height), proc_frame
                            )
                        import io

                        img_bytes = io.BytesIO()
                        save_rgba_png(combined_image, img_bytes)
                        img_bytes.seek(0)
                        results[model] = {
                            "success": True,
                            "data": base64.b64encode(img_bytes.getvalue()).decode("utf-8"),
                            "size": len(img_bytes.getvalue()),
                            "frames_processed": len(processed_frames),
                        }
                        logger.info(
                            "   ✅ %s completed successfully (%s frames, %s bytes)",
                            model,
                            len(processed_frames),
                            len(img_bytes.getvalue()),
                        )
                    else:
                        results[model] = {
                            "success": False,
                            "error": "No frames were processed successfully",
                        }
                        logger.warning(
                            f"   ⚠️ {model} failed: No frames were processed successfully"
                        )
                except Exception as e:
                    results[model] = {"success": False, "error": str(e)}
                    logger.error(f"   ❌ {model} failed with error: {str(e)}")
            successful_models = sum(1 for r in results.values() if r.get("success", False))
            logger.info(
                "🎉 SPRITESHEET ALL-MODELS COMPLETED: %s/%s models successful",
                successful_models,
                len(models),
            )
            return {
                "original_filename": file.filename,
                "original_size": len(content),
                "spritesheet_size": f"{spritesheet_width}x{spritesheet_height}",
                "grid": output_grid,
                "frames_processed": len(extracted_frames),
                "frame_size": f"{frame_width}x{frame_height}",
                "input_type": "gif" if input_is_gif else "spritesheet",
                "models": results,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ SPRITESHEET ALL-MODELS FAILED: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from None
    finally:
        if tmp_file_path:
            try:
                Path(tmp_file_path).unlink()
                logger.info("   🧹 Cleaned up temporary file")
            except Exception:
                logger.warning("   ⚠️ Failed to clean up temporary file")


async def _maybe_process_frame(
    frame_path: Path, out_path: Path, model_name: str = "isnet-general-use"
) -> Image.Image:
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
    grid: str = Form("auto"),
    frames: int | None = Form(None),
    frameWidth: int | None = Form(None),
    frameHeight: int | None = Form(None),
    model: str = Form("isnet-general-use"),
    remove_background: bool = Form(True),
    sample_evenly: bool = Form(True),
):
    """
    Upload a GIF or an image spritesheet.
    - If GIF: extract frames, process them, and repack into a PNG spritesheet.
    - If spritesheet: slice by grid (or auto-slice using frameWidth/Height),
      process, and repack.
    Returns base64-encoded PNG spritesheet and metadata.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    logger.info("🎬 SPRITESHEET PROCESSING REQUEST STARTED")
    logger.info(f"   File: {file.filename}")
    logger.info(f"   Grid: {grid}, Frames: {frames}, Model: {model}")
    logger.info(f"   Remove background: {remove_background}, Sample evenly: {sample_evenly}")
    tmp_file_path: str | None = None
    try:
        suffix = Path(file.filename or "").suffix.lower() or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Uploaded file is empty")
            tmp.write(content)
            tmp_file_path = tmp.name
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            frames_dir = temp_dir_path / "frames"
            frames_dir.mkdir()
            input_is_gif = file.content_type == "image/gif" or suffix == ".gif"
            extracted_frames: list[Image.Image] = []
            fw: int | None = None
            fh: int | None = None
            if input_is_gif:
                logger.info("   Input is GIF — extracting animation frames")
                extracted_frames = _extract_gif_frames(
                    Path(tmp_file_path), max_frames=frames, sample_evenly=sample_evenly
                )
                if not extracted_frames:
                    raise HTTPException(status_code=400, detail="GIF has no frames")
                fw, fh = extracted_frames[0].size
                logger.info(f"   Extracted {len(extracted_frames)} GIF frames at {fw}x{fh}")
            else:
                cols, rows = _parse_grid(grid)
                with Image.open(tmp_file_path) as sheet:
                    sheet = _ensure_rgba(sheet.convert("RGBA"))
                    sw, sh = sheet.size
                    if frameWidth and frameHeight:
                        fw, fh = (int(frameWidth), int(frameHeight))
                        if fw <= 0 or fh <= 0:
                            raise HTTPException(
                                status_code=400, detail="frameWidth and frameHeight must be > 0"
                            )
                        frames_per_row = sw // fw
                        frames_per_col = sh // fh
                    elif cols and rows:
                        fw = sw // cols
                        fh = sh // rows
                        frames_per_row = cols
                        frames_per_col = rows
                    else:
                        fw, fh = (sw, sh)
                        frames_per_row = 1
                        frames_per_col = 1
                    if fw <= 0 or fh <= 0:
                        raise HTTPException(
                            status_code=400, detail="Computed frame size is invalid."
                        )
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
                    raise HTTPException(
                        status_code=500, detail="No frames could be extracted from the spritesheet."
                    )
            total_to_process = len(extracted_frames)
            action = "background removal" if remove_background else "packing"
            logger.info(f"   Processing {total_to_process} frames ({action}, {model})...")
            processed_frames: list[Image.Image] = []
            for i, img in enumerate(extracted_frames):
                if remove_background:
                    in_frame_path = frames_dir / f"in_{i:05d}.png"
                    out_frame_path = frames_dir / f"out_{i:05d}.png"
                    img.save(in_frame_path)
                    processed = await _maybe_process_frame(in_frame_path, out_frame_path, model)
                    processed_frames.append(processed)
                else:
                    processed_frames.append(img.copy())
                if (i + 1) % 5 == 0 or i + 1 == total_to_process:
                    logger.info(f"   Processed {i + 1}/{total_to_process} frames")
            if grid.lower() == "auto" or input_is_gif:
                cols, rows = _auto_grid(len(processed_frames))
            else:
                cols, rows = _parse_grid(grid)
            total_slots = cols * rows if cols and rows else len(processed_frames)
            if total_slots < len(processed_frames):
                cols, rows = _auto_grid(len(processed_frames))
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
                combined.paste(frame, (c * fw, r * fh), frame)
            combined_path = frames_dir / "combined_spritesheet.png"
            save_rgba_png(combined, combined_path)
            with open(combined_path, "rb") as f:
                b64_png = base64.b64encode(f.read()).decode("utf-8")
            has_transparency = image_has_transparency(combined)
            logger.info(
                "   ✅ SPRITESHEET COMPLETED: %s frames, output %sx%s, transparent=%s",
                len(processed_frames),
                combined_w,
                combined_h,
                has_transparency,
            )
            return {
                "success": True,
                "spritesheet": b64_png,
                "spritesheet_mime": "image/png",
                "has_transparency": has_transparency,
                "config": {
                    "input": file.filename,
                    "input_type": "gif" if input_is_gif else "spritesheet",
                    "grid": f"{cols}x{rows}" if cols and rows else "auto",
                    "frames": len(processed_frames),
                    "frameWidth": fw,
                    "frameHeight": fh,
                    "remove_background": remove_background,
                    "sample_evenly": sample_evenly,
                    "has_transparency": has_transparency,
                },
                "spritesheet_size": f"{combined_w}x{combined_h}",
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
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
    duration: float | None = Form(None),
    max_width: int = Form(480),
    max_height: int = Form(480),
):
    """Convert video to GIF with custom settings."""
    logger.info("🎬 VIDEO TO GIF REQUEST STARTED")
    logger.info(f"   File: {file.filename} ({file.size} bytes)")
    logger.info(f"   Settings: {fps} FPS, {duration}s duration, {max_width}x{max_height} max size")
    try:
        file_extension = Path(file.filename or "").suffix.lower()
        is_gif = file_extension == ".gif" or file.content_type == "image/gif"
        if is_gif:
            logger.info("   Input is already a GIF, returning as-is")
            content = await file.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".gif") as temp_file:
                temp_file.write(content)
                temp_file_path = Path(temp_file.name)
            background_tasks.add_task(
                lambda: temp_file_path.unlink() if temp_file_path.exists() else None
            )
            return FileResponse(
                path=temp_file_path,
                media_type="image/gif",
                filename=f"{Path(file.filename).stem}.gif",
            )
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(file.filename).suffix
        ) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = Path(temp_file.name)
        logger.info(f"   File saved to: {temp_file_path}")
        output_path = temp_file_path.with_suffix(".gif")
        logger.info("   Converting video to GIF...")
        result_path = video_to_gif(
            temp_file_path,
            output_path,
            fps=fps,
            duration=duration,
            max_width=max_width,
            max_height=max_height,
        )
        logger.info(f"✅ VIDEO TO GIF COMPLETED: {result_path.stat().st_size} bytes")
        temp_file_path.unlink()
        background_tasks.add_task(lambda: result_path.unlink() if result_path.exists() else None)
        return FileResponse(
            path=result_path, media_type="image/gif", filename=f"{Path(file.filename).stem}.gif"
        )
    except Exception as e:
        logger.error(f"❌ VIDEO TO GIF FAILED: {e}")
        try:
            if "temp_file_path" in locals() and temp_file_path.exists():
                temp_file_path.unlink()
            if "result_path" in locals() and result_path.exists():
                result_path.unlink()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Video processing failed: {str(e)}") from None


@api.post("/analyze/gif")
async def analyze_gif_endpoint(file: UploadFile = File(...)):
    """Analyze an animated GIF and return frame count plus layout recommendations."""
    logger.info("🔍 GIF ANALYSIS REQUEST STARTED")
    logger.info(f"   File: {file.filename}")
    temp_file_path: Path | None = None
    try:
        suffix = Path(file.filename or "").suffix.lower() or ".gif"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Uploaded file is empty")
            temp_file.write(content)
            temp_file_path = Path(temp_file.name)
        with Image.open(temp_file_path) as gif:
            frame_count = int(getattr(gif, "n_frames", 1)) or 1
            width, height = gif.size
        cols, rows = _auto_grid(frame_count)
        logger.info(f"✅ GIF ANALYSIS COMPLETED: {frame_count} frames, {width}x{height}")
        return {
            "filename": file.filename,
            "analysis": {
                "frames": frame_count,
                "size": [width, height],
                "recommended_grid": f"{cols}x{rows}",
                "file_size": len(content),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ GIF ANALYSIS FAILED: {e}")
        raise HTTPException(status_code=500, detail=f"GIF analysis failed: {str(e)}") from None
    finally:
        if temp_file_path and temp_file_path.exists():
            temp_file_path.unlink(missing_ok=True)


@api.post("/analyze/video")
async def analyze_video_endpoint(file: UploadFile = File(...)):
    """Analyze video and provide processing recommendations."""
    logger.info("🔍 VIDEO ANALYSIS REQUEST STARTED")
    logger.info(f"   File: {file.filename} ({file.size} bytes)")
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(file.filename).suffix
        ) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = Path(temp_file.name)
        logger.info(f"   File saved to: {temp_file_path}")
        logger.info("   Analyzing video...")
        analysis = analyze_video(temp_file_path)
        temp_file_path.unlink()
        logger.info("✅ VIDEO ANALYSIS COMPLETED")
        return {"filename": file.filename, "analysis": analysis}
    except Exception as e:
        logger.error(f"❌ VIDEO ANALYSIS FAILED: {e}")
        try:
            if "temp_file_path" in locals() and temp_file_path.exists():
                temp_file_path.unlink()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Video analysis failed: {str(e)}") from None


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
    logger.info("🚀 VIDEO PIPELINE REQUEST STARTED")
    logger.info(f"   File: {file.filename} ({file.size} bytes)")
    logger.info(
        f"   Settings: {fps} FPS, {duration}s duration, {grid} grid, {frames} frames, {model} model"
    )
    logger.info(f"   All models: {all_models}, Keep intermediates: {keep_intermediates}")
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(file.filename).suffix
        ) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = Path(temp_file.name)
        logger.info(f"   File saved to: {temp_file_path}")
        output_dir = Path(tempfile.mkdtemp())
        logger.info(f"   Output directory: {output_dir}")
        config = VideoPipelineConfig(
            fps=fps, duration=duration, grid=grid, frames=frames, model=model
        )
        if all_models:
            logger.info("   Running pipeline with all models...")
            results = process_video_pipeline_all_models(
                temp_file_path, output_dir, config, keep_intermediates
            )
            response_data = {
                "success": True,
                "filename": file.filename,
                "gif_path": str(results["gif_path"]) if results["gif_path"] else None,
                "spritesheet_path": (
                    str(results["spritesheet_path"]) if results["spritesheet_path"] else None
                ),
                "model_results": {},
            }
            for model_name, result in results["model_results"].items():
                if result["success"] and result["path"] and result["path"].exists():
                    with open(result["path"], "rb") as f:
                        content = f.read()
                    response_data["model_results"][model_name] = {
                        "success": True,
                        "data": base64.b64encode(content).decode("utf-8"),
                        "size": len(content),
                    }
                else:
                    response_data["model_results"][model_name] = {
                        "success": False,
                        "error": result.get("error", "Unknown error"),
                    }
            logger.info(
                "✅ VIDEO PIPELINE COMPLETED: %s models processed",
                len(response_data["model_results"]),
            )
        else:
            logger.info("   Running pipeline with single model...")
            results = process_video_pipeline(temp_file_path, output_dir, config, keep_intermediates)
            gif_data = None
            spritesheet_data = None
            processed_data = None
            if results["gif_path"] and results["gif_path"].exists():
                with open(results["gif_path"], "rb") as f:
                    gif_data = base64.b64encode(f.read()).decode("utf-8")
            if results["spritesheet_path"] and results["spritesheet_path"].exists():
                with open(results["spritesheet_path"], "rb") as f:
                    spritesheet_data = base64.b64encode(f.read()).decode("utf-8")
            if results["processed_path"] and results["processed_path"].exists():
                with open(results["processed_path"], "rb") as f:
                    processed_data = base64.b64encode(f.read()).decode("utf-8")
            response_data = {
                "success": True,
                "filename": file.filename,
                "gif_data": gif_data,
                "spritesheet_data": spritesheet_data,
                "processed_data": processed_data,
            }
            logger.info("✅ VIDEO PIPELINE COMPLETED")
        temp_file_path.unlink()
        if not keep_intermediates:
            import shutil

            shutil.rmtree(output_dir, ignore_errors=True)
        return response_data
    except Exception as e:
        logger.error(f"❌ VIDEO PIPELINE FAILED: {e}")
        try:
            if "temp_file_path" in locals() and temp_file_path.exists():
                temp_file_path.unlink()
            if "output_dir" in locals() and output_dir.exists():
                import shutil

                shutil.rmtree(output_dir, ignore_errors=True)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Video pipeline failed: {str(e)}") from None


@api.post("/process/gif-to-spritesheet")
async def process_gif_to_spritesheet(
    file: UploadFile = File(...),
    grid: str = Form(...),
    frames: int | None = Form(None),
    frameWidth: int | None = Form(None),
    frameHeight: int | None = Form(None),
    remove_background: bool = Form(True),
    sample_evenly: bool = Form(True),
):
    """Convert an animated GIF to a spritesheet, optionally removing backgrounds."""
    logger.info("🎬 GIF TO SPRITESHEET REQUEST STARTED")
    logger.info(
        "   File: %s (%s bytes)",
        getattr(file, "filename", "unknown"),
        getattr(file, "size", "unknown"),
    )
    logger.info(f"   Grid: {grid}")
    logger.info(f"   Frames (raw): {frames}")
    logger.info(f"   Remove background: {remove_background}, Sample evenly: {sample_evenly}")
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    try:
        cols, rows = map(int, grid.lower().strip().split("x"))
        if cols <= 0 or rows <= 0:
            raise ValueError
    except Exception:
        raise HTTPException(
            status_code=400, detail="Grid must be in format 'colsxrows' (e.g., '5x2')"
        ) from None
    logger.info(f"   Parsed grid: {cols} columns x {rows} rows")
    if frames is not None:
        try:
            frames = int(frames)
            if frames <= 0:
                frames = None
        except Exception:
            frames = None
    logger.info(f"   Frames (normalized): {frames}")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".gif") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = Path(tmp_file.name)
        logger.info(f"   GIF saved to: {tmp_file_path} ({len(content)} bytes)")
    except Exception as e:
        logger.error(f"   ❌ Failed saving upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to read uploaded file") from None
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "frames"
            output_dir.mkdir(parents=True, exist_ok=True)
            extracted_frames = _extract_gif_frames(
                tmp_file_path, max_frames=frames, sample_evenly=sample_evenly
            )
            if not extracted_frames:
                raise HTTPException(
                    status_code=400, detail="No frames could be extracted from the GIF"
                )
            logger.info(f"   Extracted {len(extracted_frames)} frames")
            action = "background removal" if remove_background else "packing"
            logger.info(f"   {action} for {len(extracted_frames)} frames...")
            processed_frames: list[Image.Image] = []
            for i, frame in enumerate(extracted_frames):
                try:
                    if remove_background:
                        frame_path = output_dir / f"frame_{i:05d}.png"
                        frame.save(frame_path)
                        logger.info(
                            f"   Removing background for frame {i + 1}/{len(extracted_frames)}"
                        )
                        processed_path = _process_one(
                            frame_path, output_dir / f"processed_{frame_path.name}"
                        )
                        processed_frames.append(Image.open(processed_path).convert("RGBA"))
                    else:
                        logger.info(f"   Packing frame {i + 1}/{len(extracted_frames)}")
                        processed_frames.append(frame.copy())
                except Exception as e:
                    logger.error(f"   Error processing frame {i + 1}: {e}")
                    processed_frames.append(frame.copy())
            if not processed_frames:
                raise HTTPException(status_code=500, detail="No frames were processed successfully")
            frame_w, frame_h = processed_frames[0].size
            if frameWidth and frameHeight:
                frame_w, frame_h = (int(frameWidth), int(frameHeight))
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
                sheet.paste(im, (c * frame_w, r * frame_h), im)
            combined_path = output_dir / "gif_spritesheet.png"
            save_rgba_png(sheet, combined_path)
            has_transparency = image_has_transparency(sheet)
            if not combined_path.exists():
                raise HTTPException(status_code=500, detail="Failed to create spritesheet")
            with open(combined_path, "rb") as f:
                b = f.read()
            spritesheet_base64 = base64.b64encode(b).decode("utf-8")
            logger.info(f"   ✅ GIF TO SPRITESHEET COMPLETED: {len(b)} bytes")
            return {
                "success": True,
                "spritesheet": spritesheet_base64,
                "spritesheet_mime": "image/png",
                "has_transparency": has_transparency,
                "config": {
                    "grid": grid,
                    "frames": len(processed_frames),
                    "frameWidth": frame_w,
                    "frameHeight": frame_h,
                    "remove_background": remove_background,
                    "sample_evenly": sample_evenly,
                    "has_transparency": has_transparency,
                },
                "frames_processed": len(processed_frames),
                "spritesheet_size": f"{sheet_w}x{sheet_h}",
                "gif_frames": len(extracted_frames),
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ GIF TO SPRITESHEET FAILED: {e}")
        raise HTTPException(
            status_code=500, detail=f"GIF to spritesheet conversion failed: {str(e)}"
        ) from None
    finally:
        try:
            if "tmp_file_path" in locals() and tmp_file_path.exists():
                tmp_file_path.unlink()
        except Exception:
            pass


@api.post("/extract/gif-frames")
async def extract_gif_frames_endpoint(
    file: UploadFile = File(...), grid: str = Form("auto"), frames: int | None = Form(None)
):
    """Extract frames from GIF without background removal for user selection."""
    logger.info("🖼️ GIF FRAMES EXTRACTION REQUEST STARTED")
    logger.info(f"   File: {file.filename} ({file.size} bytes)")
    logger.info(f"   Grid: {grid}, Frames: {frames}")
    if not file:
        logger.error("❌ No file uploaded")
        raise HTTPException(status_code=400, detail="No file uploaded")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".gif") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = Path(tmp_file.name)
        logger.info(f"   File saved to: {tmp_file_path}")
        from . import remove_bytes
        from .video import extract_gif_frames

        extracted_frames = extract_gif_frames(tmp_file_path, max_frames=None)
        logger.info(f"   Extracted {len(extracted_frames)} frames")
        logger.info("   Pre-processing frames with recommended model...")
        processed_frames = []
        for i, frame in enumerate(extracted_frames):
            try:
                import io

                img_buffer = io.BytesIO()
                frame.save(img_buffer, format="PNG")
                frame_bytes = img_buffer.getvalue()
                processed_bytes = remove_bytes(frame_bytes, model_name="isnet-general-use")
                processed_frame = Image.open(io.BytesIO(processed_bytes)).convert("RGBA")
                processed_frames.append(processed_frame)
                if (i + 1) % 5 == 0:
                    logger.info(f"   Processed {i + 1}/{len(extracted_frames)} frames")
            except Exception as e:
                logger.warning(f"   Failed to process frame {i + 1}: {e}")
                processed_frames.append(frame)
        logger.info(f"   ✅ Pre-processed {len(processed_frames)} frames with isnet-general-use")
        if grid == "auto":
            num_frames = len(extracted_frames)
            cols = int(math.ceil(math.sqrt(num_frames)))
            rows = int(math.ceil(num_frames / cols))
            grid = f"{cols}x{rows}"
            logger.info(f"   Auto-detected grid: {grid}")
        elif frames and frames > 0:
            cols = int(math.ceil(math.sqrt(frames)))
            rows = int(math.ceil(frames / cols))
            suggested_grid = f"{cols}x{rows}"
            logger.info(f"   Suggested grid for {frames} frames: {suggested_grid}")
        try:
            cols, rows = map(int, grid.split("x"))
        except ValueError:
            logger.error("❌ Invalid grid format")
            raise HTTPException(
                status_code=400, detail="Grid must be in format 'colsxrows' (e.g., '5x2')"
            ) from None
        frame_data = []
        for i, (original_frame, processed_frame) in enumerate(
            zip(extracted_frames, processed_frames, strict=False)
        ):
            import io

            orig_buffer = io.BytesIO()
            original_frame.save(orig_buffer, format="PNG")
            orig_bytes = orig_buffer.getvalue()
            proc_buffer = io.BytesIO()
            processed_frame.save(proc_buffer, format="PNG")
            proc_bytes = proc_buffer.getvalue()
            frame_data.append(
                {
                    "index": i,
                    "data": base64.b64encode(proc_bytes).decode("utf-8"),
                    "original_data": base64.b64encode(orig_bytes).decode("utf-8"),
                    "size": len(proc_bytes),
                    "width": processed_frame.width,
                    "height": processed_frame.height,
                    "processed": True,
                    "model": "isnet-general-use",
                }
            )
        tmp_file_path.unlink()
        logger.info("✅ GIF FRAMES EXTRACTION COMPLETED")
        return {
            "success": True,
            "filename": file.filename,
            "grid": grid,
            "cols": cols,
            "rows": rows,
            "total_frames": len(extracted_frames),
            "frames": frame_data,
        }
    except Exception as e:
        logger.error(f"❌ GIF FRAMES EXTRACTION FAILED: {e}")
        try:
            if "tmp_file_path" in locals() and tmp_file_path.exists():
                tmp_file_path.unlink()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Frame extraction failed: {str(e)}") from None


@api.post("/process/frames-with-model")
async def process_frames_with_model_endpoint(
    frames_data: str = Form(...), model: str = Form("isnet-general-use"), grid: str = Form(...)
):
    """Process extracted frames with selected background removal model."""
    logger.info("🎨 FRAMES PROCESSING REQUEST STARTED")
    logger.info(f"   Model: {model}")
    logger.info(f"   Grid: {grid}")
    try:
        import json

        frames = json.loads(frames_data)
        logger.info(f"   Processing {len(frames)} frames")
        cols, rows = map(int, grid.split("x"))
        processed_frames = []
        for frame_info in frames:
            try:
                frame_bytes = base64.b64decode(frame_info["data"])
                processed_bytes = remove_bytes(frame_bytes, model_name=model)
                processed_data = base64.b64encode(processed_bytes).decode("utf-8")
                processed_frames.append(
                    {
                        "index": frame_info["index"],
                        "data": processed_data,
                        "size": len(processed_bytes),
                        "width": frame_info["width"],
                        "height": frame_info["height"],
                    }
                )
            except Exception as e:
                logger.error(f"   Failed to process frame {frame_info['index']}: {e}")
                processed_frames.append(
                    {
                        "index": frame_info["index"],
                        "error": str(e),
                        "original_data": frame_info["data"],
                    }
                )
        logger.info("✅ FRAMES PROCESSING COMPLETED")
        return {"success": True, "model": model, "grid": grid, "processed_frames": processed_frames}
    except Exception as e:
        logger.error(f"❌ FRAMES PROCESSING FAILED: {e}")
        raise HTTPException(status_code=500, detail=f"Frame processing failed: {str(e)}") from None


@api.post("/extract/clothing")
async def extract_clothing_endpoint(
    base_image: UploadFile = File(..., description="Base character image (without clothing)"),
    dressed_image: UploadFile = File(..., description="Dressed character image (with clothing)"),
    threshold: int = Form(10, description="Transparency threshold for cleanup (0-255)"),
):
    """Extract clothing/accessories by subtracting base character from dressed character."""
    logger.info("👕 CLOTHING EXTRACTION REQUEST STARTED")
    logger.info(f"   Base image: {base_image.filename}")
    logger.info(f"   Dressed image: {dressed_image.filename}")
    logger.info(f"   Threshold: {threshold}")
    try:
        import io

        from PIL import Image

        base_data = await base_image.read()
        dressed_data = await dressed_image.read()
        base_img = Image.open(io.BytesIO(base_data)).convert("RGBA")
        dressed_img = Image.open(io.BytesIO(dressed_data)).convert("RGBA")
        logger.info(f"   Base image size: {base_img.size}, mode: {base_img.mode}")
        logger.info(f"   Dressed image size: {dressed_img.size}, mode: {dressed_img.mode}")
        if base_img.size != dressed_img.size:
            logger.info("   Images different sizes, attempting auto-alignment...")
            logger.info(f"   Base: {base_img.size}, Dressed: {dressed_img.size}")
            target_size = (
                max(base_img.size[0], dressed_img.size[0]),
                max(base_img.size[1], dressed_img.size[1]),
            )
            base_img = base_img.resize(target_size, Image.Resampling.LANCZOS)
            dressed_img = dressed_img.resize(target_size, Image.Resampling.LANCZOS)
            logger.info(f"   Resized both images to: {target_size}")
        else:
            logger.info(f"   Images already same size: {base_img.size}")
        base_pixels = base_img.getdata()
        dressed_pixels = dressed_img.getdata()
        logger.info(f"   Base image pixel count: {len(base_pixels)}")
        logger.info(f"   Dressed image pixel count: {len(dressed_pixels)}")
        import numpy as np

        base_array = np.array(base_img)
        dressed_array = np.array(dressed_img)
        diff_array = np.abs(dressed_array.astype(np.float32) - base_array.astype(np.float32))
        rgb_diff = np.sqrt(np.sum(diff_array[:, :, :3] ** 2, axis=2))
        alpha_diff = np.clip(rgb_diff * 2, 0, 255).astype(np.uint8)
        clothing_array = dressed_array.copy()
        clothing_array[:, :, 3] = alpha_diff
        mask = alpha_diff >= threshold
        clothing_array[~mask] = [0, 0, 0, 0]
        clothing = Image.fromarray(clothing_array, "RGBA")
        from PIL import ImageFilter, ImageOps

        clothing = clothing.filter(ImageFilter.GaussianBlur(radius=1))
        rgb_clothing = clothing.convert("RGB")
        enhanced_rgb = ImageOps.autocontrast(rgb_clothing, cutoff=2)
        alpha_channel = clothing.split()[-1]
        clothing = Image.merge("RGBA", (*enhanced_rgb.split(), alpha_channel))
        datas = clothing.getdata()
        newData = []
        for item in datas:
            if item[3] < max(threshold // 2, 5):
                newData.append((0, 0, 0, 0))
            else:
                newData.append(item)
        clothing.putdata(newData)
        clothing_pixels = clothing.getdata()
        non_transparent_pixels = sum(1 for pixel in clothing_pixels if pixel[3] > 0)
        total_pixels = len(clothing_pixels)
        extraction_ratio = non_transparent_pixels / total_pixels * 100
        logger.info(
            f"   Extracted clothing: {non_transparent_pixels}/{total_pixels} non-transparent pixels"
        )
        logger.info(f"   Extraction ratio: {extraction_ratio:.2f}%")
        if extraction_ratio < 1.0:
            logger.info("   Low extraction ratio, trying alternative method...")
            from PIL import ImageFilter

            base_edges = base_img.convert("L").filter(ImageFilter.FIND_EDGES)
            dressed_edges = dressed_img.convert("L").filter(ImageFilter.FIND_EDGES)
            base_edge_array = np.array(base_edges)
            dressed_edge_array = np.array(dressed_edges)
            new_edges = (dressed_edge_array > base_edge_array) & (dressed_edge_array > 50)
            clothing_array = dressed_array.copy()
            clothing_array[:, :, 3] = np.where(new_edges, 255, 0)
            clothing = Image.fromarray(clothing_array, "RGBA")
            clothing_pixels = clothing.getdata()
            non_transparent_pixels = sum(1 for pixel in clothing_pixels if pixel[3] > 0)
            extraction_ratio = non_transparent_pixels / total_pixels * 100
            logger.info(
                "   Alternative method: %s/%s non-transparent pixels",
                non_transparent_pixels,
                total_pixels,
            )
            logger.info(f"   Alternative extraction ratio: {extraction_ratio:.2f}%")
        img_buffer = io.BytesIO()
        clothing.save(img_buffer, format="PNG")
        clothing_bytes = img_buffer.getvalue()
        logger.info("✅ CLOTHING EXTRACTION COMPLETED")
        return Response(
            content=clothing_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": "attachment; filename=extracted_clothing.png",
                "X-Image-Size": f"{clothing.size[0]}x{clothing.size[1]}",
                "X-Image-Mode": clothing.mode,
            },
        )
    except Exception as e:
        logger.error(f"❌ CLOTHING EXTRACTION FAILED: {e}")
        raise HTTPException(
            status_code=500, detail=f"Clothing extraction failed: {str(e)}"
        ) from None


@api.post("/extract/clothing-advanced")
async def extract_clothing_advanced_endpoint(
    base_image: UploadFile = File(..., description="Base character image (without clothing)"),
    dressed_image: UploadFile = File(..., description="Dressed character image (with clothing)"),
    threshold: int = Form(10, description="Transparency threshold for cleanup (0-255)"),
    auto_align: bool = Form(True, description="Automatically align and scale images"),
    scale_factor: float = Form(
        1.0, description="Manual scale factor for base image (1.0 = no scaling)"
    ),
    offset_x: int = Form(0, description="Manual X offset for base image"),
    offset_y: int = Form(0, description="Manual Y offset for base image"),
):
    """Advanced clothing extraction with manual alignment options."""
    logger.info("👕 ADVANCED CLOTHING EXTRACTION REQUEST STARTED")
    logger.info(f"   Base image: {base_image.filename}")
    logger.info(f"   Dressed image: {dressed_image.filename}")
    logger.info(f"   Threshold: {threshold}")
    logger.info(f"   Auto-align: {auto_align}")
    logger.info(f"   Scale factor: {scale_factor}")
    logger.info(f"   Offset: ({offset_x}, {offset_y})")
    try:
        import io

        import numpy as np
        from PIL import Image

        base_data = await base_image.read()
        dressed_data = await dressed_image.read()
        base_img = Image.open(io.BytesIO(base_data)).convert("RGBA")
        dressed_img = Image.open(io.BytesIO(dressed_data)).convert("RGBA")
        logger.info(f"   Original base size: {base_img.size}")
        logger.info(f"   Original dressed size: {dressed_img.size}")
        if auto_align:
            target_size = (
                max(base_img.size[0], dressed_img.size[0]),
                max(base_img.size[1], dressed_img.size[1]),
            )
            base_img = base_img.resize(target_size, Image.Resampling.LANCZOS)
            dressed_img = dressed_img.resize(target_size, Image.Resampling.LANCZOS)
            logger.info(f"   Auto-aligned to: {target_size}")
        else:
            if scale_factor != 1.0:
                new_size = (
                    int(base_img.size[0] * scale_factor),
                    int(base_img.size[1] * scale_factor),
                )
                base_img = base_img.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"   Scaled base to: {new_size}")
            if offset_x != 0 or offset_y != 0:
                new_base = Image.new("RGBA", dressed_img.size, (0, 0, 0, 0))
                new_base.paste(base_img, (offset_x, offset_y))
                base_img = new_base
                logger.info(f"   Applied offset: ({offset_x}, {offset_y})")
        if base_img.size != dressed_img.size:
            target_size = (
                max(base_img.size[0], dressed_img.size[0]),
                max(base_img.size[1], dressed_img.size[1]),
            )
            base_img = base_img.resize(target_size, Image.Resampling.LANCZOS)
            dressed_img = dressed_img.resize(target_size, Image.Resampling.LANCZOS)
        base_array = np.array(base_img)
        dressed_array = np.array(dressed_img)
        diff_array = np.abs(dressed_array.astype(np.float32) - base_array.astype(np.float32))
        rgb_diff = np.sqrt(np.sum(diff_array[:, :, :3] ** 2, axis=2))
        alpha_diff = np.clip(rgb_diff * 2, 0, 255).astype(np.uint8)
        clothing_array = dressed_array.copy()
        clothing_array[:, :, 3] = alpha_diff
        mask = alpha_diff >= threshold
        clothing_array[~mask] = [0, 0, 0, 0]
        clothing = Image.fromarray(clothing_array, "RGBA")
        from PIL import ImageFilter, ImageOps

        clothing = clothing.filter(ImageFilter.GaussianBlur(radius=1))
        rgb_clothing = clothing.convert("RGB")
        enhanced_rgb = ImageOps.autocontrast(rgb_clothing, cutoff=2)
        alpha_channel = clothing.split()[-1]
        clothing = Image.merge("RGBA", (*enhanced_rgb.split(), alpha_channel))
        datas = clothing.getdata()
        newData = []
        for item in datas:
            if item[3] < max(threshold // 2, 5):
                newData.append((0, 0, 0, 0))
            else:
                newData.append(item)
        clothing.putdata(newData)
        clothing_pixels = clothing.getdata()
        non_transparent_pixels = sum(1 for pixel in clothing_pixels if pixel[3] > 0)
        total_pixels = len(clothing_pixels)
        extraction_ratio = non_transparent_pixels / total_pixels * 100
        logger.info(
            f"   Extracted clothing: {non_transparent_pixels}/{total_pixels} non-transparent pixels"
        )
        logger.info(f"   Extraction ratio: {extraction_ratio:.2f}%")
        img_buffer = io.BytesIO()
        clothing.save(img_buffer, format="PNG")
        clothing_bytes = img_buffer.getvalue()
        logger.info("✅ ADVANCED CLOTHING EXTRACTION COMPLETED")
        return Response(
            content=clothing_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": "attachment; filename=extracted_clothing_advanced.png",
                "X-Image-Size": f"{clothing.size[0]}x{clothing.size[1]}",
                "X-Image-Mode": clothing.mode,
                "X-Extraction-Ratio": f"{extraction_ratio:.2f}%",
            },
        )
    except Exception as e:
        logger.error(f"❌ ADVANCED CLOTHING EXTRACTION FAILED: {e}")
        raise HTTPException(
            status_code=500, detail=f"Advanced clothing extraction failed: {str(e)}"
        ) from None


@api.post("/reconstruct/spritesheet")
async def reconstruct_spritesheet_endpoint(
    frames_data: str = Form(...),
    grid: str = Form(...),
    filename: str = Form("reconstructed_spritesheet"),
):
    """Reconstruct spritesheet from processed frames."""
    logger.info("🔧 SPRITESHEET RECONSTRUCTION REQUEST STARTED")
    logger.info(f"   Grid: {grid}")
    logger.info(f"   Filename: {filename}")
    try:
        import json

        frames = json.loads(frames_data)
        logger.info(f"   Reconstructing from {len(frames)} frames")
        cols, rows = map(int, grid.split("x"))
        pil_frames = []
        for frame_info in frames:
            if "error" in frame_info:
                frame_bytes = base64.b64decode(frame_info["original_data"])
            else:
                frame_bytes = base64.b64decode(frame_info["data"])
            import io

            from PIL import Image

            img = Image.open(io.BytesIO(frame_bytes))
            pil_frames.append(img)
        from .cli import _create_spritesheet

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
            spritesheet_path = Path(tmp_file.name)
        _create_spritesheet(pil_frames, cols, rows, spritesheet_path)
        with open(spritesheet_path, "rb") as f:
            spritesheet_bytes = f.read()
        spritesheet_data = base64.b64encode(spritesheet_bytes).decode("utf-8")
        spritesheet_path.unlink()
        logger.info("✅ SPRITESHEET RECONSTRUCTION COMPLETED")
        return {
            "success": True,
            "filename": f"{filename}.png",
            "data": spritesheet_data,
            "size": len(spritesheet_bytes),
            "grid": grid,
            "frames_used": len(pil_frames),
        }
    except Exception as e:
        logger.error(f"❌ SPRITESHEET RECONSTRUCTION FAILED: {e}")
        try:
            if "spritesheet_path" in locals() and spritesheet_path.exists():
                spritesheet_path.unlink()
        except Exception:
            pass
        raise HTTPException(
            status_code=500, detail=f"Spritesheet reconstruction failed: {str(e)}"
        ) from None


def serve(host: str = "127.0.0.1", port: int = 8002):
    uvicorn.run(api, host=host, port=port)
