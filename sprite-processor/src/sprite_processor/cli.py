import sys
import time
from pathlib import Path
from typing import Optional

import click
from PIL import Image
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from . import remove_bytes


def _process_one(in_path: Path, out_path: Optional[Path] = None, overwrite: bool = False, model_name: str = "isnet-general-use") -> Path:
    """
    Process a single image file through background removal.
    
    Args:
        in_path: Path to the input image file
        out_path: Path for the output file (auto-generated if None)
        overwrite: Whether to overwrite existing output files
        model_name: Name of the rembg model to use
        
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
    
    # Read image bytes and process through rembg with specified model
    img = in_path.read_bytes()
    cut = remove_bytes(img, model_name=model_name)
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
@click.option("--frame-width", type=int, help="Width of each frame in pixels (alternative to --grid)")
@click.option("--frame-height", type=int, help="Height of each frame in pixels (alternative to --grid)")
@click.option("--grid", type=str, help="Grid layout as 'WIDTHxHEIGHT' (e.g., '5x2' for 5 frames per row, 2 rows)")
@click.option("--frames", type=int, help="Total number of frames to process (for irregular layouts)")
@click.option("--frames-per-row", type=int, help="Number of frames per row (auto-detect if not specified)")
@click.option("--output-spritesheet", type=click.Path(dir_okay=False, path_type=Path), help="Output as a single spritesheet file instead of individual frames")
@click.option("--overwrite", is_flag=True, help="Overwrite existing output files.")
def spritesheet(input: Path, output_dir: Path, frame_width: Optional[int], frame_height: Optional[int], grid: Optional[str], frames: Optional[int], frames_per_row: Optional[int], output_spritesheet: Optional[Path], overwrite: bool) -> None:
    """
    Process a spritesheet by splitting into frames and removing background from each.
    
    This command is perfect for game development where you have character animations,
    tile sets, or other multi-frame images that need background removal.
    
    The spritesheet is automatically divided into a grid based on the frame dimensions,
    and each frame is processed individually through the background removal algorithm.
    
    Examples:
        # Using grid layout (recommended for most spritesheets)
        bgremove spritesheet character.png frames/ --grid 5x2
        
        # Using pixel dimensions
        bgremove spritesheet tiles.png tiles/ --frame-width 32 --frame-height 32
    """
    if not input.exists():
        raise FileNotFoundError(input)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load the spritesheet image
    with Image.open(input) as img:
        sheet_width, sheet_height = img.size
        
        # Parse grid layout if provided
        if grid:
            try:
                frames_per_row, frames_per_col = map(int, grid.split('x'))
                # Calculate frame dimensions from grid
                frame_width = sheet_width // frames_per_row
                frame_height = sheet_height // frames_per_col
            except ValueError:
                raise click.BadParameter("Grid must be in format 'WIDTHxHEIGHT' (e.g., '5x2')")
        elif frame_width and frame_height:
            # Use provided pixel dimensions
            frames_per_row = frames_per_row or (sheet_width // frame_width)
            frames_per_col = sheet_height // frame_height
        else:
            raise click.BadParameter(
                "Either --grid (e.g., '5x2') or --frame-width and --frame-height must be provided"
            )
        
        # Validate dimensions
        if sheet_width % frames_per_row != 0:
            raise click.BadParameter(
                f"Spritesheet width ({sheet_width}) is not divisible by frames per row ({frames_per_row})"
            )
        if sheet_height % frames_per_col != 0:
            raise click.BadParameter(
                f"Spritesheet height ({sheet_height}) is not divisible by frames per column ({frames_per_col})"
            )
        
        total_frames = frames_per_row * frames_per_col
        max_frames = frames or total_frames
        
        # Display processing information
        click.echo(f"Spritesheet: {sheet_width}x{sheet_height}")
        click.echo(f"Frame size: {frame_width}x{frame_height}")
        click.echo(f"Grid: {frames_per_row}x{frames_per_col}")
        click.echo(f"Total frames: {total_frames}")
        if frames:
            click.echo(f"Processing: {max_frames} frames")
        
        processed = 0
        frame_count = 0
        processed_frames = []  # Store processed frames for spritesheet output
        
        # Process each frame in the grid
        for row in range(frames_per_col):
            if frames and frame_count >= max_frames:
                break
            for col in range(frames_per_row):
                # Stop if we've processed the requested number of frames
                if frames and frame_count >= max_frames:
                    break
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
                        # Load existing processed frame for spritesheet
                        if output_spritesheet:
                            processed_frames.append(Image.open(out_path))
                        frame_count += 1
                        continue
                    
                    # Process the frame through background removal
                    _process_one(frame_path, out_path, overwrite)
                    processed += 1
                    frame_count += 1
                    click.echo(f"Processed frame {frame_count}/{max_frames}: {out_path}")
                    
                    # Load processed frame for spritesheet output
                    if output_spritesheet:
                        processed_frames.append(Image.open(out_path))
                    
                    # Clean up the temporary frame file
                    frame_path.unlink()
                    
                except Exception as e:
                    click.echo(f"Error processing frame {frame_count + 1}: {e}", err=True)
                    # Ensure temporary file is cleaned up even on error
                    if frame_path.exists():
                        frame_path.unlink()
                    frame_count += 1
        
        # Create combined spritesheet if requested
        if output_spritesheet and processed_frames:
            click.echo(f"Creating combined spritesheet: {output_spritesheet}")
            
            # Calculate the layout for the combined spritesheet
            num_frames = len(processed_frames)
            if frames_per_row:
                cols = min(frames_per_row, num_frames)
                rows = (num_frames + cols - 1) // cols  # Ceiling division
            else:
                # Auto-arrange in a roughly square layout
                cols = int(num_frames ** 0.5)
                if cols * cols < num_frames:
                    cols += 1
                rows = (num_frames + cols - 1) // cols
            
            # Create the combined spritesheet
            combined_width = cols * frame_width
            combined_height = rows * frame_height
            combined_img = Image.new('RGBA', (combined_width, combined_height), (0, 0, 0, 0))
            
            # Place each processed frame in the combined image
            for i, processed_frame in enumerate(processed_frames):
                row = i // cols
                col = i % cols
                x = col * frame_width
                y = row * frame_height
                combined_img.paste(processed_frame, (x, y))
            
            # Save the combined spritesheet
            combined_img.save(output_spritesheet)
            click.echo(f"Saved combined spritesheet: {output_spritesheet}")
            click.echo(f"Combined layout: {cols}x{rows} ({num_frames} frames)")
    
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


@app.command()
@click.argument('input', type=click.Path(exists=True, path_type=Path))
@click.option('-o', '--output', type=click.Path(path_type=Path), help='Output GIF file path')
@click.option('--fps', type=int, default=10, help='Frames per second for output GIF')
@click.option('--duration', type=float, help='Maximum duration in seconds')
@click.option('--max-width', type=int, default=480, help='Maximum width for output GIF')
@click.option('--max-height', type=int, default=480, help='Maximum height for output GIF')
@click.option('--overwrite', is_flag=True, help='Overwrite existing output files')
def video(input: Path, output: Optional[Path], fps: int, duration: Optional[float], 
          max_width: int, max_height: int, overwrite: bool) -> None:
    """
    Convert video to GIF with custom settings.
    
    Examples:
        sprite-processor video input.mp4 -o output.gif --fps 10 --duration 5
        sprite-processor video input.mp4 --fps 15 --max-width 640
    """
    if output is None:
        output = input.with_suffix('.gif')
    
    if output.exists() and not overwrite:
        click.echo(f"Error: Output exists (use --overwrite): {output}", err=True)
        return
    
    try:
        from .video import video_to_gif
        result_path = video_to_gif(
            input, output, fps=fps, duration=duration, 
            max_width=max_width, max_height=max_height
        )
        click.echo(f"✅ Video converted to GIF: {result_path}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@app.command()
@click.argument('input', type=click.Path(exists=True, path_type=Path))
@click.option('-o', '--output', type=click.Path(path_type=Path), help='Output spritesheet file path')
@click.option('--grid', required=True, help='Grid layout (e.g., "5x2")')
@click.option('--frames', type=int, help='Number of frames to extract')
@click.option('--fps', type=int, default=10, help='Frames per second for extraction')
@click.option('--duration', type=float, help='Maximum duration in seconds')
@click.option('--overwrite', is_flag=True, help='Overwrite existing output files')
def video_spritesheet(input: Path, output: Optional[Path], grid: str, frames: Optional[int],
                     fps: int, duration: Optional[float], overwrite: bool) -> None:
    """
    Convert video directly to spritesheet by extracting frames.
    
    Examples:
        sprite-processor video-spritesheet input.mp4 --grid 5x2 --frames 6
        sprite-processor video-spritesheet input.mp4 --grid 4x2 --fps 15 --duration 3
    """
    if output is None:
        output = input.with_suffix('_spritesheet.png')
    
    if output.exists() and not overwrite:
        click.echo(f"Error: Output exists (use --overwrite): {output}", err=True)
        return
    
    try:
        from .video import video_to_spritesheet
        result_path = video_to_spritesheet(
            input, output, grid=grid, frames=frames, 
            fps=fps, duration=duration
        )
        click.echo(f"✅ Video converted to spritesheet: {result_path}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@app.command()
@click.argument('input', type=click.Path(exists=True, path_type=Path))
@click.option('-o', '--output-dir', type=click.Path(path_type=Path), help='Output directory')
@click.option('--fps', type=int, default=10, help='Frames per second for GIF')
@click.option('--duration', type=float, help='Maximum duration in seconds')
@click.option('--grid', default='5x2', help='Grid layout for spritesheet (e.g., "5x2")')
@click.option('--frames', type=int, help='Number of frames to extract')
@click.option('--model', default='isnet-general-use', help='Background removal model')
@click.option('--all-models', is_flag=True, help='Process with all available models')
@click.option('--keep-intermediates', is_flag=True, help='Keep intermediate files (GIF, spritesheet)')
@click.option('--overwrite', is_flag=True, help='Overwrite existing output files')
def pipeline(input: Path, output_dir: Optional[Path], fps: int, duration: Optional[float],
            grid: str, frames: Optional[int], model: str, all_models: bool,
            keep_intermediates: bool, overwrite: bool) -> None:
    """
    Complete pipeline: Video → GIF → Spritesheet → Background Removal
    
    Examples:
        sprite-processor pipeline input.mp4 --fps 10 --grid 5x2 --frames 6
        sprite-processor pipeline input.mp4 --all-models --keep-intermediates
        sprite-processor pipeline input.mp4 --duration 3 --grid 4x2
    """
    if output_dir is None:
        output_dir = input.parent / f"{input.stem}_processed"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        from .pipeline import VideoPipelineConfig, process_video_pipeline, process_video_pipeline_all_models
        
        config = VideoPipelineConfig(
            fps=fps,
            duration=duration,
            grid=grid,
            frames=frames,
            model=model
        )
        
        if all_models:
            results = process_video_pipeline_all_models(input, output_dir, config, keep_intermediates)
            successful_models = sum(1 for r in results['model_results'].values() if r['success'])
            click.echo(f"✅ Pipeline completed! {successful_models}/6 models successful")
            click.echo(f"Results saved to: {output_dir}")
        else:
            results = process_video_pipeline(input, output_dir, config, keep_intermediates)
            click.echo(f"✅ Pipeline completed!")
            click.echo(f"GIF: {results['gif_path']}")
            click.echo(f"Spritesheet: {results['spritesheet_path']}")
            click.echo(f"Processed: {results['processed_path']}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@app.command()
@click.argument('input', type=click.Path(exists=True, path_type=Path))
def analyze(input: Path) -> None:
    """
    Analyze video and provide recommendations for processing.
    
    Examples:
        sprite-processor analyze input.mp4
    """
    try:
        from .pipeline import analyze_video_for_pipeline
        
        analysis = analyze_video_for_pipeline(input)
        
        click.echo(f"📹 Video Analysis: {input.name}")
        click.echo(f"   Duration: {analysis['video_analysis']['duration']:.1f}s")
        click.echo(f"   FPS: {analysis['video_analysis']['fps']:.1f}")
        click.echo(f"   Size: {analysis['video_analysis']['size'][0]}x{analysis['video_analysis']['size'][1]}")
        click.echo(f"   File Size: {analysis['video_analysis']['file_size'] / 1024 / 1024:.1f} MB")
        click.echo()
        
        click.echo("💡 Recommended Settings:")
        rec = analysis['recommendations']
        click.echo(f"   FPS: {rec['fps']}")
        click.echo(f"   Duration: {rec['duration']:.1f}s")
        click.echo(f"   Grid: {rec['grid']}")
        click.echo(f"   Frames: {rec['frames']}")
        click.echo(f"   Max Size: {rec['max_width']}x{rec['max_height']}")
        click.echo(f"   Estimated Processing Time: {rec['estimated_processing_time']}")
        click.echo()
        
        click.echo("🚀 Suggested Command:")
        click.echo(f"   sprite-processor pipeline {input.name} --fps {rec['fps']} --duration {rec['duration']:.1f} --grid {rec['grid']} --frames {rec['frames']}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


if __name__ == "__main__":
    # Allows python -m bgremove.cli ...
    try:
        app()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
