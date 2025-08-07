"""Configuration management for video recording bot."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from dotenv import load_dotenv


@dataclass
class Config:
    """Bot configuration."""

    # Discord settings
    discord_token: str
    channel_id: int

    # OBS settings
    obs_host: str = "localhost"
    obs_port: int = 4455
    obs_password: str | None = None

    # Recording settings
    recording_duration: float = 30.0  # seconds
    recording_interval: float = 1800.0  # seconds (30 minutes)
    video_max_size_mb: float = 25.0  # Discord file size limit

    @classmethod
    def from_env(cls) -> Self:
        """Load configuration from environment variables.

        Returns:
            Configuration instance.

        Raises:
            ValueError: If required environment variables are missing.
        """
        load_dotenv()

        discord_token = os.getenv("DISCORD_BOT_TOKEN")
        if not discord_token:
            raise ValueError("DISCORD_BOT_TOKEN is not set")

        channel_id_str = os.getenv("DISCORD_CHANNEL_ID")
        if not channel_id_str:
            raise ValueError("DISCORD_CHANNEL_ID is not set")

        try:
            channel_id = int(channel_id_str)
        except ValueError:
            raise ValueError(f"Invalid DISCORD_CHANNEL_ID: {channel_id_str}")

        return cls(
            discord_token=discord_token,
            channel_id=channel_id,
            obs_host=os.getenv("OBS_HOST", "localhost"),
            obs_port=int(os.getenv("OBS_PORT", "4455")),
            obs_password=os.getenv("OBS_PASSWORD"),
            recording_duration=float(os.getenv("RECORDING_DURATION", "30")),
            recording_interval=float(os.getenv("RECORDING_INTERVAL", "1800")),
            video_max_size_mb=float(os.getenv("VIDEO_MAX_SIZE_MB", "25")),
        )
