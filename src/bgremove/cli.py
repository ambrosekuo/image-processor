import sys
import time
from pathlib import Path
from typing import Optional

import click
from PIL import Image
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from . import remove_bytes


def _process_one(in_path: Path, out_path: Optional[Path] = None, overwrite: bool = False) -> Path:
    """
    Process a single image file through background removal.
    
    Args:
        in_path: Path to the input image file
        out_path: Path for the output file (auto-generated if None)
        overwrite: Whether to overwrite existing output files
        
    Returns:
        Path to the processed output file
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        FileExistsError: If output file exists and overwrite is False
    """
    if not in_path.exists():
        raise FileNotFoundError(in_path)
    
    # Auto-generate output path if not provided
    if out_path is None:
        out_path = in_path.with_suffix(".png")
    
    # Check for existing output file
    if out_path.exists() and not overwrite:
        raise FileExistsError(f"Output exists (use --overwrite): {out_path}")
    
    # Read image bytes and process through rembg
    img = in_path.read_bytes()
    cut = remove_bytes(img)
    out_path.write_bytes(cut)
    return out_path


@click.group()
def app() -> None:
    """bgremove CLI: background removal via rembg."""
    pass


@app.command("one")
@click.argument("input", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", type=click.Path(dir_okay=False, path_type=Path))
@click.option("--overwrite", is_flag=True, help="Overwrite existing output file.")
def one(input: Path, output: Optional[Path], overwrite: bool) -> None:
    """Process a single file."""
    out = _process_one(input, output, overwrite)
    click.echo(f"Saved: {out}")


@app.command("batch")
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("output_dir", type=click.Path(file_okay=False, path_type=Path))
@click.option("--overwrite", is_flag=True)
def batch(input_dir: Path, output_dir: Path, overwrite: bool) -> None:
    """Process all images in INPUT_DIR to OUTPUT_DIR."""
    output_dir.mkdir(parents=True, exist_ok=True)
    exts = {".png", ".jpg", ".jpeg", ".webp"}
    count = 0
    for p in input_dir.iterdir():
        if p.suffix.lower() in exts and p.is_file():
            out = output_dir / (p.stem + ".png")
            try:
                _process_one(p, out, overwrite)
                count += 1
            except FileExistsError:
                if overwrite:
                    raise
                click.echo(f"Skip exists: {out}")
    click.echo(f"Done. Processed: {count}")


class _WatchHandler(FileSystemEventHandler):
    """
    File system event handler for watch mode.
    
    Monitors a directory for new or modified image files and automatically
    processes them through background removal.
    """
    
    def __init__(self, out_dir: Path, overwrite: bool) -> None:
        """Initialize the watch handler with output directory and overwrite setting."""
        self.out_dir = out_dir
        self.overwrite = overwrite
        # Supported image file extensions
        self.exts = {".png", ".jpg", ".jpeg", ".webp"}

    def on_created(self, event):
        """Handle file creation events."""
        self._maybe_process(event.src_path)

    def on_modified(self, event):
        """Handle file modification events."""
        self._maybe_process(event.src_path)

    def _maybe_process(self, path_str: str) -> None:
        """
        Process a file if it's a supported image format.
        
        Args:
            path_str: Path to the file to potentially process
        """
        p = Path(path_str)
        
        # Skip directories and unsupported file types
        if p.is_dir() or p.suffix.lower() not in self.exts:
            return
        
        # Generate output path
        out = self.out_dir / (p.stem + ".png")
        
        try:
            _process_one(p, out, self.overwrite)
            print(f"[watch] Saved: {out}")
        except FileExistsError:
            if not self.overwrite:
                print(f"[watch] Skip exists: {out}")


@app.command("spritesheet")
@click.argument("input", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output_dir", type=click.Path(file_okay=False, path_type=Path))
@click.option("--frame-width", type=int, required=True, help="Width of each frame in pixels")
@click.option("--frame-height", type=int, required=True, help="Height of each frame in pixels")
@click.option("--frames-per-row", type=int, help="Number of frames per row (auto-detect if not specified)")
@click.option("--overwrite", is_flag=True, help="Overwrite existing output files.")
def spritesheet(input: Path, output_dir: Path, frame_width: int, frame_height: int, frames_per_row: Optional[int], overwrite: bool) -> None:
    """
    Process a spritesheet by splitting into frames and removing background from each.
    
    This command is perfect for game development where you have character animations,
    tile sets, or other multi-frame images that need background removal.
    
    The spritesheet is automatically divided into a grid based on the frame dimensions,
    and each frame is processed individually through the background removal algorithm.
    """
    if not input.exists():
        raise FileNotFoundError(input)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load the spritesheet image
    with Image.open(input) as img:
        sheet_width, sheet_height = img.size
        
        # Auto-detect frames per row if not specified
        # This assumes frames are arranged in a regular grid
        if frames_per_row is None:
            frames_per_row = sheet_width // frame_width
        
        # Calculate the grid dimensions
        frames_per_col = sheet_height // frame_height
        total_frames = frames_per_row * frames_per_col
        
        # Display processing information
        click.echo(f"Spritesheet: {sheet_width}x{sheet_height}")
        click.echo(f"Frame size: {frame_width}x{frame_height}")
        click.echo(f"Frames per row: {frames_per_row}")
        click.echo(f"Total frames: {total_frames}")
        
        processed = 0
        # Process each frame in the grid
        for row in range(frames_per_col):
            for col in range(frames_per_row):
                # Calculate the pixel coordinates for this frame
                x = col * frame_width
                y = row * frame_height
                
                # Extract the frame from the spritesheet
                frame = img.crop((x, y, x + frame_width, y + frame_height))
                
                # Save the frame temporarily for processing
                # We need to save it because rembg expects file paths, not PIL Images
                frame_path = output_dir / f"frame_{row:03d}_{col:03d}.png"
                frame.save(frame_path)
                
                try:
                    # Define the output path for the processed frame
                    out_path = output_dir / f"frame_{row:03d}_{col:03d}_processed.png"
                    
                    # Skip if output exists and overwrite is not enabled
                    if out_path.exists() and not overwrite:
                        click.echo(f"Skip exists: {out_path}")
                        continue
                    
                    # Process the frame through background removal
                    _process_one(frame_path, out_path, overwrite)
                    processed += 1
                    click.echo(f"Processed frame {row*frames_per_row + col + 1}/{total_frames}: {out_path}")
                    
                    # Clean up the temporary frame file
                    frame_path.unlink()
                    
                except Exception as e:
                    click.echo(f"Error processing frame {row*frames_per_row + col + 1}: {e}", err=True)
                    # Ensure temporary file is cleaned up even on error
                    if frame_path.exists():
                        frame_path.unlink()
    
    click.echo(f"Done. Processed: {processed}/{total_frames} frames")


@app.command("watch")
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("output_dir", type=click.Path(file_okay=False, path_type=Path))
@click.option("--overwrite", is_flag=True, help="Overwrite outputs when source changes.")
def watch(input_dir: Path, output_dir: Path, overwrite: bool) -> None:
    """Watch INPUT_DIR and auto-export processed PNGs to OUTPUT_DIR."""
    output_dir.mkdir(parents=True, exist_ok=True)
    handler = _WatchHandler(output_dir, overwrite)
    obs = Observer()
    obs.schedule(handler, str(input_dir), recursive=False)
    obs.start()
    print(f"Watching {input_dir} → {output_dir} (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        obs.stop()
    obs.join()


if __name__ == "__main__":
    # Allows python -m bgremove.cli ...
    try:
        app()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
