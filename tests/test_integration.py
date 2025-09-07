"""
Integration tests for sprite-processor.

These tests verify that the different components work together correctly.
"""

from unittest.mock import MagicMock, patch

import pytest

from sprite_processor import remove_bytes, remove_file
from sprite_processor.pipeline import VideoPipelineConfig, process_video_pipeline
from sprite_processor.video import analyze_video, video_to_gif


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""

    def test_image_processing_workflow(self, temp_dir, sample_image_bytes):
        """Test complete image processing workflow."""
        # Create input file
        input_path = temp_dir / "input.png"
        input_path.write_bytes(sample_image_bytes)

        # Process with different models
        models = ["isnet-general-use", "u2net_human_seg", "u2net"]

        with patch("sprite_processor.new_session") as mock_session:
            # Mock the rembg session
            mock_session_instance = MagicMock()
            mock_session_instance.predict.return_value = b"processed_image_data"
            mock_session.return_value = mock_session_instance

            for model in models:
                # Test remove_file
                result_bytes = remove_file(str(input_path), model_name=model)
                assert isinstance(result_bytes, bytes)
                assert result_bytes.startswith(b"\x89PNG\r\n\x1a\n")

                # Test remove_bytes
                result_bytes = remove_bytes(sample_image_bytes, model_name=model)
                assert isinstance(result_bytes, bytes)
                assert result_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    def test_video_processing_workflow(self, temp_dir, sample_video_file):
        """Test complete video processing workflow."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        with patch("sprite_processor.video.VideoFileClip") as mock_clip:
            # Mock video analysis
            mock_video = MagicMock()
            mock_video.duration = 5.0
            mock_video.fps = 24.0
            mock_video.size = (1280, 720)
            mock_clip.return_value = mock_video

            # Test video analysis
            analysis = analyze_video(str(sample_video_file))
            assert analysis["fps"] == 10  # Default recommended FPS
            assert analysis["duration"] == 5.0
            assert analysis["frames"] == 50

            # Test video to GIF conversion
            mock_video.resize.return_value = mock_video
            mock_video.subclip.return_value = mock_video
            mock_video.write_gif.return_value = None

            gif_path = video_to_gif(
                str(sample_video_file),
                str(output_dir / "output.gif"),
                fps=10,
                duration=2.0,
                max_width=480,
                max_height=480,
            )

            assert gif_path == str(output_dir / "output.gif")

    def test_pipeline_workflow(self, temp_dir, sample_video_file):
        """Test complete pipeline workflow."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        with (
            patch("sprite_processor.pipeline.video_to_gif") as mock_video_to_gif,
            patch("sprite_processor.pipeline.video_to_spritesheet") as mock_video_to_spritesheet,
        ):

            # Mock the pipeline functions
            mock_video_to_gif.return_value = str(output_dir / "output.gif")
            mock_video_to_spritesheet.return_value = str(output_dir / "output.png")

            config = VideoPipelineConfig(
                fps=10,
                duration=5.0,
                max_width=480,
                max_height=480,
                grid_cols=5,
                grid_rows=2,
                model="isnet-general-use",
            )

            result = process_video_pipeline(str(sample_video_file), str(output_dir), config)

            assert result["success"] is True
            assert "gif_path" in result
            assert "spritesheet_path" in result

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


class TestModuleIntegration:
    """Test integration between different modules."""

    def test_core_video_integration(self, temp_dir, sample_image_bytes):
        """Test integration between core and video modules."""
        # This test would verify that core functions work with video processing
        # when video frames are extracted and processed individually

        with patch("sprite_processor.new_session") as mock_session:
            mock_session_instance = MagicMock()
            mock_session_instance.predict.return_value = b"processed_frame_data"
            mock_session.return_value = mock_session_instance

            # Process a single frame (simulating video frame processing)
            result = remove_bytes(sample_image_bytes, model_name="isnet-general-use")
            assert isinstance(result, bytes)
            assert result.startswith(b"\x89PNG\r\n\x1a\n")

    def test_api_core_integration(self, temp_dir, sample_image_bytes):
        """Test integration between API and core modules."""
        from fastapi.testclient import TestClient

        from sprite_processor.api import api

        client = TestClient(api)

        with patch("sprite_processor.api.remove_bytes") as mock_remove_bytes:
            mock_remove_bytes.return_value = b"processed_image_data"

            files = {"file": ("test.png", sample_image_bytes, "image/png")}
            data = {"model": "isnet-general-use"}

            response = client.post("/remove", files=files, data=data)

            assert response.status_code == 200
            assert response.headers["content-type"] == "image/png"
            assert response.content == b"processed_image_data"

    def test_cli_core_integration(self, temp_dir, sample_image_bytes):
        """Test integration between CLI and core modules."""
        input_path = temp_dir / "input.png"
        output_path = temp_dir / "output.png"

        input_path.write_bytes(sample_image_bytes)

        with patch("sprite_processor.cli.remove_file") as mock_remove_file:
            mock_remove_file.return_value = b"processed_image_data"

            from sprite_processor.cli import _process_one

            result = _process_one(str(input_path), str(output_path), False, "isnet-general-use")

            assert result == str(output_path)
            mock_remove_file.assert_called_once_with(str(input_path), "isnet-general-use")


class TestPerformanceIntegration:
    """Test performance characteristics of integrated workflows."""

    def test_memory_usage(self, sample_image_bytes):
        """Test that processing doesn't cause memory leaks."""
        # This is a basic test - in a real scenario, you'd use memory profiling tools

        with patch("sprite_processor.new_session") as mock_session:
            mock_session_instance = MagicMock()
            mock_session_instance.predict.return_value = b"processed_image_data"
            mock_session.return_value = mock_session_instance

            # Process multiple images to check for memory issues
            for _ in range(10):
                result = remove_bytes(sample_image_bytes, model_name="isnet-general-use")
                assert isinstance(result, bytes)

    def test_concurrent_processing(self, sample_image_bytes):
        """Test that multiple processing operations can run concurrently."""
        import threading

        results = []
        errors = []

        def process_image():
            try:
                with patch("sprite_processor.new_session") as mock_session:
                    mock_session_instance = MagicMock()
                    mock_session_instance.predict.return_value = b"processed_image_data"
                    mock_session.return_value = mock_session_instance

                    result = remove_bytes(sample_image_bytes, model_name="isnet-general-use")
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=process_image)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert len(results) == 5
        assert len(errors) == 0

        for result in results:
            assert isinstance(result, bytes)
            assert result.startswith(b"\x89PNG\r\n\x1a\n")
