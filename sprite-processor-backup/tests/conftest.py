"""
Test configuration and fixtures for sprite-processor.
"""

import io
import shutil
import tempfile
from pathlib import Path

import pytest
from PIL import Image, ImageDraw


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_image():
    """Create a sample test image."""
    img = Image.new("RGB", (64, 64), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Draw a simple red circle
    draw.ellipse([16, 16, 48, 48], fill=(255, 0, 0))
    return img


@pytest.fixture
def sample_image_bytes(sample_image):
    """Convert sample image to bytes."""
    img_bytes = io.BytesIO()
    sample_image.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


@pytest.fixture
def sample_spritesheet():
    """Create a sample spritesheet with 4 frames (2x2 grid)."""
    # Create a 2x2 spritesheet (128x128 total)
    spritesheet = Image.new("RGB", (128, 128), color=(255, 255, 255))
    draw = ImageDraw.Draw(spritesheet)

    # Frame 1 (top-left): Red circle
    draw.ellipse([16, 16, 48, 48], fill=(255, 0, 0))

    # Frame 2 (top-right): Green square
    draw.rectangle([80, 16, 112, 48], fill=(0, 255, 0))

    # Frame 3 (bottom-left): Blue triangle
    draw.polygon([(16, 80), (48, 80), (32, 112)], fill=(0, 0, 255))

    # Frame 4 (bottom-right): Yellow diamond
    draw.polygon([(80, 96), (96, 80), (112, 96), (96, 112)], fill=(255, 255, 0))

    return spritesheet


@pytest.fixture
def sample_gif():
    """Create a sample animated GIF."""
    frames = []
    for i in range(4):
        img = Image.new("RGB", (32, 32), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        # Draw a moving circle
        x = i * 8
        draw.ellipse([x, 8, x + 16, 24], fill=(255, 0, 0))
        frames.append(img)

    # Save as GIF
    gif_bytes = io.BytesIO()
    frames[0].save(
        gif_bytes, format="GIF", save_all=True, append_images=frames[1:], duration=200, loop=0
    )
    return gif_bytes.getvalue()


@pytest.fixture
def sample_video_file(temp_dir):
    """Create a sample video file for testing."""
    # For testing purposes, we'll create a simple video file
    # In real tests, you might want to use a small test video
    video_path = temp_dir / "test_video.mp4"
    # This is a placeholder - in real tests you'd use a small test video
    video_path.write_bytes(b"fake video content")
    return video_path


@pytest.fixture
def mock_rembg_session():
    """Mock rembg session for testing."""

    class MockSession:
        def __init__(self, model_name):
            self.model_name = model_name

        def predict(self, img, *args, **kwargs):
            # Return a proper mask image (not bytes)
            # The rembg library expects a mask image, not bytes
            mask = Image.new("L", img.size, color=255)  # White mask (foreground)
            return [mask]  # Return as list of masks

    return MockSession


@pytest.fixture
def api_client():
    """Create a test client for the API."""
    from fastapi.testclient import TestClient

    from sprite_processor.api import api

    return TestClient(api)
