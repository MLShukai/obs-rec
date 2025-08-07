"""Tests for video compressor."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from obs_rec.video_compressor import VideoCompressor


class TestVideoCompressor:
    """Test suite for VideoCompressor."""

    def test_init(self) -> None:
        """Test VideoCompressor initialization."""
        compressor = VideoCompressor(target_size_mb=50.0)
        assert compressor.target_size_mb == 50.0

    def test_process_success(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test successful video processing."""
        # Create test file
        input_path = tmp_path / "input.mkv"
        input_path.write_bytes(b"x" * (30 * 1024 * 1024))  # 30MB file

        # Expected output path
        output_path = tmp_path / "input_processed.mp4"

        # Mock subprocess and duration detection
        def mock_run(*args, **kwargs):
            cmd = args[0]
            if "ffprobe" in cmd[0]:
                return MagicMock(stdout="30.0")
            elif "ffmpeg" in cmd[0]:
                # Create output file when ffmpeg runs
                output_path.write_bytes(b"compressed")
                return MagicMock()
            return MagicMock()

        mocker.patch("subprocess.run", side_effect=mock_run)

        compressor = VideoCompressor(target_size_mb=25.0)
        result = compressor.process(input_path)

        assert result == output_path
        assert output_path.exists()
        assert not input_path.exists()  # Original should be deleted

    def test_process_already_optimal(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test processing skipped for already optimal video."""
        video_path = tmp_path / "video.mp4"
        # Create 10MB MP4 file (under 25MB limit)
        video_path.write_bytes(b"x" * (10 * 1024 * 1024))

        compressor = VideoCompressor(target_size_mb=25.0)
        result = compressor.process(video_path)

        assert result == video_path  # Should return original

    def test_process_convert_only(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test MP4 conversion without compression."""
        input_path = tmp_path / "input.mkv"
        input_path.write_bytes(b"x" * (10 * 1024 * 1024))  # 10MB file (under limit)

        output_path = tmp_path / "input_processed.mp4"

        def mock_run(*args, **kwargs):
            cmd = args[0]
            if "ffmpeg" in cmd[0]:
                output_path.write_bytes(b"converted")
                return MagicMock()
            return MagicMock()

        mocker.patch("subprocess.run", side_effect=mock_run)

        compressor = VideoCompressor(target_size_mb=25.0)
        result = compressor.process(input_path)

        assert result == output_path
        assert output_path.exists()

    def test_process_input_not_found(self) -> None:
        """Test processing with non-existent input file."""
        compressor = VideoCompressor()

        with pytest.raises(FileNotFoundError, match="Input file not found"):
            compressor.process(Path("/nonexistent/file.mp4"))

    def test_get_duration(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test getting video duration."""
        video_path = tmp_path / "video.mp4"
        video_path.write_bytes(b"fake video")

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value.stdout = "42.5"

        compressor = VideoCompressor()
        duration = compressor._get_duration(video_path)

        assert duration == 42.5

    def test_get_duration_fallback(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test duration detection with fallback."""
        video_path = tmp_path / "video.mkv"
        video_path.write_bytes(b"fake video")

        call_count = 0

        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call fails (format duration)
                return MagicMock(stdout="N/A")
            else:
                # Second call succeeds (stream duration)
                return MagicMock(stdout="45.0")

        mocker.patch("subprocess.run", side_effect=mock_run)

        compressor = VideoCompressor()
        duration = compressor._get_duration(video_path)

        assert duration == 45.0

    def test_get_duration_default(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test duration detection failure uses default."""
        video_path = tmp_path / "video.mp4"
        video_path.write_bytes(b"fake video")

        mocker.patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "ffprobe"),
        )

        compressor = VideoCompressor()
        duration = compressor._get_duration(video_path)

        assert duration == 30.0  # Default fallback

    def test_build_compress_cmd(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test compress command building."""
        input_path = tmp_path / "input.mp4"
        output_path = tmp_path / "output.mp4"

        mocker.patch.object(VideoCompressor, "_get_duration", return_value=30.0)

        compressor = VideoCompressor(target_size_mb=25.0)
        cmd = compressor._build_compress_cmd(input_path, output_path)

        assert "ffmpeg" in cmd[0]
        assert str(input_path) in cmd
        assert str(output_path) in cmd
        assert "-c:v" in cmd
        assert "libx264" in cmd
        assert "-b:v" in cmd

    def test_build_convert_cmd(self, tmp_path: Path) -> None:
        """Test convert command building."""
        input_path = tmp_path / "input.mkv"
        output_path = tmp_path / "output.mp4"

        compressor = VideoCompressor()
        cmd = compressor._build_convert_cmd(input_path, output_path)

        assert "ffmpeg" in cmd[0]
        assert str(input_path) in cmd
        assert str(output_path) in cmd
        assert "-c:v" in cmd
        assert "libx264" in cmd
        assert "-preset" in cmd
        assert "fast" in cmd

    def test_process_ffmpeg_failure(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test handling of ffmpeg failure."""
        input_path = tmp_path / "input.mkv"
        input_path.write_bytes(b"x" * (30 * 1024 * 1024))

        def mock_run(*args, **kwargs):
            cmd = args[0]
            if "ffprobe" in cmd[0]:
                return MagicMock(stdout="30.0")
            elif "ffmpeg" in cmd[0]:
                raise subprocess.CalledProcessError(1, "ffmpeg", stderr=b"Error")
            return MagicMock()

        mocker.patch("subprocess.run", side_effect=mock_run)

        compressor = VideoCompressor()

        with pytest.raises(RuntimeError, match="Video processing failed"):
            compressor.process(input_path)

    def test_compress_if_needed_backward_compat(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test compress_if_needed backward compatibility."""
        video_path = tmp_path / "video.mkv"
        video_path.write_bytes(b"x" * (30 * 1024 * 1024))

        processed_path = tmp_path / "video_processed.mp4"

        # Mock process method
        mock_process = mocker.patch.object(
            VideoCompressor,
            "process",
            return_value=processed_path,
        )

        compressor = VideoCompressor()
        result = compressor.compress_if_needed(video_path, threshold_mb=20.0)

        assert result == processed_path
        assert compressor.target_size_mb == 20.0
        mock_process.assert_called_once_with(video_path)

    def test_process_deletion_failure(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test handling of original file deletion failure."""
        input_path = tmp_path / "input.mkv"
        input_path.write_bytes(b"x" * (30 * 1024 * 1024))

        output_path = tmp_path / "input_processed.mp4"

        def mock_run(*args, **kwargs):
            cmd = args[0]
            if "ffprobe" in cmd[0]:
                return MagicMock(stdout="30.0")
            elif "ffmpeg" in cmd[0]:
                output_path.write_bytes(b"compressed")
                return MagicMock()
            return MagicMock()

        mocker.patch("subprocess.run", side_effect=mock_run)
        mocker.patch.object(Path, "unlink", side_effect=OSError("Permission denied"))

        compressor = VideoCompressor(target_size_mb=25.0)
        result = compressor.process(input_path)

        assert result == output_path
        assert input_path.exists()  # Original still exists due to deletion failure
