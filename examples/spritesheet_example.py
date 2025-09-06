#!/usr/bin/env python3
"""
Example script demonstrating spritesheet processing with bgremove.

This script creates a sample spritesheet and processes it using the bgremove tool.
"""

import subprocess
import sys
from pathlib import Path

def create_sample_spritesheet():
    """Create a sample spritesheet for demonstration."""
    from PIL import Image, ImageDraw
    
    # Create a 3x2 spritesheet with 32x32 frames
    frame_width, frame_height = 32, 32
    frames_per_row = 3
    frames_per_col = 2
    
    sheet_width = frame_width * frames_per_row
    sheet_height = frame_height * frames_per_col
    
    # Create the spritesheet with a light background
    spritesheet = Image.new('RGB', (sheet_width, sheet_height), 'lightblue')
    draw = ImageDraw.Draw(spritesheet)
    
    # Draw different colored shapes in each frame
    shapes = [
        ('ellipse', 'red'),
        ('rectangle', 'blue'), 
        ('polygon', 'green'),
        ('ellipse', 'yellow'),
        ('rectangle', 'purple'),
        ('polygon', 'orange')
    ]
    
    for row in range(frames_per_col):
        for col in range(frames_per_row):
            x = col * frame_width
            y = row * frame_height
            
            center_x = x + frame_width // 2
            center_y = y + frame_height // 2
            
            shape_type, color = shapes[row * frames_per_row + col]
            
            if shape_type == 'ellipse':
                draw.ellipse([center_x - 12, center_y - 12, 
                             center_x + 12, center_y + 12], 
                            fill=color, outline='black', width=1)
            elif shape_type == 'rectangle':
                draw.rectangle([center_x - 12, center_y - 12, 
                               center_x + 12, center_y + 12], 
                              fill=color, outline='black', width=1)
            elif shape_type == 'polygon':
                # Draw a triangle
                points = [(center_x, center_y - 12), 
                         (center_x - 12, center_y + 12), 
                         (center_x + 12, center_y + 12)]
                draw.polygon(points, fill=color, outline='black', width=1)
    
    # Save the spritesheet
    output_path = Path('sample_spritesheet.png')
    spritesheet.save(output_path)
    print(f"Created sample spritesheet: {output_path}")
    print(f"Size: {sheet_width}x{sheet_height}")
    print(f"Frame size: {frame_width}x{frame_height}")
    print(f"Frames: {frames_per_row}x{frames_per_col} = {frames_per_row * frames_per_col}")
    
    return output_path

def process_spritesheet(spritesheet_path):
    """Process the spritesheet using bgremove."""
    output_dir = Path('spritesheet_output')
    
    # Run the bgremove spritesheet command
    cmd = [
        'bgremove', 'spritesheet',
        str(spritesheet_path),
        str(output_dir),
        '--frame-width', '32',
        '--frame-height', '32',
        '--overwrite'
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Spritesheet processed successfully!")
        print(result.stdout)
        
        # List the output files
        if output_dir.exists():
            output_files = list(output_dir.glob('*.png'))
            print(f"\n📁 Output files ({len(output_files)}):")
            for file in sorted(output_files):
                print(f"  - {file.name}")
    else:
        print("❌ Error processing spritesheet:")
        print(result.stderr)
        return False
    
    return True

def main():
    """Main function to run the example."""
    print("🎬 Spritesheet Processing Example")
    print("=" * 40)
    
    try:
        # Create sample spritesheet
        spritesheet_path = create_sample_spritesheet()
        
        # Process the spritesheet
        success = process_spritesheet(spritesheet_path)
        
        if success:
            print("\n🎉 Example completed successfully!")
            print("\nYou can now:")
            print("1. View the original spritesheet: sample_spritesheet.png")
            print("2. Check the processed frames in: spritesheet_output/")
            print("3. Use these frames in your game or application")
        else:
            print("\n❌ Example failed. Check the error messages above.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
