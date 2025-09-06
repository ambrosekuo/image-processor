# bgremove Usage Guide

This guide provides practical examples and tips for using the bgremove tool effectively.

## Quick Reference

### Basic Commands

```bash
# Single image
bgremove one input.jpg -o output.png

# Spritesheet
bgremove spritesheet sheet.png frames/ --frame-width 64 --frame-height 64

# Batch processing
bgremove batch input_dir/ output_dir/

# Watch mode
bgremove watch input_dir/ output_dir/

# API server
bgremove-api --host 0.0.0.0 --port 8000
```

## Common Use Cases

### 1. Game Development

#### Character Spritesheets
```bash
# Process a character animation spritesheet (recommended)
bgremove spritesheet character_walk.png character_frames/ --grid 5x2

# Process only 6 frames from a 5x2 grid (irregular layout)
bgremove spritesheet character_walk.png character_frames/ --grid 5x2 --frames 6

# Output as a single spritesheet file
bgremove spritesheet character_walk.png character_frames/ --grid 5x2 --frames 6 --output-spritesheet processed_character.png

# Process with pixel dimensions (alternative)
bgremove spritesheet character_idle.png idle_frames/ \
  --frame-width 48 --frame-height 48 --frames-per-row 4
```

#### Tile Sets
```bash
# Process a tile set (recommended)
bgremove spritesheet tiles.png processed_tiles/ --grid 8x4

# Process with pixel dimensions (alternative)
bgremove spritesheet tiles.png processed_tiles/ \
  --frame-width 32 --frame-height 32 --frames-per-row 8
```

### 2. Web Development

#### Product Images
```bash
# Process a single product image
bgremove one product.jpg -o product_transparent.png

# Batch process product photos
bgremove batch product_photos/ processed_products/
```

#### Logo Processing
```bash
# Remove background from logo
bgremove one logo.png -o logo_transparent.png --overwrite
```

### 3. Content Creation

#### Photo Processing
```bash
# Process individual photos
bgremove one photo.jpg

# Process entire photo collection
bgremove batch photos/ processed_photos/ --overwrite
```

#### Asset Preparation
```bash
# Watch folder for new assets
bgremove watch drop_folder/ processed_assets/
```

## Spritesheet Guidelines

### Frame Dimensions
- **Common sizes**: 32x32, 48x48, 64x64, 128x128
- **Power of 2**: Recommended for better performance
- **Consistent size**: All frames should be the same size

### Layout Tips
- **Grid arrangement**: Frames should be arranged in a regular grid
- **No gaps**: Frames should be adjacent without spacing
- **Consistent rows**: All rows should have the same number of frames

### Example Spritesheet Layouts

```
# 2x2 Layout (4 frames)
[Frame 1] [Frame 2]
[Frame 3] [Frame 4]

# 3x2 Layout (6 frames)  
[Frame 1] [Frame 2] [Frame 3]
[Frame 4] [Frame 5] [Frame 6]

# 4x1 Layout (4 frames)
[Frame 1] [Frame 2] [Frame 3] [Frame 4]
```

## API Usage

### Basic API Calls

```bash
# Health check
curl http://localhost:8000/health

# Process image
curl -X POST -F "file=@image.jpg" \
  http://localhost:8000/remove -o output.png
```

### Python API Client

```python
import requests

# Process an image via API
with open('image.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/remove',
        files={'file': f}
    )

if response.status_code == 200:
    with open('output.png', 'wb') as f:
        f.write(response.content)
    print("Image processed successfully!")
```

## Performance Tips

### For Large Spritesheets
- Use smaller frame sizes when possible
- Process in batches if memory is limited
- Consider using watch mode for continuous processing

### For Batch Processing
- Organize files in separate directories
- Use descriptive output directory names
- Enable overwrite mode for re-processing

### For API Usage
- Use appropriate image sizes
- Implement proper error handling
- Consider rate limiting for production use

## Troubleshooting

### Common Issues

**"Output exists (use --overwrite)"**
```bash
# Add the --overwrite flag
bgremove one input.jpg -o output.png --overwrite
```

**Spritesheet dimensions don't match**
```bash
# Check your frame dimensions
bgremove spritesheet sheet.png output/ --frame-width 64 --frame-height 64

# Use --frames-per-row if auto-detection fails
bgremove spritesheet sheet.png output/ \
  --frame-width 64 --frame-height 64 --frames-per-row 4
```

**API server won't start**
```bash
# Install missing dependency
pip install python-multipart

# Check if port is available
lsof -i :8000
```

### Getting Help

```bash
# General help
bgremove --help

# Command-specific help
bgremove spritesheet --help
bgremove one --help
bgremove batch --help
bgremove watch --help
```

## Examples

### Complete Workflow

```bash
# 1. Set up environment
python3 -m venv .venv
source .venv/bin/activate
make dev

# 2. Process a spritesheet
bgremove spritesheet character.png frames/ \
  --frame-width 64 --frame-height 64

# 3. Start API server
bgremove-api --host 0.0.0.0 --port 8000 &

# 4. Test API
curl -X POST -F "file=@test.jpg" \
  http://localhost:8000/remove -o test_output.png
```

### Integration with Game Engines

#### Unity
```csharp
// Use processed frames in Unity
// Place processed PNG files in Assets/Sprites/
// Import as Sprite (2D and UI)
```

#### Godot
```gdscript
# Use processed frames in Godot
# Place in res://sprites/
# Load as Texture2D resources
```

#### Web (HTML5 Canvas)
```javascript
// Load processed frames for web games
const img = new Image();
img.src = 'frame_000_000_processed.png';
img.onload = () => {
    ctx.drawImage(img, x, y);
};
```

## Best Practices

1. **File Organization**: Keep original and processed files separate
2. **Naming Conventions**: Use descriptive names for output directories
3. **Version Control**: Don't commit processed files, only originals
4. **Backup**: Always keep backups of original spritesheets
5. **Testing**: Test with small batches before processing large collections
6. **Documentation**: Document frame dimensions and layouts for team members
