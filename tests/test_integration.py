"""
Integration tests for sprite-processor.

These tests verify that the different components work together correctly.
"""

from unittest.mock import patch

import pytest

from sprite_processor import remove_bytes, remove_file
from sprite_processor.pipeline import VideoPipelineConfig, process_video_pipeline
from sprite_processor.video import analyze_video


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""




    def test_error_handling_workflow(self, temp_dir):
        """Test error handling across the workflow."""
        # Test with non-existent file
        with pytest.raises(FileNotFoundError):
            remove_file("nonexistent_file.png")

        # Test with invalid data
        with pytest.raises(Exception):
            remove_bytes(b"invalid image data")

        # Test video analysis with non-existent file
        with pytest.raises(Exception):
            analyze_video("nonexistent_video.mp4")




