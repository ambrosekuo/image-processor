"""
Tests for core sprite-processor functions.
"""

from unittest.mock import patch

import pytest

from sprite_processor import remove_bytes, remove_file


class TestRemoveBytes:
    """Test the remove_bytes function."""

    def test_remove_bytes_basic(self, sample_image_bytes, mock_rembg_session):
        """Test basic background removal functionality."""
        with patch(
            "sprite_processor.new_session", return_value=mock_rembg_session("isnet-general-use")
        ):
            result = remove_bytes(sample_image_bytes)

            # Should return bytes
            assert isinstance(result, bytes)
            # Should be a PNG (starts with PNG signature)
            assert result.startswith(b"\x89PNG\r\n\x1a\n")

    def test_remove_bytes_different_models(self, sample_image_bytes, mock_rembg_session):
        """Test remove_bytes with different model names."""
        models = [
            "isnet-general-use",
            "u2net_human_seg",
            "u2net",
            "u2netp",
            "u2net_cloth_seg",
            "silueta",
        ]

        for model in models:
            with patch("sprite_processor.new_session", return_value=mock_rembg_session(model)):
                result = remove_bytes(sample_image_bytes, model_name=model)
                assert isinstance(result, bytes)
                assert result.startswith(b"\x89PNG\r\n\x1a\n")

    def test_remove_bytes_invalid_data(self):
        """Test remove_bytes with invalid image data."""
        with pytest.raises(Exception):  # rembg will raise an exception for invalid data
            remove_bytes(b"invalid image data")

    def test_remove_bytes_empty_data(self):
        """Test remove_bytes with empty data."""
        with pytest.raises(Exception):
            remove_bytes(b"")


class TestRemoveFile:
    """Test the remove_file function."""

    def test_remove_file_basic(self, temp_dir, sample_image_bytes, mock_rembg_session):
        """Test basic file processing."""
        # Create a test image file
        test_file = temp_dir / "test_image.png"
        test_file.write_bytes(sample_image_bytes)

        with patch(
            "sprite_processor.new_session", return_value=mock_rembg_session("isnet-general-use")
        ):
            result = remove_file(str(test_file))

            assert isinstance(result, bytes)
            assert result.startswith(b"\x89PNG\r\n\x1a\n")

    def test_remove_file_nonexistent(self, mock_rembg_session):
        """Test remove_file with non-existent file."""
        with pytest.raises(FileNotFoundError):
            remove_file("nonexistent_file.png")

    def test_remove_file_different_models(self, temp_dir, sample_image_bytes, mock_rembg_session):
        """Test remove_file with different model names."""
        test_file = temp_dir / "test_image.png"
        test_file.write_bytes(sample_image_bytes)

        models = ["isnet-general-use", "u2net_human_seg", "u2net"]

        for model in models:
            with patch("sprite_processor.new_session", return_value=mock_rembg_session(model)):
                result = remove_file(str(test_file), model_name=model)
                assert isinstance(result, bytes)
                assert result.startswith(b"\x89PNG\r\n\x1a\n")

    def test_remove_file_invalid_image(self, temp_dir, mock_rembg_session):
        """Test remove_file with invalid image file."""
        test_file = temp_dir / "invalid_image.png"
        test_file.write_bytes(b"not an image")

        with patch(
            "sprite_processor.new_session", return_value=mock_rembg_session("isnet-general-use")
        ):
            with pytest.raises(Exception):
                remove_file(str(test_file))

    def test_remove_bytes_invalid_model(self, sample_image_bytes, mock_rembg_session):
        """Test remove_bytes with invalid model name."""
        with patch("sprite_processor.new_session") as mock_session:
            mock_session.side_effect = Exception("Invalid model name")
            
            with pytest.raises(Exception, match="Invalid model name"):
                remove_bytes(sample_image_bytes, model_name="invalid-model")

    def test_remove_file_invalid_model(self, temp_dir, sample_image_bytes, mock_rembg_session):
        """Test remove_file with invalid model name."""
        test_file = temp_dir / "test_image.png"
        test_file.write_bytes(sample_image_bytes)

        with patch("sprite_processor.new_session") as mock_session:
            mock_session.side_effect = Exception("Invalid model name")
            
            with pytest.raises(Exception, match="Invalid model name"):
                remove_file(str(test_file), model_name="invalid-model")

    def test_remove_bytes_unsupported_format(self, mock_rembg_session):
        """Test remove_bytes with unsupported image format."""
        # Create a fake BMP file (unsupported format)
        bmp_data = b"BM\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        
        with patch("sprite_processor.new_session", return_value=mock_rembg_session("isnet-general-use")):
            with pytest.raises(Exception):
                remove_bytes(bmp_data)

    def test_remove_file_unsupported_format(self, temp_dir, mock_rembg_session):
        """Test remove_file with unsupported image format."""
        # Create a fake BMP file
        test_file = temp_dir / "test.bmp"
        test_file.write_bytes(b"BM\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")

        with patch("sprite_processor.new_session", return_value=mock_rembg_session("isnet-general-use")):
            with pytest.raises(Exception):
                remove_file(str(test_file))


