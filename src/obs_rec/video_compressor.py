"""Video compression utilities using ffmpeg."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoCompressor:
    """Video compressor using ffmpeg."""

    def __init__(self, target_size_mb: float = 25.0) -> None:
        """Initialize video compressor.

        Args:
            target_size_mb: Target file size in megabytes.
        """
        self.target_size_mb = target_size_mb

    def process(self, video_path: Path) -> Path:
        """Process video: compress if needed and convert to MP4.

        Args:
            video_path: Path to video file.

        Returns:
            Path to processed video file.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Input file not found: {video_path}")

        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        needs_compression = file_size_mb > self.target_size_mb
        is_mp4 = video_path.suffix.lower() == ".mp4"

        # Skip if already optimal
        if not needs_compression and is_mp4:
            logger.info(f"Video already optimal: {file_size_mb:.2f} MB, MP4 format")
            return video_path

        # Determine output path
        output_path = video_path.with_stem(f"{video_path.stem}_processed").with_suffix(
            ".mp4"
        )

        # Build ffmpeg command
        if needs_compression:
            logger.info(
                f"Compressing {file_size_mb:.2f} MB to ~{self.target_size_mb} MB"
            )
            cmd = self._build_compress_cmd(video_path, output_path)
        else:
            logger.info(f"Converting {video_path.suffix} to MP4")
            cmd = self._build_convert_cmd(video_path, output_path)

        # Execute ffmpeg
        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed: {e.stderr.decode()}")
            raise RuntimeError(f"Video processing failed: {e}")

        # Verify output
        if not output_path.exists():
            raise RuntimeError(f"Failed to create output: {output_path}")

        output_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Processed: {file_size_mb:.2f} MB -> {output_size_mb:.2f} MB")

        # Delete original
        if output_path != video_path:
            try:
                video_path.unlink()
                logger.info(f"Deleted original: {video_path}")
            except Exception as e:
                logger.warning(f"Failed to delete original: {e}")

        return output_path

    def _build_compress_cmd(self, input_path: Path, output_path: Path) -> list[str]:
        """Build ffmpeg command for compression."""
        # Calculate bitrate (simple formula)
        duration = self._get_duration(input_path)
        target_bits = self.target_size_mb * 1024 * 1024 * 8 * 0.95
        video_bitrate = max(500_000, min(5_000_000, (target_bits / duration) - 128000))
        bitrate_k = f"{int(video_bitrate / 1000)}k"

        return [
            "ffmpeg",
            "-i",
            str(input_path),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-b:v",
            bitrate_k,
            "-maxrate",
            bitrate_k,
            "-bufsize",
            f"{int(video_bitrate / 500)}k",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            "-f",
            "mp4",
            "-y",
            str(output_path),
        ]

    def _build_convert_cmd(self, input_path: Path, output_path: Path) -> list[str]:
        """Build ffmpeg command for simple conversion."""
        return [
            "ffmpeg",
            "-i",
            str(input_path),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            "-y",
            str(output_path),
        ]

    def _get_duration(self, video_path: Path) -> float:
        """Get video duration in seconds."""
        for probe_cmd in [
            # Try format duration first
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            # Try stream duration as fallback
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
        ]:
            try:
                result = subprocess.run(
                    probe_cmd, capture_output=True, text=True, check=True
                )
                duration_str = result.stdout.strip()
                if duration_str and duration_str != "N/A":
                    return float(duration_str)
            except (subprocess.CalledProcessError, ValueError):
                continue

        logger.warning("Could not detect duration, using default 30 seconds")
        return 30.0

    # Compatibility method
    def compress_if_needed(
        self,
        video_path: Path,
        threshold_mb: float | None = None,
        convert_to_mp4: bool = True,
    ) -> Path:
        """Process if needed (for backward compatibility)."""
        if threshold_mb:
            self.target_size_mb = threshold_mb
        return self.process(video_path)
