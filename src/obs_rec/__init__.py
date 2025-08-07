"""obs-rec - Discord bot for automatic video recording via OBS."""

from importlib import metadata

__version__ = metadata.version(__name__.replace("_", "-"))

from .bot import VideoRecordingBot, run_bot
from .config import Config
from .obs_client import OBSClient
from .video_compressor import VideoCompressor

__all__ = ["VideoRecordingBot", "Config", "OBSClient", "VideoCompressor", "run_bot"]
