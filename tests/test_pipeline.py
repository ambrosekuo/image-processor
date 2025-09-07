"""
Tests for pipeline processing functions.
"""

from unittest.mock import patch

import pytest

from sprite_processor.pipeline import (
    VideoPipelineConfig,
    process_video_pipeline,
    process_video_pipeline_all_models,
)


class TestVideoPipelineConfig:
    """Test the VideoPipelineConfig class."""

    def test_config_creation(self):
        """Test creating a VideoPipelineConfig."""
        config = VideoPipelineConfig(
            fps=10,
            duration=5.0,
            max_width=480,
            max_height=480,
            grid="5x2",
            model="isnet-general-use",
        )

        assert config.fps == 10
        assert config.duration == 5.0
        assert config.max_width == 480
        assert config.max_height == 480
        assert config.grid == "5x2"
        assert config.model == "isnet-general-use"

    def test_config_defaults(self):
        """Test VideoPipelineConfig with default values."""
        config = VideoPipelineConfig()

        assert config.fps == 10
        assert config.duration is None
        assert config.max_width == 480
        assert config.max_height == 480
        assert config.grid == "5x2"
        assert config.frames is None
        assert config.model == "isnet-general-use"


class TestProcessVideoPipeline:
    """Test the process_video_pipeline function."""



    def test_process_video_pipeline_video_error(self, temp_dir, sample_video_file):
        """Test video pipeline processing with video processing error."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        with patch("sprite_processor.pipeline.video_to_gif") as mock_video_to_gif:
            mock_video_to_gif.side_effect = Exception("Video processing failed")

            config = VideoPipelineConfig()

            # The pipeline raises exceptions on error, doesn't return success=False
            with pytest.raises(Exception, match="Video processing failed"):
                process_video_pipeline(str(sample_video_file), str(output_dir), config)

    def test_process_video_pipeline_spritesheet_error(self, temp_dir, sample_video_file):
        """Test video pipeline processing with spritesheet processing error."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        with (
            patch("sprite_processor.pipeline.video_to_gif") as mock_video_to_gif,
            patch("sprite_processor.pipeline.extract_gif_frames") as mock_extract_frames,
            patch("sprite_processor.cli._create_spritesheet") as mock_create_spritesheet,
        ):

            mock_video_to_gif.return_value = str(output_dir / "output.gif")
            mock_extract_frames.return_value = [b"frame1", b"frame2", b"frame3"]
            mock_create_spritesheet.side_effect = Exception("Spritesheet processing failed")

            config = VideoPipelineConfig(grid="5x2")

            # The pipeline raises exceptions on error, doesn't return success=False
            with pytest.raises(Exception, match="Spritesheet processing failed"):
                process_video_pipeline(str(sample_video_file), str(output_dir), config)


class TestProcessVideoPipelineAllModels:
    """Test the process_video_pipeline_all_models function."""

    def test_process_video_pipeline_all_models_success(self, temp_dir, sample_video_file):
        """Test successful video pipeline processing with all models."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        with (
            patch("sprite_processor.pipeline.video_to_gif") as mock_video_to_gif,
            patch("sprite_processor.pipeline.extract_gif_frames") as mock_extract_frames,
            patch("sprite_processor.cli._create_spritesheet") as mock_create_spritesheet,
            patch("sprite_processor.cli._process_one") as mock_process_one,
        ):
            # Mock the video processing functions
            mock_video_to_gif.return_value = str(output_dir / "output.gif")
            mock_extract_frames.return_value = [b"frame1", b"frame2", b"frame3"]
            mock_create_spritesheet.return_value = None
            mock_process_one.return_value = None

            # Create actual files that the pipeline expects
            (output_dir / "test_video.gif").touch()
            (output_dir / "test_video_spritesheet.png").touch()
            # Create files for each model
            for model in ["isnet-general-use", "u2net_human_seg", "u2net", "u2netp", "u2net_cloth_seg", "silueta"]:
                (output_dir / f"test_video_{model}_processed.png").touch()

            config = VideoPipelineConfig(
                fps=10, duration=5.0, max_width=480, max_height=480, grid="5x2"
            )

            result = process_video_pipeline_all_models(
                str(sample_video_file), str(output_dir), config
            )

            assert "model_results" in result
            assert len(result["model_results"]) > 0  # Should have results for multiple models

            # Check that each model was processed
            for model_name, model_result in result["model_results"].items():
                assert model_result["success"] is True
                assert "path" in model_result

    def test_process_video_pipeline_all_models_partial_failure(self, temp_dir, sample_video_file):
        """Test video pipeline processing with some models failing."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        def mock_process_one_side_effect(input_path, output_path, model_name):
            if model_name == "isnet-general-use":
                # Success for this model
                return None
            else:
                # Failure for other models
                raise Exception(f"Processing failed for {model_name}")

        with (
            patch("sprite_processor.pipeline.video_to_gif") as mock_video_to_gif,
            patch("sprite_processor.pipeline.extract_gif_frames") as mock_extract_frames,
            patch("sprite_processor.cli._create_spritesheet") as mock_create_spritesheet,
            patch("sprite_processor.cli._process_one") as mock_process_one,
        ):
            # Mock the video processing functions
            mock_video_to_gif.return_value = str(output_dir / "output.gif")
            mock_extract_frames.return_value = [b"frame1", b"frame2", b"frame3"]
            mock_create_spritesheet.return_value = None
            mock_process_one.side_effect = mock_process_one_side_effect

            # Create actual files that the pipeline expects
            (output_dir / "test_video.gif").touch()
            (output_dir / "test_video_spritesheet.png").touch()
            # Create files for the successful model only
            (output_dir / "test_video_isnet-general-use_processed.png").touch()

            config = VideoPipelineConfig(grid="5x2")

            result = process_video_pipeline_all_models(
                str(sample_video_file), str(output_dir), config
            )

            assert "model_results" in result

            # Check that we have both successful and failed results
            success_count = sum(1 for r in result["model_results"].values() if r["success"])
            failure_count = sum(1 for r in result["model_results"].values() if not r["success"])

            assert success_count > 0
            assert failure_count > 0

    def test_process_video_pipeline_all_models_all_fail(self, temp_dir, sample_video_file):
        """Test video pipeline processing when all models fail."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        with (
            patch("sprite_processor.pipeline.video_to_gif") as mock_video_to_gif,
            patch("sprite_processor.pipeline.extract_gif_frames") as mock_extract_frames,
            patch("sprite_processor.cli._create_spritesheet") as mock_create_spritesheet,
            patch("sprite_processor.cli._process_one") as mock_process_one,
        ):
            # Mock the video processing functions
            mock_video_to_gif.return_value = str(output_dir / "output.gif")
            mock_extract_frames.return_value = [b"frame1", b"frame2", b"frame3"]
            mock_create_spritesheet.return_value = None
            mock_process_one.side_effect = Exception("All models failed")

            config = VideoPipelineConfig(grid="5x2")

            result = process_video_pipeline_all_models(
                str(sample_video_file), str(output_dir), config
            )

            assert "model_results" in result
            # All models should have failed
            for model_name, model_result in result["model_results"].items():
                assert model_result["success"] is False
                assert "error" in model_result


class TestVideoPipelineConfigValidation:
    """Test VideoPipelineConfig validation and edge cases."""

    def test_config_invalid_grid_format(self):
        """Test VideoPipelineConfig with invalid grid format."""
        # The config doesn't validate grid format on creation, only during processing
        config = VideoPipelineConfig(grid="invalid")
        assert config.grid == "invalid"

    def test_config_negative_values(self):
        """Test VideoPipelineConfig with negative values."""
        # The config doesn't validate negative values on creation
        config = VideoPipelineConfig(fps=-1)
        assert config.fps == -1

        config = VideoPipelineConfig(duration=-1.0)
        assert config.duration == -1.0

        config = VideoPipelineConfig(max_width=-100)
        assert config.max_width == -100

        config = VideoPipelineConfig(max_height=-100)
        assert config.max_height == -100

    def test_config_edge_cases(self):
        """Test VideoPipelineConfig with edge case values."""
        # Very high FPS
        config = VideoPipelineConfig(fps=120)
        assert config.fps == 120

        # Very short duration
        config = VideoPipelineConfig(duration=0.1)
        assert config.duration == 0.1

        # Large dimensions
        config = VideoPipelineConfig(max_width=4096, max_height=4096)
        assert config.max_width == 4096
        assert config.max_height == 4096




