"""OBS WebSocket client for video recording."""

import asyncio
import logging
from pathlib import Path

import obsws_python as obs
from obsws_python.error import OBSSDKError

logger = logging.getLogger(__name__)


class OBSClient:
    """Client for controlling OBS via WebSocket.

    This class provides methods to control OBS recording functionality
    through the OBS WebSocket API.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 4455,
        password: str | None = None,
        timeout: float = 3.0,
    ) -> None:
        """Initialize OBS client.

        Args:
            host: OBS WebSocket server host.
            port: OBS WebSocket server port.
            password: OBS WebSocket server password.
            timeout: Connection timeout in seconds.
        """
        self._host = host
        self._port = port
        self._password = password
        self._timeout = timeout
        self._client: obs.ReqClient | None = None

    def connect(self) -> None:
        """Connect to OBS WebSocket server."""
        if self._client is not None:
            logger.warning("Already connected to OBS")
            return

        try:
            self._client = obs.ReqClient(
                host=self._host,
                port=self._port,
                password=self._password,
                timeout=self._timeout,
            )
            logger.info(f"Connected to OBS at {self._host}:{self._port}")
        except Exception as e:
            logger.error(f"Failed to connect to OBS: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from OBS WebSocket server."""
        if self._client is None:
            return

        try:
            if self.is_recording():
                self.stop_recording()
        except OBSSDKError:
            pass  # Ignore errors during cleanup

        self._client = None
        logger.info("Disconnected from OBS")

    def is_recording(self) -> bool:
        """Check if OBS is currently recording.

        Returns:
            True if recording, False otherwise.
        """
        if self._client is None:
            raise RuntimeError("Not connected to OBS")

        try:
            status = self._client.get_record_status()
            return status.output_active  # pyright: ignore

        except OBSSDKError as e:
            logger.error(f"Failed to get recording status: {e}")
            return False

    def start_recording(self) -> None:
        """Start recording in OBS."""
        if self._client is None:
            raise RuntimeError("Not connected to OBS")

        if self.is_recording():
            logger.warning("Already recording")
            return

        try:
            self._client.start_record()
            logger.info("Started recording")
        except OBSSDKError as e:
            logger.error(f"Failed to start recording: {e}")
            raise

    def stop_recording(self) -> Path:
        """Stop recording in OBS.

        Returns:
            Path to the recorded video file.
        """
        if self._client is None:
            raise RuntimeError("Not connected to OBS")

        if not self.is_recording():
            raise RuntimeError("Not currently recording")

        try:
            result = self._client.stop_record()
            output_path = Path(result.output_path)  # pyright: ignore
            logger.info(f"Stopped recording: {output_path}")
            return output_path
        except OBSSDKError as e:
            logger.error(f"Failed to stop recording: {e}")
            raise

    async def record_video(self, duration: float) -> Path:
        """Record video for specified duration.

        Args:
            duration: Recording duration in seconds.

        Returns:
            Path to the recorded video file.
        """
        self.start_recording()
        await asyncio.sleep(duration)
        return self.stop_recording()

    def __enter__(self) -> "OBSClient":
        """Enter context manager."""
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        """Exit context manager."""
        self.disconnect()
