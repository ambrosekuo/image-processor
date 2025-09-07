"""
Legacy tests for background removal functionality.
These tests are kept for backward compatibility.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from sprite_processor import remove_file


def test_smoke_png():
    """Test basic PNG processing with a 1x1 white pixel."""
    # Create a proper 1x1 PNG using PIL
    from PIL import Image

    sample = Path(__file__).parent / "white1x1.png"
    if not sample.exists():
        # Create a proper 1x1 white PNG
        img = Image.new("RGB", (1, 1), color=(255, 255, 255))
        img.save(sample, format="PNG")

    with patch("sprite_processor.remove") as mock_remove:
        mock_remove.return_value = b"fake_processed_data"

        out = remove_file(str(sample))
        assert isinstance(out, (bytes, bytearray))
        assert out == b"fake_processed_data"


def test_remove_file_with_model():
    """Test remove_file with different model parameter."""
    from PIL import Image

    sample = Path(__file__).parent / "white1x1.png"
    if not sample.exists():
        # Create a proper 1x1 white PNG
        img = Image.new("RGB", (1, 1), color=(255, 255, 255))
        img.save(sample, format="PNG")

    # Test with different models
    models = ["isnet-general-use", "u2net", "u2netp"]
    for model in models:
        with patch("sprite_processor.remove") as mock_remove:
            mock_remove.return_value = b"fake_processed_data"

            out = remove_file(str(sample), model_name=model)
            assert isinstance(out, (bytes, bytearray))
            assert out == b"fake_processed_data"


def test_remove_file_nonexistent():
    """Test remove_file with non-existent file."""
    with pytest.raises(FileNotFoundError):
        remove_file("nonexistent_file.png")
