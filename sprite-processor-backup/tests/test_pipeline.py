"""
Tests for pipeline processing functions.
"""

from unittest.mock import patch

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
            patch("sprite_processor.pipeline.video_to_spritesheet") as mock_video_to_spritesheet,
        ):

            # Mock the video processing functions
            mock_video_to_gif.return_value = str(output_dir / "output.gif")
            mock_video_to_spritesheet.return_value = str(output_dir / "output.png")

            config = VideoPipelineConfig(
                fps=10,
                duration=5.0,
                max_width=480,
                max_height=480,
                grid="5x2",
                model="isnet-general-use",
            )

            result = process_video_pipeline(str(sample_video_file), str(output_dir), config)

            assert result["success"] is True
            assert "gif_path" in result
            assert "spritesheet_path" in result
            assert result["gif_path"] == str(output_dir / "output.gif")
            assert result["spritesheet_path"] == str(output_dir / "output.png")

            # Verify the functions were called with correct parameters
            mock_video_to_gif.assert_called_once()
            mock_video_to_spritesheet.assert_called_once()

    def test_process_video_pipeline_gif_only(self, temp_dir, sample_video_file):
        """Test video pipeline processing with GIF only (no spritesheet)."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        with patch("sprite_processor.pipeline.video_to_gif") as mock_video_to_gif:
            mock_video_to_gif.return_value = str(output_dir / "output.gif")

            config = VideoPipelineConfig(
                fps=10,
                duration=5.0,
                max_width=480,
                max_height=480,
                grid=None,  # No spritesheet
                model="isnet-general-use",
            )

            result = process_video_pipeline(str(sample_video_file), str(output_dir), config)

            assert result["success"] is True
            assert "gif_path" in result
            assert "spritesheet_path" not in result
            assert result["gif_path"] == str(output_dir / "output.gif")

    def test_process_video_pipeline_video_error(self, temp_dir, sample_video_file):
        """Test video pipeline processing with video processing error."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        with patch("sprite_processor.pipeline.video_to_gif") as mock_video_to_gif:
            mock_video_to_gif.side_effect = Exception("Video processing failed")

            config = VideoPipelineConfig()

            result = process_video_pipeline(str(sample_video_file), str(output_dir), config)

            assert result["success"] is False
            assert "error" in result
            assert "Video processing failed" in result["error"]

    def test_process_video_pipeline_spritesheet_error(self, temp_dir, sample_video_file):
        """Test video pipeline processing with spritesheet processing error."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        with (
            patch("sprite_processor.pipeline.video_to_gif") as mock_video_to_gif,
            patch("sprite_processor.pipeline.video_to_spritesheet") as mock_video_to_spritesheet,
        ):

            mock_video_to_gif.return_value = str(output_dir / "output.gif")
            mock_video_to_spritesheet.side_effect = Exception("Spritesheet processing failed")

            config = VideoPipelineConfig(grid_cols=5, grid_rows=2)

            result = process_video_pipeline(str(sample_video_file), str(output_dir), config)

            assert result["success"] is False
            assert "error" in result
            assert "Spritesheet processing failed" in result["error"]


class TestProcessVideoPipelineAllModels:
    """Test the process_video_pipeline_all_models function."""

    def test_process_video_pipeline_all_models_success(self, temp_dir, sample_video_file):
        """Test successful video pipeline processing with all models."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        with patch("sprite_processor.pipeline.process_video_pipeline") as mock_pipeline:
            # Mock successful processing for each model
            mock_pipeline.return_value = {
                "success": True,
                "gif_path": str(output_dir / "output.gif"),
                "spritesheet_path": str(output_dir / "output.png"),
            }

            config = VideoPipelineConfig(
                fps=10, duration=5.0, max_width=480, max_height=480, grid="5x2"
            )

            result = process_video_pipeline_all_models(
                str(sample_video_file), str(output_dir), config
            )

            assert result["success"] is True
            assert "results" in result
            assert len(result["results"]) > 0  # Should have results for multiple models

            # Check that each model was processed
            for model_name, model_result in result["results"].items():
                assert model_result["success"] is True
                assert "gif_path" in model_result
                assert "spritesheet_path" in model_result

    def test_process_video_pipeline_all_models_partial_failure(self, temp_dir, sample_video_file):
        """Test video pipeline processing with some models failing."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        def mock_pipeline_side_effect(video_path, output_dir, config):
            if config.model == "isnet-general-use":
                return {
                    "success": True,
                    "gif_path": str(output_dir / "output.gif"),
                    "spritesheet_path": str(output_dir / "output.png"),
                }
            else:
                return {"success": False, "error": f"Processing failed for {config.model}"}

        with patch("sprite_processor.pipeline.process_video_pipeline") as mock_pipeline:
            mock_pipeline.side_effect = mock_pipeline_side_effect

            config = VideoPipelineConfig()

            result = process_video_pipeline_all_models(
                str(sample_video_file), str(output_dir), config
            )

            assert result["success"] is True  # Overall success if at least one model works
            assert "results" in result

            # Check that we have both successful and failed results
            success_count = sum(1 for r in result["results"].values() if r["success"])
            failure_count = sum(1 for r in result["results"].values() if not r["success"])

            assert success_count > 0
            assert failure_count > 0

    def test_process_video_pipeline_all_models_all_fail(self, temp_dir, sample_video_file):
        """Test video pipeline processing when all models fail."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        with patch("sprite_processor.pipeline.process_video_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {"success": False, "error": "All models failed"}

            config = VideoPipelineConfig()

            result = process_video_pipeline_all_models(
                str(sample_video_file), str(output_dir), config
            )

            assert result["success"] is False
            assert "error" in result
            assert "All models failed" in result["error"]


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
