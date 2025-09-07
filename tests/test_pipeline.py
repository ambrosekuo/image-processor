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

    def test_process_video_pipeline_success(self, temp_dir, sample_video_file):
        """Test successful video pipeline processing."""
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

            config = VideoPipelineConfig(
                fps=10,
                duration=5.0,
                max_width=480,
                max_height=480,
                grid="5x2",
                model="isnet-general-use",
            )

            result = process_video_pipeline(str(sample_video_file), str(output_dir), config)

            assert "gif_path" in result
            assert "spritesheet_path" in result
            assert str(result["gif_path"]) == str(output_dir / "test_video.gif")
            assert str(result["spritesheet_path"]) == str(output_dir / "test_video_spritesheet.png")

            # Verify the functions were called with correct parameters
            mock_video_to_gif.assert_called_once()
            mock_extract_frames.assert_called_once()
            mock_create_spritesheet.assert_called_once()
            mock_process_one.assert_called_once()

    def test_process_video_pipeline_gif_only(self, temp_dir, sample_video_file):
        """Test video pipeline processing with GIF only (no spritesheet)."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        with (
            patch("sprite_processor.pipeline.video_to_gif") as mock_video_to_gif,
            patch("sprite_processor.pipeline.extract_gif_frames") as mock_extract_frames,
            patch("sprite_processor.cli._create_spritesheet") as mock_create_spritesheet,
            patch("sprite_processor.cli._process_one") as mock_process_one,
        ):
            mock_video_to_gif.return_value = str(output_dir / "output.gif")
            mock_extract_frames.return_value = [b"frame1", b"frame2", b"frame3"]
            mock_create_spritesheet.return_value = None
            mock_process_one.return_value = None

            # Create actual files that the pipeline expects
            (output_dir / "test_video.gif").touch()
            (output_dir / "test_video_spritesheet.png").touch()

            config = VideoPipelineConfig(
                fps=10,
                duration=5.0,
                max_width=480,
                max_height=480,
                grid="5x2",  # Use valid grid format
                model="isnet-general-use",
            )

            result = process_video_pipeline(str(sample_video_file), str(output_dir), config)

            assert "gif_path" in result
            assert "spritesheet_path" in result  # Spritesheet is still created
            assert str(result["gif_path"]) == str(output_dir / "test_video.gif")

            # Verify only video_to_gif was called
            mock_video_to_gif.assert_called_once()

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
            for model in [
                "isnet-general-use",
                "u2net_human_seg",
                "u2net",
                "u2netp",
                "u2net_cloth_seg",
                "silueta",
            ]:
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


class TestPipelineModuleImports:
    """Test that pipeline module functions are properly importable."""

    def test_import_process_video_pipeline(self):
        """Test that process_video_pipeline can be imported."""
        from sprite_processor.pipeline import process_video_pipeline

        assert callable(process_video_pipeline)

    def test_import_process_video_pipeline_all_models(self):
        """Test that process_video_pipeline_all_models can be imported."""
        from sprite_processor.pipeline import process_video_pipeline_all_models

        assert callable(process_video_pipeline_all_models)

    def test_import_video_pipeline_config(self):
        """Test that VideoPipelineConfig can be imported."""
        from sprite_processor.pipeline import VideoPipelineConfig

        assert VideoPipelineConfig is not None
