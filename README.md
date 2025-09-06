# bgremove

A powerful local background removal tool built on [`rembg`](https://github.com/danielgatis/rembg). Includes a Python CLI, FastAPI server, and specialized spritesheet processing capabilities.

## Features

- 🖼️ **Single Image Processing** - Remove backgrounds from individual images
- 📁 **Batch Processing** - Process entire directories of images
- 🎬 **Spritesheet Processing** - Automatically split and process spritesheets frame by frame
- 🔄 **Watch Mode** - Monitor directories for new images and process them automatically
- 🌐 **REST API** - FastAPI server for programmatic access
- ⚡ **Fast & Local** - No cloud dependencies, runs entirely on your machine

## Quick Start

### Installation

```bash
# Clone the repository
git clone <your-repo-url> rembg-tool && cd rembg-tool

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
make dev
```

### Basic Usage

```bash
# Process a single image
bgremove one input.jpg -o output.png

# Process a spritesheet
bgremove spritesheet spritesheet.png output_dir --frame-width 64 --frame-height 64

# Start API server
bgremove-api --host 0.0.0.0 --port 8000
```

## CLI Commands

### 1. Single Image Processing

Process one image at a time:

```bash
bgremove one <input-file> [options]
```

**Options:**
- `-o, --output <path>`: Output file path (default: input with .png extension)
- `--overwrite`: Overwrite existing output file

**Examples:**
```bash
# Basic usage
bgremove one photo.jpg -o photo_no_bg.png

# Auto-generate output name
bgremove one photo.jpg

# Overwrite existing file
bgremove one photo.jpg -o output.png --overwrite
```

### 2. Spritesheet Processing

Process spritesheets by splitting them into individual frames:

```bash
bgremove spritesheet <spritesheet-file> <output-directory> [options]
```

**Options:**
- `--grid <WIDTHxHEIGHT>`: Grid layout (e.g., '5x2' for 5 frames per row, 2 rows) - **Recommended**
- `--frames <int>`: Total number of frames to process (for irregular layouts)
- `--output-spritesheet <file>`: Output as a single spritesheet file instead of individual frames
- `--frame-width <int>`: Width of each frame in pixels (alternative to --grid)
- `--frame-height <int>`: Height of each frame in pixels (alternative to --grid)
- `--frames-per-row <int>`: Number of frames per row (auto-detected if not specified)
- `--overwrite`: Overwrite existing output files

**Examples:**
```bash
# Process using grid layout (recommended)
bgremove spritesheet character.png frames/ --grid 5x2

# Process only 6 frames from a 5x2 grid (irregular layout)
bgremove spritesheet character.png frames/ --grid 5x2 --frames 6

# Output as a single spritesheet file
bgremove spritesheet character.png frames/ --grid 5x2 --frames 6 --output-spritesheet processed_character.png

# Process using pixel dimensions
bgremove spritesheet tiles.png tiles_output/ --frame-width 32 --frame-height 32

# Process with specific layout (4 frames per row)
bgremove spritesheet tiles.png tiles_output/ --frame-width 32 --frame-height 32 --frames-per-row 4

# Overwrite existing files
bgremove spritesheet animation.png anim_frames/ --grid 4x3 --overwrite
```

**Output:**
- **Individual frames**: Each frame is saved as `frame_<row>_<col>_processed.png`
- **Combined spritesheet**: Single file with all processed frames arranged in a grid
- Files are numbered by row and column (e.g., `frame_000_000_processed.png`)
- All frames have transparent backgrounds after processing

### 3. Batch Processing

Process all images in a directory:

```bash
bgremove batch <input-directory> <output-directory> [options]
```

**Options:**
- `--overwrite`: Overwrite existing output files

**Examples:**
```bash
# Process all images in a folder
bgremove batch input_photos/ processed_photos/

# Overwrite existing files
bgremove batch photos/ output/ --overwrite
```

**Supported formats:** PNG, JPG, JPEG, WEBP

### 4. Watch Mode

Monitor a directory and automatically process new images:

```bash
bgremove watch <input-directory> <output-directory> [options]
```

**Options:**
- `--overwrite`: Overwrite outputs when source changes

**Examples:**
```bash
# Watch for new images
bgremove watch drop_folder/ processed_folder/

# Auto-overwrite on changes
bgremove watch input/ output/ --overwrite
```

**Usage:** Press `Ctrl+C` to stop watching.

## REST API

### Starting the Server

```bash
bgremove-api --host 0.0.0.0 --port 8000
```

### API Endpoints

#### Health Check
```bash
GET /health
```

**Response:**
```json
{"ok": true}
```

#### Remove Background
```bash
POST /remove
```

**Parameters:**
- `file`: Image file (multipart/form-data)
- `filename`: Optional custom filename

**Examples:**
```bash
# Using curl
curl -X POST -F "file=@image.jpg" http://localhost:8000/remove -o output.png

# With custom filename
curl -X POST -F "file=@image.jpg" -F "filename=my_image" http://localhost:8000/remove -o output.png
```

**Response:** PNG image with transparent background

## Development

### Project Structure

```
rembg-tool/
├── src/bgremove/
│   ├── __init__.py      # Core background removal functions
│   ├── cli.py           # Command-line interface
│   └── api.py           # FastAPI server
├── tests/               # Test files
├── pyproject.toml       # Project configuration
└── README.md           # This file
```

### Available Make Commands

```bash
# Install development dependencies
make dev

# Run tests
make test

# Format code
make format

# Lint code
make lint

# Install pre-commit hooks
make pre-commit
```

### Dependencies

**Core:**
- `rembg>=2.0.57` - Background removal engine
- `Pillow>=10.4.0` - Image processing
- `click>=8.0.0` - CLI framework
- `fastapi>=0.115.0` - Web API framework
- `uvicorn>=0.30.0` - ASGI server
- `watchdog>=4.0.0` - File system monitoring
- `python-multipart` - File upload support

**Development:**
- `pytest>=8.3.0` - Testing framework
- `ruff>=0.6.0` - Linting
- `black>=24.8.0` - Code formatting
- `isort>=5.13.2` - Import sorting

## Use Cases

### Game Development
- Process character spritesheets
- Remove backgrounds from tile sets
- Batch process UI elements

### Web Development
- Process product images
- Create transparent logos
- Optimize images for web

### Content Creation
- Remove backgrounds from photos
- Process image collections
- Create transparent assets

## Troubleshooting

### Common Issues

**"Form data requires python-multipart"**
```bash
pip install python-multipart
```

**"Output exists (use --overwrite)"**
```bash
# Add --overwrite flag
bgremove one input.jpg -o output.png --overwrite
```

**Spritesheet processing fails**
- Verify frame dimensions are correct
- Check that spritesheet dimensions are divisible by frame size
- Use `--frames-per-row` if auto-detection fails

### Performance Tips

- Use smaller frame sizes for spritesheets when possible
- Process images in batches for better performance
- Use watch mode for continuous processing workflows

## License

This project is built on top of `rembg` and follows the same licensing terms.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the command help: `bgremove --help`
3. Open an issue on GitHub