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

    def convert_to_mp4(self, input_path: Path, output_path: Path | None = None) -> Path:
        """Convert video to MP4 format.

        Args:
            input_path: Path to input video file.
            output_path: Path for output MP4. If None, uses input.mp4.

        Returns:
            Path to converted MP4 file.

        Raises:
            RuntimeError: If conversion fails.
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if output_path is None:
            output_path = input_path.with_suffix(".mp4")

        # Skip if already MP4
        if input_path.suffix.lower() == ".mp4" and output_path == input_path:
            logger.info(f"File is already MP4: {input_path}")
            return input_path

        cmd = [
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

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            logger.info(f"Converted to MP4: {input_path} -> {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"MP4 conversion failed: {e.stderr.decode()}")
            raise RuntimeError(f"MP4 conversion failed: {e}")

    def compress(
        self,
        input_path: Path,
        output_path: Path | None = None,
        duration: float | None = None,
    ) -> Path:
        """Compress video file to target size.

        Args:
            input_path: Path to input video file.
            output_path: Path for compressed output. If None, uses input_compressed.mp4.
            duration: Video duration in seconds. If None, will be detected.

        Returns:
            Path to compressed video file.

        Raises:
            RuntimeError: If compression fails.
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if output_path is None:
            output_path = input_path.with_stem(
                f"{input_path.stem}_compressed"
            ).with_suffix(".mp4")

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
            duration_str = result.stdout.strip()
            if duration_str and duration_str != "N/A":
                return float(duration_str)
            else:
                # Try alternative method for MKV files
                logger.warning(
                    "Duration not found with format=duration, trying streams"
                )
                cmd_alt = [
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
                ]
                result_alt = subprocess.run(
                    cmd_alt, capture_output=True, text=True, check=True
                )
                duration_str_alt = result_alt.stdout.strip()
                if duration_str_alt and duration_str_alt != "N/A":
                    return float(duration_str_alt)
                # Default to 30 seconds if detection fails
                logger.warning("Could not detect duration, using default 30 seconds")
                return 30.0
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

        # Ensure maximum quality (should be min, not max)
        video_bitrate = min(video_bitrate, 5_000_000)  # Maximum 5000kbps

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
            "-f",
            "mp4",  # Force MP4 format
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
        self,
        video_path: Path,
        threshold_mb: float | None = None,
        convert_to_mp4: bool = True,
    ) -> Path:
        """Compress video only if it exceeds threshold size and optionally
        convert to MP4.

        Args:
            video_path: Path to video file.
            threshold_mb: Size threshold in MB. Uses target_size_mb if None.
            convert_to_mp4: Whether to convert to MP4 format.

        Returns:
            Path to video (compressed/converted or original).
        """
        if threshold_mb is None:
            threshold_mb = self.target_size_mb

        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        needs_compression = file_size_mb > threshold_mb
        needs_conversion = convert_to_mp4 and video_path.suffix.lower() != ".mp4"

        if not needs_compression and not needs_conversion:
            logger.info(
                f"Video size ({file_size_mb:.2f} MB) within limit and already MP4, skipping processing"
            )
            return video_path

        if needs_compression:
            logger.info(
                f"Video size ({file_size_mb:.2f} MB) exceeds limit, compressing..."
            )
            processed_path = self.compress(video_path)
        elif needs_conversion:
            logger.info(f"Converting {video_path.suffix} to MP4...")
            processed_path = self.convert_to_mp4(video_path)
        else:
            return video_path

        # Delete original if processing successful
        if processed_path != video_path:
            try:
                video_path.unlink()
                logger.info(f"Deleted original video: {video_path}")
            except Exception as e:
                logger.warning(f"Failed to delete original video: {e}")

        return processed_path
