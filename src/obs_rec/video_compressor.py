"""Video compression utilities using ffmpeg."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoCompressor:
    """Video compressor using ffmpeg.

    Provides methods to compress video files to meet size constraints
    while maintaining reasonable quality.
    """

    def __init__(self, target_size_mb: float = 25.0) -> None:
        """Initialize video compressor.

        Args:
            target_size_mb: Target file size in megabytes.
        """
        self.target_size_mb = target_size_mb

    def compress(
        self,
        input_path: Path,
        output_path: Path | None = None,
        duration: float | None = None,
    ) -> Path:
        """Compress video file to target size.

        Args:
            input_path: Path to input video file.
            output_path: Path for compressed output. If None, uses input_compressed.ext.
            duration: Video duration in seconds. If None, will be detected.

        Returns:
            Path to compressed video file.

        Raises:
            RuntimeError: If compression fails.
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if output_path is None:
            output_path = input_path.with_stem(f"{input_path.stem}_compressed")

        # Get video duration if not provided
        if duration is None:
            duration = self._get_duration(input_path)

        # Calculate target bitrate
        bitrate = self._calculate_bitrate(duration)

        # Compress video
        self._run_ffmpeg(input_path, output_path, bitrate)

        # Verify output
        if not output_path.exists():
            raise RuntimeError(f"Failed to create compressed video: {output_path}")

        output_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(
            f"Compressed {input_path.name}: "
            f"{input_path.stat().st_size / (1024 * 1024):.2f} MB -> "
            f"{output_size_mb:.2f} MB"
        )

        return output_path

    def _get_duration(self, video_path: Path) -> float:
        """Get video duration using ffprobe.

        Args:
            video_path: Path to video file.

        Returns:
            Duration in seconds.
        """
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError) as e:
            logger.error(f"Failed to get video duration: {e}")
            # Default to 30 seconds if detection fails
            return 30.0

    def _calculate_bitrate(self, duration: float) -> str:
        """Calculate target bitrate for desired file size.

        Args:
            duration: Video duration in seconds.

        Returns:
            Bitrate string for ffmpeg (e.g., "1000k").
        """
        # Target size in bits (with 95% safety margin)
        target_bits = self.target_size_mb * 1024 * 1024 * 8 * 0.95

        # Calculate bitrate (subtract audio bitrate estimate of 128kbps)
        video_bitrate = (target_bits / duration) - 128000

        # Ensure minimum quality
        video_bitrate = max(video_bitrate, 500_000)  # Minimum 500kbps

        # Ensure maximum quality
        video_bitrate = max(video_bitrate, 5_000_000)  # Maximum 5000kbps

        # Convert to kilobits
        video_bitrate_k = int(video_bitrate / 1000)

        return f"{video_bitrate_k}k"

    def _run_ffmpeg(self, input_path: Path, output_path: Path, bitrate: str) -> None:
        """Run ffmpeg compression command.

        Args:
            input_path: Input video path.
            output_path: Output video path.
            bitrate: Target video bitrate.
        """
        cmd = [
            "ffmpeg",
            "-i",
            str(input_path),
            "-c:v",
            "libx264",  # H.264 codec
            "-preset",
            "medium",  # Balance between speed and compression
            "-b:v",
            bitrate,  # Video bitrate
            "-maxrate",
            bitrate,  # Maximum bitrate
            "-bufsize",
            f"{int(bitrate[:-1]) * 2}k",  # Buffer size
            "-c:a",
            "aac",  # AAC audio codec
            "-b:a",
            "128k",  # Audio bitrate
            "-movflags",
            "+faststart",  # Web optimization
            "-y",  # Overwrite output
            str(output_path),
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg compression failed: {e.stderr.decode()}")
            raise RuntimeError(f"Video compression failed: {e}")

    def compress_if_needed(
        self, video_path: Path, threshold_mb: float | None = None
    ) -> Path:
        """Compress video only if it exceeds threshold size.

        Args:
            video_path: Path to video file.
            threshold_mb: Size threshold in MB. Uses target_size_mb if None.

        Returns:
            Path to video (compressed or original).
        """
        if threshold_mb is None:
            threshold_mb = self.target_size_mb

        file_size_mb = video_path.stat().st_size / (1024 * 1024)

        if file_size_mb <= threshold_mb:
            logger.info(
                f"Video size ({file_size_mb:.2f} MB) within limit, skipping compression"
            )
            return video_path

        logger.info(f"Video size ({file_size_mb:.2f} MB) exceeds limit, compressing...")
        compressed_path = self.compress(video_path)

        # Delete original if compression successful
        try:
            video_path.unlink()
            logger.info(f"Deleted original video: {video_path}")
        except Exception as e:
            logger.warning(f"Failed to delete original video: {e}")

        return compressed_path
