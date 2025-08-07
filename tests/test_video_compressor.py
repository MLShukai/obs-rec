"""Tests for video compressor."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest
from pytest_mock import MockerFixture

from obs_rec.video_compressor import VideoCompressor


class TestVideoCompressor:
    """Test suite for VideoCompressor."""

    def test_init(self) -> None:
        """Test VideoCompressor initialization."""
        compressor = VideoCompressor(target_size_mb=50.0)
        assert compressor.target_size_mb == 50.0

    def test_compress_success(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test successful video compression."""
        # Create test files
        input_path = tmp_path / "input.mp4"
        input_path.write_bytes(b"fake video data")
        output_path = tmp_path / "output.mp4"

        # Mock subprocess and duration detection
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value.stdout = "30.0"  # Duration

        compressor = VideoCompressor()

        # Mock output file creation
        def create_output(*args, **kwargs):
            if "ffmpeg" in args[0][0]:
                output_path.write_bytes(b"compressed")
            return MagicMock(stdout="30.0")

        mock_run.side_effect = create_output

        result = compressor.compress(input_path, output_path, duration=30.0)

        assert result == output_path
        assert output_path.exists()

    def test_compress_input_not_found(self) -> None:
        """Test compression with non-existent input file."""
        compressor = VideoCompressor()

        with pytest.raises(FileNotFoundError, match="Input file not found"):
            compressor.compress(Path("/nonexistent/file.mp4"))

    def test_get_duration(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test getting video duration."""
        video_path = tmp_path / "video.mp4"
        video_path.write_bytes(b"fake video")

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value.stdout = "42.5"

        compressor = VideoCompressor()
        duration = compressor._get_duration(video_path)

        assert duration == 42.5
        mock_run.assert_called_once()

    def test_get_duration_failure(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test duration detection failure fallback."""
        video_path = tmp_path / "video.mp4"
        video_path.write_bytes(b"fake video")

        mocker.patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "ffprobe"),
        )

        compressor = VideoCompressor()
        duration = compressor._get_duration(video_path)

        assert duration == 30.0  # Default fallback

    def test_calculate_bitrate(self) -> None:
        """Test bitrate calculation."""
        compressor = VideoCompressor(target_size_mb=25.0)

        # 30 second video
        bitrate = compressor._calculate_bitrate(30.0)
        bitrate_k = int(bitrate[:-1])

        # Should be around 6500k for 25MB/30s minus audio
        assert bitrate_k > 5000
        assert bitrate_k < 8000

    def test_run_ffmpeg_success(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test successful ffmpeg execution."""
        input_path = tmp_path / "input.mp4"
        output_path = tmp_path / "output.mp4"

        mock_run = mocker.patch("subprocess.run")

        compressor = VideoCompressor()
        compressor._run_ffmpeg(input_path, output_path, "1000k")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "ffmpeg" in args[0]
        assert str(input_path) in args
        assert str(output_path) in args
        assert "1000k" in args

    def test_run_ffmpeg_failure(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test ffmpeg execution failure."""
        input_path = tmp_path / "input.mp4"
        output_path = tmp_path / "output.mp4"

        mocker.patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(
                1, "ffmpeg", stderr=b"Error message"
            ),
        )

        compressor = VideoCompressor()

        with pytest.raises(RuntimeError, match="Video compression failed"):
            compressor._run_ffmpeg(input_path, output_path, "1000k")

    def test_compress_if_needed_under_limit(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test compression skipped when file is under limit."""
        video_path = tmp_path / "video.mp4"
        # Create 10MB file (under 25MB limit)
        video_path.write_bytes(b"x" * (10 * 1024 * 1024))

        compressor = VideoCompressor(target_size_mb=25.0)
        result = compressor.compress_if_needed(video_path)

        assert result == video_path  # Should return original

    def test_compress_if_needed_over_limit(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test compression triggered when file exceeds limit."""
        video_path = tmp_path / "video.mp4"
        # Create 30MB file (over 25MB limit)
        video_path.write_bytes(b"x" * (30 * 1024 * 1024))

        compressed_path = tmp_path / "video_compressed.mp4"

        # Mock compress method
        mock_compress = mocker.patch.object(
            VideoCompressor,
            "compress",
            return_value=compressed_path,
        )

        # Create compressed file
        compressed_path.write_bytes(b"compressed")

        compressor = VideoCompressor(target_size_mb=25.0)
        result = compressor.compress_if_needed(video_path)

        assert result == compressed_path
        mock_compress.assert_called_once_with(video_path)
        assert not video_path.exists()  # Original should be deleted

    def test_compress_if_needed_deletion_failure(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test handling of original file deletion failure."""
        video_path = tmp_path / "video.mp4"
        video_path.write_bytes(b"x" * (30 * 1024 * 1024))

        compressed_path = tmp_path / "video_compressed.mp4"
        compressed_path.write_bytes(b"compressed")

        mocker.patch.object(
            VideoCompressor,
            "compress",
            return_value=compressed_path,
        )

        # Mock unlink to raise exception
        mocker.patch.object(Path, "unlink", side_effect=OSError("Permission denied"))

        compressor = VideoCompressor(target_size_mb=25.0)
        result = compressor.compress_if_needed(video_path)

        assert result == compressed_path
        assert video_path.exists()  # Original still exists due to deletion failure
