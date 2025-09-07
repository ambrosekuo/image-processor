"""
Tests for video processing functions.
"""

from unittest.mock import MagicMock, patch

import pytest

from sprite_processor.video import analyze_video, video_to_gif, video_to_spritesheet


class TestVideoToGif:
    """Test the video_to_gif function."""

    def test_video_to_gif_basic(self, temp_dir, sample_video_file):
        """Test basic video to GIF conversion."""
        output_path = temp_dir / "output.gif"

        with patch("sprite_processor.video.VideoFileClip") as mock_clip:
            # Mock the video clip
            mock_video = MagicMock()
            mock_video.duration = 5.0
            mock_video.fps = 24.0
            mock_video.size = (1280, 720)
            mock_video.w = 1280
            mock_video.h = 720
            mock_video.resize.return_value = mock_video
            mock_video.subclip.return_value = mock_video
            mock_video.write_gif.return_value = None

            # Mock set_end to return the same video object
            mock_video.set_end.return_value = mock_video

            mock_clip.return_value.__enter__.return_value = mock_video

            # Create a dummy output file so stat() works
            output_path.write_bytes(b"dummy gif content")

            result = video_to_gif(
                str(sample_video_file),
                str(output_path),
                fps=10,
                duration=2.0,
                max_width=480,
                max_height=480,
            )

            assert result == output_path
            mock_video.write_gif.assert_called_once()

    def test_video_to_gif_with_resize(self, temp_dir, sample_video_file):
        """Test video to GIF conversion with resizing."""
        output_path = temp_dir / "output.gif"

        with patch("sprite_processor.video.VideoFileClip") as mock_clip:
            mock_video = MagicMock()
            mock_video.duration = 5.0
            mock_video.fps = 24.0
            mock_video.size = (1920, 1080)  # Large video
            mock_video.w = 1920
            mock_video.h = 1080
            mock_video.resize.return_value = mock_video
            mock_video.subclip.return_value = mock_video
            mock_video.write_gif.return_value = None
            mock_video.set_end.return_value = mock_video

            mock_clip.return_value.__enter__.return_value = mock_video

            # Create a dummy output file so stat() works
            output_path.write_bytes(b"dummy gif content")

            video_to_gif(
                str(sample_video_file), str(output_path), fps=15, max_width=640, max_height=480
            )

            # Should call resize with the correct dimensions
            mock_video.resize.assert_called_once()

    def test_video_to_gif_no_duration_limit(self, temp_dir, sample_video_file):
        """Test video to GIF conversion without duration limit."""
        output_path = temp_dir / "output.gif"

        with patch("sprite_processor.video.VideoFileClip") as mock_clip:
            mock_video = MagicMock()
            mock_video.duration = 3.0
            mock_video.fps = 24.0
            mock_video.size = (1280, 720)
            mock_video.w = 1280
            mock_video.h = 720
            mock_video.resize.return_value = mock_video
            mock_video.subclip.return_value = mock_video
            mock_video.write_gif.return_value = None
            mock_video.set_end.return_value = mock_video

            mock_clip.return_value.__enter__.return_value = mock_video

            # Create a dummy output file so stat() works
            output_path.write_bytes(b"dummy gif content")

            video_to_gif(
                str(sample_video_file), str(output_path), fps=12, duration=None  # No duration limit
            )

            # Should not call subclip when duration is None
            mock_video.subclip.assert_not_called()

    def test_video_to_gif_nonexistent_file(self, temp_dir):
        """Test video_to_gif with non-existent file."""
        output_path = temp_dir / "output.gif"

        with pytest.raises(Exception):  # VideoFileClip will raise an exception
            video_to_gif("nonexistent.mp4", str(output_path))


class TestVideoToSpritesheet:
    """Test the video_to_spritesheet function."""

    def test_video_to_spritesheet_basic(self, temp_dir, sample_video_file):
        """Test basic video to spritesheet conversion."""
        output_path = temp_dir / "output.png"

        with (
            patch("sprite_processor.video.VideoFileClip") as mock_clip,
            patch("sprite_processor.video.extract_gif_frames") as mock_extract,
            patch("sprite_processor.cli._create_spritesheet") as mock_create_spritesheet,
        ):
            # Mock the video clip
            mock_video = MagicMock()
            mock_video.duration = 5.0
            mock_video.fps = 24.0
            mock_video.size = (1280, 720)
            mock_video.w = 1280
            mock_video.h = 720
            mock_video.resize.return_value = mock_video
            mock_video.subclip.return_value = mock_video
            mock_video.write_gif.return_value = None
            mock_video.set_end.return_value = mock_video

            # Mock frame iteration
            mock_frames = []
            for i in range(10):  # 10 frames
                mock_frame = MagicMock()
                mock_frame.size = (640, 360)
                mock_frames.append(mock_frame)

            mock_video.iter_frames.return_value = mock_frames

            mock_clip.return_value.__enter__.return_value = mock_video

            # Mock the extracted frames
            mock_frames = []
            for i in range(10):
                mock_frame = MagicMock()
                mock_frame.size = (640, 360)
                mock_frames.append(mock_frame)
            mock_extract.return_value = mock_frames

            # Mock the spritesheet creation
            mock_create_spritesheet.return_value = output_path

            with patch("sprite_processor.video.Image") as mock_image:
                mock_img = MagicMock()
                mock_img.size = (640, 360)
                mock_image.new.return_value = mock_img
                mock_image.open.return_value = mock_img

            # Create dummy output files
            temp_gif = temp_dir / "temp.gif"
            temp_gif.write_bytes(b"dummy gif content")
            output_path.write_bytes(b"dummy png content")

            result = video_to_spritesheet(
                str(sample_video_file),
                str(output_path),
                grid="5x2",
                fps=5,
                duration=2.0,
                max_width=640,
                max_height=360,
            )

            assert result == output_path
            mock_create_spritesheet.assert_called_once()

    def test_video_to_spritesheet_auto_grid(self, temp_dir, sample_video_file):
        """Test video to spritesheet with automatic grid calculation."""
        output_path = temp_dir / "output.png"

        with (
            patch("sprite_processor.video.VideoFileClip") as mock_clip,
            patch("sprite_processor.video.extract_gif_frames") as mock_extract,
            patch("sprite_processor.cli._create_spritesheet") as mock_create_spritesheet,
        ):
            mock_video = MagicMock()
            mock_video.duration = 5.0
            mock_video.fps = 24.0
            mock_video.size = (1280, 720)
            mock_video.w = 1280
            mock_video.h = 720
            mock_video.resize.return_value = mock_video
            mock_video.subclip.return_value = mock_video
            mock_video.write_gif.return_value = None
            mock_video.set_end.return_value = mock_video

            # Mock 12 frames
            mock_frames = [MagicMock() for _ in range(12)]
            mock_video.iter_frames.return_value = mock_frames

            mock_clip.return_value.__enter__.return_value = mock_video

            # Mock the extracted frames
            mock_frames = []
            for i in range(12):
                mock_frame = MagicMock()
                mock_frame.size = (640, 360)
                mock_frames.append(mock_frame)
            mock_extract.return_value = mock_frames

            # Mock the spritesheet creation
            mock_create_spritesheet.return_value = output_path

            with patch("sprite_processor.video.Image") as mock_image:
                mock_img = MagicMock()
                mock_img.size = (640, 360)
                mock_image.new.return_value = mock_img
                mock_image.open.return_value = mock_img

            # Create dummy output files
            temp_gif = temp_dir / "temp.gif"
            temp_gif.write_bytes(b"dummy gif content")
            output_path.write_bytes(b"dummy png content")

            video_to_spritesheet(
                str(sample_video_file),
                str(output_path),
                grid="4x3",  # 12 frames = 4x3 grid
                fps=6,
                duration=2.0,
                max_width=640,
                max_height=360,
            )

            mock_create_spritesheet.assert_called_once()


class TestAnalyzeVideo:
    """Test the analyze_video function."""

    def test_analyze_video_basic(self, temp_dir, sample_video_file):
        """Test basic video analysis."""
        with patch("sprite_processor.video.VideoFileClip") as mock_clip:
            mock_video = MagicMock()
            mock_video.duration = 5.0
            mock_video.fps = 24.0
            mock_video.size = (1280, 720)

            mock_clip.return_value.__enter__.return_value = mock_video

            result = analyze_video(str(sample_video_file))

            assert "fps" in result
            assert "duration" in result
            assert "frames" in result
            assert "width" in result
            assert "height" in result

            assert result["fps"] == 10  # Default recommended FPS
            assert result["duration"] == 5.0
            assert result["frames"] == 50  # 5.0 * 10 FPS
            assert result["width"] == 1280
            assert result["height"] == 720

    def test_analyze_video_custom_fps(self, temp_dir, sample_video_file):
        """Test video analysis with custom FPS."""
        with patch("sprite_processor.video.VideoFileClip") as mock_clip:
            mock_video = MagicMock()
            mock_video.duration = 3.0
            mock_video.fps = 30.0
            mock_video.size = (1920, 1080)

            mock_clip.return_value.__enter__.return_value = mock_video

            result = analyze_video(str(sample_video_file), target_fps=15)

            assert result["fps"] == 15
            assert result["duration"] == 3.0
            assert result["frames"] == 45  # 3.0 * 15 FPS

    def test_analyze_video_short_duration(self, temp_dir, sample_video_file):
        """Test video analysis with very short duration."""
        with patch("sprite_processor.video.VideoFileClip") as mock_clip:
            mock_video = MagicMock()
            mock_video.duration = 0.5  # Very short video
            mock_video.fps = 60.0
            mock_video.size = (640, 480)

            mock_clip.return_value.__enter__.return_value = mock_video

            result = analyze_video(str(sample_video_file))

            # Should still recommend reasonable values
            assert result["fps"] >= 5
            assert result["frames"] >= 1

    def test_analyze_video_nonexistent_file(self, temp_dir):
        """Test analyze_video with non-existent file."""
        with pytest.raises(Exception):  # VideoFileClip will raise an exception
            analyze_video("nonexistent.mp4")


class TestVideoModuleImports:
    """Test that video module functions are properly importable."""

    def test_import_video_to_gif(self):
        """Test that video_to_gif can be imported."""
        from sprite_processor.video import video_to_gif

        assert callable(video_to_gif)

    def test_import_video_to_spritesheet(self):
        """Test that video_to_spritesheet can be imported."""
        from sprite_processor.video import video_to_spritesheet

        assert callable(video_to_spritesheet)

    def test_import_analyze_video(self):
        """Test that analyze_video can be imported."""
        from sprite_processor.video import analyze_video

        assert callable(analyze_video)
