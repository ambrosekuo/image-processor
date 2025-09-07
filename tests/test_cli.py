"""
Tests for CLI functionality.
"""

from unittest.mock import patch

import pytest

from sprite_processor.cli import _process_one, app


class TestProcessOne:
    """Test the _process_one function."""

    def test_process_one_success(self, temp_dir, sample_image_bytes, mock_rembg_session):
        """Test successful single file processing."""
        input_path = temp_dir / "input.png"
        output_path = temp_dir / "output.png"

        input_path.write_bytes(sample_image_bytes)

        with patch("sprite_processor.cli.remove_file") as mock_remove_file:
            mock_remove_file.return_value = b"processed_image_data"

            result = _process_one(str(input_path), str(output_path), False, "isnet-general-use")

            assert result == str(output_path)
            mock_remove_file.assert_called_once_with(str(input_path), "isnet-general-use")

            # Check that output file was created
            assert output_path.exists()
            assert output_path.read_bytes() == b"processed_image_data"

    def test_process_one_overwrite_false(self, temp_dir, sample_image_bytes, mock_rembg_session):
        """Test process_one with overwrite=False when output exists."""
        input_path = temp_dir / "input.png"
        output_path = temp_dir / "output.png"

        input_path.write_bytes(sample_image_bytes)
        output_path.write_bytes(b"existing_data")  # Create existing output

        with patch("sprite_processor.cli.remove_file") as mock_remove_file:
            result = _process_one(str(input_path), str(output_path), False, "isnet-general-use")

            # Should return the existing file path without processing
            assert result == str(output_path)
            mock_remove_file.assert_not_called()

            # Original data should still be there
            assert output_path.read_bytes() == b"existing_data"

    def test_process_one_overwrite_true(self, temp_dir, sample_image_bytes, mock_rembg_session):
        """Test process_one with overwrite=True when output exists."""
        input_path = temp_dir / "input.png"
        output_path = temp_dir / "output.png"

        input_path.write_bytes(sample_image_bytes)
        output_path.write_bytes(b"existing_data")  # Create existing output

        with patch("sprite_processor.cli.remove_file") as mock_remove_file:
            mock_remove_file.return_value = b"new_processed_data"

            result = _process_one(str(input_path), str(output_path), True, "isnet-general-use")

            assert result == str(output_path)
            mock_remove_file.assert_called_once_with(str(input_path), "isnet-general-use")

            # Should have new data
            assert output_path.read_bytes() == b"new_processed_data"

    def test_process_one_processing_error(self, temp_dir, sample_image_bytes):
        """Test process_one with processing error."""
        input_path = temp_dir / "input.png"
        output_path = temp_dir / "output.png"

        input_path.write_bytes(sample_image_bytes)

        with patch("sprite_processor.cli.remove_file") as mock_remove_file:
            mock_remove_file.side_effect = Exception("Processing failed")

            with pytest.raises(Exception, match="Processing failed"):
                _process_one(str(input_path), str(output_path), False, "isnet-general-use")

    def test_process_one_nonexistent_input(self, temp_dir):
        """Test process_one with non-existent input file."""
        input_path = temp_dir / "nonexistent.png"
        output_path = temp_dir / "output.png"

        with pytest.raises(FileNotFoundError):
            _process_one(str(input_path), str(output_path), False, "isnet-general-use")

    def test_process_one_different_models(self, temp_dir, sample_image_bytes, mock_rembg_session):
        """Test process_one with different model names."""
        input_path = temp_dir / "input.png"
        output_path = temp_dir / "output.png"

        input_path.write_bytes(sample_image_bytes)

        models = ["isnet-general-use", "u2net_human_seg", "u2net"]

        with patch("sprite_processor.cli.remove_file") as mock_remove_file:
            mock_remove_file.return_value = b"processed_image_data"

            for model in models:
                result = _process_one(str(input_path), str(output_path), True, model)
                assert result == str(output_path)
                mock_remove_file.assert_called_with(str(input_path), model)


class TestCLIApp:
    """Test the CLI app function."""

    def test_app_help(self):
        """Test that app function shows help when called with --help."""
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_app_version(self):
        """Test that app function shows version when called with --version."""
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0

    def test_app_invalid_args(self):
        """Test app function with invalid arguments."""
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["--invalid-arg"])
        assert result.exit_code != 0

    def test_app_process_file(self, temp_dir, sample_image_bytes):
        """Test app function processing a single file."""
        input_path = temp_dir / "input.png"
        output_path = temp_dir / "output.png"

        input_path.write_bytes(sample_image_bytes)

        with patch("sprite_processor.cli._process_one") as mock_process_one:
            mock_process_one.return_value = str(output_path)

            from click.testing import CliRunner

            runner = CliRunner()
            result = runner.invoke(
                app, [str(input_path), str(output_path), "--model", "isnet-general-use"]
            )

            assert result.exit_code == 0
            mock_process_one.assert_called_once_with(
                str(input_path), str(output_path), False, "isnet-general-use"
            )

    def test_app_process_directory(self, temp_dir, sample_image_bytes):
        """Test app function processing a directory."""
        input_dir = temp_dir / "input"
        output_dir = temp_dir / "output"

        input_dir.mkdir()
        output_dir.mkdir()

        # Create test images
        for i in range(3):
            img_path = input_dir / f"image{i}.png"
            img_path.write_bytes(sample_image_bytes)

        with patch("sprite_processor.cli._process_one") as mock_process_one:
            mock_process_one.return_value = "processed_path"

            from click.testing import CliRunner

            runner = CliRunner()
            result = runner.invoke(
                app, [str(input_dir), str(output_dir), "--model", "u2net_human_seg"]
            )

            assert result.exit_code == 0
            # Should process each image in the directory
            assert mock_process_one.call_count == 3

    def test_app_with_overwrite(self, temp_dir, sample_image_bytes):
        """Test app function with overwrite flag."""
        input_path = temp_dir / "input.png"
        output_path = temp_dir / "output.png"

        input_path.write_bytes(sample_image_bytes)

        with patch("sprite_processor.cli._process_one") as mock_process_one:
            mock_process_one.return_value = str(output_path)

            from click.testing import CliRunner

            runner = CliRunner()
            result = runner.invoke(
                app, [str(input_path), str(output_path), "--overwrite", "--model", "u2net"]
            )

            assert result.exit_code == 0
            mock_process_one.assert_called_once_with(
                str(input_path), str(output_path), True, "u2net"  # overwrite=True
            )


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_app_nonexistent_input_file(self, temp_dir):
        """Test app function with non-existent input file."""
        input_path = temp_dir / "nonexistent.png"
        output_path = temp_dir / "output.png"

        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, [str(input_path), str(output_path)])
        assert result.exit_code != 0

    def test_app_processing_error(self, temp_dir, sample_image_bytes):
        """Test app function with processing error."""
        input_path = temp_dir / "input.png"
        output_path = temp_dir / "output.png"

        input_path.write_bytes(sample_image_bytes)

        with patch("sprite_processor.cli._process_one") as mock_process_one:
            mock_process_one.side_effect = Exception("Processing failed")

            from click.testing import CliRunner

            runner = CliRunner()
            result = runner.invoke(app, [str(input_path), str(output_path)])
            assert result.exit_code != 0


class TestCLIModuleImports:
    """Test that CLI module functions are properly importable."""

    def test_import_process_one(self):
        """Test that _process_one can be imported."""
        from sprite_processor.cli import _process_one

        assert callable(_process_one)

    def test_import_app(self):
        """Test that app can be imported."""
        from sprite_processor.cli import app

        assert callable(app)
