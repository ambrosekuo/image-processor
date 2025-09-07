"""
Tests for API endpoints.
"""

import io
from unittest.mock import MagicMock, patch


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_endpoint(self, api_client):
        """Test that health endpoint returns OK."""
        response = api_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"ok": True}


class TestRemoveEndpoint:
    """Test the background removal endpoint."""

    def test_remove_endpoint_success(self, api_client, sample_image_bytes):
        """Test successful background removal."""
        with patch("sprite_processor.api.remove_bytes") as mock_remove:
            mock_remove.return_value = b"fake_processed_image_data"

            files = {"file": ("test.png", sample_image_bytes, "image/png")}
            data = {"model": "isnet-general-use"}

            response = api_client.post("/remove", files=files, data=data)

            assert response.status_code == 200
            assert response.headers["content-type"] == "image/png"
            assert response.content == b"fake_processed_image_data"

    def test_remove_endpoint_no_file(self, api_client):
        """Test remove endpoint without file."""
        response = api_client.post("/remove")
        assert response.status_code == 422  # Validation error

    def test_remove_endpoint_different_models(self, api_client, sample_image_bytes):
        """Test remove endpoint with different models."""
        models = ["isnet-general-use", "u2net_human_seg", "u2net"]

        with patch("sprite_processor.api.remove_bytes") as mock_remove:
            mock_remove.return_value = b"fake_processed_image_data"

            for model in models:
                files = {"file": ("test.png", sample_image_bytes, "image/png")}
                data = {"model": model}

                response = api_client.post("/remove", files=files, data=data)
                assert response.status_code == 200
                mock_remove.assert_called_with(sample_image_bytes, model_name=model)


class TestSpritesheetEndpoint:
    """Test the spritesheet processing endpoint."""

    def test_spritesheet_endpoint_success(self, api_client, sample_spritesheet):
        """Test successful spritesheet processing."""
        # Convert spritesheet to bytes
        img_bytes = io.BytesIO()
        sample_spritesheet.save(img_bytes, format="PNG")
        spritesheet_bytes = img_bytes.getvalue()

        with patch("sprite_processor.api._maybe_process_frame") as mock_process:
            # Mock the processing to return the original image
            mock_process.return_value = sample_spritesheet

            files = {"file": ("spritesheet.png", spritesheet_bytes, "image/png")}
            data = {"grid": "2x2", "frames": "4", "model": "isnet-general-use"}

            response = api_client.post("/process/spritesheet", files=files, data=data)

            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert "spritesheet" in result
            assert "config" in result

    def test_spritesheet_endpoint_gif_input(self, api_client, sample_gif):
        """Test spritesheet processing with GIF input."""
        # Mock the entire spritesheet processing pipeline
        with (
            patch("sprite_processor.video.extract_gif_frames") as mock_extract_frames,
            patch("sprite_processor.cli._create_spritesheet") as mock_create_spritesheet,
            patch("sprite_processor.cli._process_one") as mock_process_one,
        ):
            # Mock the GIF frame extraction
            mock_frames = [MagicMock() for _ in range(4)]
            for frame in mock_frames:
                frame.size = (32, 32)
            mock_extract_frames.return_value = mock_frames

            # Mock the spritesheet creation
            mock_create_spritesheet.return_value = None

            # Mock the background removal
            mock_process_one.return_value = None

            files = {"file": ("animation.gif", sample_gif, "image/gif")}
            data = {"grid": "auto", "frames": "4", "model": "isnet-general-use"}

            response = api_client.post("/process/spritesheet", files=files, data=data)

            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True

    def test_spritesheet_endpoint_invalid_grid(self, api_client, sample_image_bytes):
        """Test spritesheet processing with invalid grid format."""
        files = {"file": ("test.png", sample_image_bytes, "image/png")}
        data = {"grid": "invalid", "frames": "4"}

        response = api_client.post("/process/spritesheet", files=files, data=data)
        assert response.status_code == 400
        assert "Grid must be 'colsxrows'" in response.json()["detail"]

    def test_spritesheet_endpoint_no_file(self, api_client):
        """Test spritesheet endpoint without file."""
        response = api_client.post("/process/spritesheet")
        assert response.status_code == 422


class TestVideoToGifEndpoint:
    """Test the video to GIF endpoint."""

    def test_video_to_gif_endpoint_success(self, api_client, sample_video_file):
        """Test successful video to GIF conversion."""
        with patch("sprite_processor.api.video_to_gif") as mock_video_to_gif:
            mock_video_to_gif.return_value = sample_video_file

            files = {"file": ("test.mp4", b"fake video data", "video/mp4")}
            data = {"fps": "10", "duration": "5.0", "max_width": "480", "max_height": "480"}

            response = api_client.post("/process/video-to-gif", files=files, data=data)

            assert response.status_code == 200
            assert response.headers["content-type"] == "image/gif"

    def test_video_to_gif_endpoint_gif_input(self, api_client, sample_gif):
        """Test video to GIF endpoint with GIF input (should return as-is)."""
        files = {"file": ("test.gif", sample_gif, "image/gif")}
        data = {"fps": "10"}

        response = api_client.post("/process/video-to-gif", files=files, data=data)

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/gif"
        assert response.content == sample_gif

    def test_video_to_gif_endpoint_no_file(self, api_client):
        """Test video to GIF endpoint without file."""
        response = api_client.post("/process/video-to-gif")
        assert response.status_code == 422


class TestAnalyzeVideoEndpoint:
    """Test the video analysis endpoint."""

    def test_analyze_video_endpoint_success(self, api_client, sample_video_file):
        """Test successful video analysis."""
        with patch("sprite_processor.api.analyze_video") as mock_analyze:
            mock_analyze.return_value = {
                "fps": 10,
                "duration": 5.0,
                "frames": 50,
                "width": 1280,
                "height": 720,
            }

            files = {"file": ("test.mp4", b"fake video data", "video/mp4")}

            response = api_client.post("/analyze/video", files=files)

            assert response.status_code == 200
            result = response.json()
            assert result["analysis"]["fps"] == 10
            assert result["analysis"]["duration"] == 5.0
            assert result["analysis"]["frames"] == 50

    def test_analyze_video_endpoint_no_file(self, api_client):
        """Test analyze video endpoint without file."""
        response = api_client.post("/analyze/video")
        assert response.status_code == 422


class TestPipelineEndpoints:
    """Test the pipeline processing endpoints."""

    def test_process_video_pipeline_endpoint(self, api_client, sample_video_file):
        """Test video pipeline processing endpoint."""
        with patch("sprite_processor.api.process_video_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {
                "success": True,
                "gif_path": sample_video_file,
                "spritesheet_path": sample_video_file,
                "processed_path": sample_video_file,
            }

            files = {"file": ("test.mp4", b"fake video data", "video/mp4")}
            data = {
                "fps": "10",
                "duration": "5.0",
                "grid": "5x2",
                "model": "isnet-general-use",
            }

            response = api_client.post("/process/video-pipeline", files=files, data=data)

            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True

    def test_process_video_pipeline_all_models_endpoint(self, api_client, sample_video_file):
        """Test video pipeline processing with all models endpoint."""
        with patch("sprite_processor.api.process_video_pipeline_all_models") as mock_pipeline:
            mock_pipeline.return_value = {
                "gif_path": sample_video_file,
                "spritesheet_path": sample_video_file,
                "model_results": {
                    "isnet-general-use": {
                        "success": True,
                        "path": sample_video_file,
                    },
                    "u2net_human_seg": {
                        "success": True,
                        "path": sample_video_file,
                    },
                },
            }

            files = {"file": ("test.mp4", b"fake video data", "video/mp4")}
            data = {
                "fps": "10",
                "duration": "5.0",
                "grid": "5x2",
            }

            response = api_client.post(
                "/process/video-pipeline", files=files, data={**data, "all_models": "true"}
            )

            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert "model_results" in result


class TestRemoveAllModelsEndpoint:
    """Test the remove all models endpoint."""

    def test_remove_all_models_endpoint_success(self, api_client, sample_image_bytes):
        """Test successful processing with all models."""
        with patch("sprite_processor.api.remove_bytes") as mock_remove:
            mock_remove.return_value = b"fake_processed_image_data"

            files = {"file": ("test.png", sample_image_bytes, "image/png")}

            response = api_client.post("/remove-all-models", files=files)

            assert response.status_code == 200
            result = response.json()
            assert "models" in result
            assert len(result["models"]) > 0  # Should have results for multiple models

    def test_remove_all_models_endpoint_no_file(self, api_client):
        """Test remove all models endpoint without file."""
        response = api_client.post("/remove-all-models")
        assert response.status_code == 422


class TestAPIErrorHandling:
    """Test API error handling."""

    def test_remove_endpoint_processing_error(self, api_client, sample_image_bytes):
        """Test remove endpoint with processing error."""
        with patch("sprite_processor.api.remove_bytes") as mock_remove:
            mock_remove.side_effect = Exception("Processing failed")

            files = {"file": ("test.png", sample_image_bytes, "image/png")}

            response = api_client.post("/remove", files=files)

            assert response.status_code == 500
            assert "Processing failed" in response.json()["detail"]

    def test_spritesheet_endpoint_processing_error(self, api_client, sample_image_bytes):
        """Test spritesheet endpoint with processing error."""
        with patch("sprite_processor.api._maybe_process_frame") as mock_process:
            mock_process.side_effect = Exception("Processing failed")

            files = {"file": ("test.png", sample_image_bytes, "image/png")}
            data = {"grid": "2x2", "frames": "4"}

            response = api_client.post("/process/spritesheet", files=files, data=data)

            assert response.status_code == 500
            assert "Processing failed" in response.json()["detail"]


class TestAnalyzeSpritesheetEndpoint:
    """Test the analyze spritesheet endpoint."""

    def test_analyze_spritesheet_endpoint_success(self, api_client, sample_image_bytes):
        """Test successful spritesheet analysis."""
        with patch("sprite_processor.api.Image") as mock_image:
            # Mock PIL Image
            mock_img = MagicMock()
            mock_img.size = (100, 50)  # 100x50 spritesheet
            mock_image.open.return_value = mock_img

            files = {"file": ("spritesheet.png", sample_image_bytes, "image/png")}

            response = api_client.post("/analyze-spritesheet", files=files)

            assert response.status_code == 200
            result = response.json()
            assert "spritesheet_size" in result
            assert "suggested_layouts" in result
            assert "width_divisors" in result
            assert "height_divisors" in result

    def test_analyze_spritesheet_endpoint_no_file(self, api_client):
        """Test analyze spritesheet endpoint without file."""
        response = api_client.post("/analyze-spritesheet")
        assert response.status_code == 422

    def test_analyze_spritesheet_endpoint_invalid_file(self, api_client):
        """Test analyze spritesheet endpoint with invalid file."""
        files = {"file": ("test.txt", b"not an image", "text/plain")}

        response = api_client.post("/analyze-spritesheet", files=files)
        assert response.status_code == 500  # API returns 500 for invalid images


class TestGifToSpritesheetEndpoint:
    """Test the GIF to spritesheet endpoint."""

    def test_gif_to_spritesheet_endpoint_success(self, api_client, sample_gif):
        """Test successful GIF to spritesheet conversion."""
        with (
            patch("sprite_processor.video.extract_gif_frames") as mock_extract_frames,
            patch("sprite_processor.cli._create_spritesheet") as mock_create_spritesheet,
            patch("sprite_processor.cli._process_one") as mock_process_one,
        ):
            # Mock the GIF frame extraction
            mock_frames = [MagicMock() for _ in range(4)]
            for frame in mock_frames:
                frame.size = (32, 32)
            mock_extract_frames.return_value = mock_frames

            # Mock the spritesheet creation
            mock_create_spritesheet.return_value = None

            # Mock the background removal
            mock_process_one.return_value = None

            files = {"file": ("animation.gif", sample_gif, "image/gif")}
            data = {"grid": "2x2", "frames": "4"}

            response = api_client.post("/process/gif-to-spritesheet", files=files, data=data)

            assert response.status_code == 200
            result = response.json()
            assert "success" in result

    def test_gif_to_spritesheet_endpoint_invalid_grid(self, api_client, sample_gif):
        """Test GIF to spritesheet endpoint with invalid grid format."""
        files = {"file": ("animation.gif", sample_gif, "image/gif")}
        data = {"grid": "invalid"}

        response = api_client.post("/process/gif-to-spritesheet", files=files, data=data)
        assert response.status_code == 400
        assert "Grid must be in format" in response.json()["detail"]

    def test_gif_to_spritesheet_endpoint_no_file(self, api_client):
        """Test GIF to spritesheet endpoint without file."""
        response = api_client.post("/process/gif-to-spritesheet")
        assert response.status_code == 422
