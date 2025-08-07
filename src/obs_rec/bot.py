"""Discord bot for automatic video recording."""

import asyncio
import logging
import platform
from datetime import datetime
from pathlib import Path
from typing import override

import discord
from discord.ext import tasks

from .config import Config
from .obs_client import OBSClient
from .video_compressor import VideoCompressor

logger = logging.getLogger(__name__)


class VideoRecordingBot(discord.Client):
    """Discord bot that records and posts videos periodically.

    This bot connects to OBS via WebSocket to record videos at specified
    intervals and posts them to a Discord channel.
    """

    def __init__(self, config: Config) -> None:
        """Initialize the bot.

        Args:
            config: Bot configuration.
        """
        intents = discord.Intents.default()
        super().__init__(intents=intents)

        self.config = config
        self.obs_client = OBSClient(
            host=config.obs_host,
            port=config.obs_port,
            password=config.obs_password,
        )
        self.video_compressor = VideoCompressor(target_size_mb=config.video_max_size_mb)
        self.recording_task.start()

    @override
    async def setup_hook(self) -> None:
        """Set up the bot before starting."""
        try:
            self.obs_client.connect()
            logger.info("OBS client connected during setup")
        except Exception as e:
            logger.error(f"Failed to connect to OBS during setup: {e}")
            raise

    async def on_ready(self) -> None:
        """Handle bot ready event."""
        logger.info(f"Bot logged in as {self.user}")

    @override
    async def close(self) -> None:
        """Clean up resources before closing."""
        self.recording_task.cancel()
        self.obs_client.disconnect()
        await super().close()

    @tasks.loop(seconds=1)
    async def recording_task(self) -> None:
        """Background task for periodic recording."""
        await self.wait_until_ready()

        while not self.is_closed():
            try:
                await self._record_and_post()
                await asyncio.sleep(self.config.recording_interval)
            except Exception as e:
                logger.error(f"Error in recording task: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _record_and_post(self) -> None:
        """Record video and post to Discord channel."""
        channel = self.get_channel(self.config.channel_id)
        if not isinstance(channel, discord.TextChannel):
            logger.error(
                f"Channel {self.config.channel_id} not found or not text channel"
            )
            return

        # Record video
        start_time = datetime.now()
        logger.info(f"Starting recording at {start_time}")

        try:
            video_path = await self.obs_client.record_video(
                self.config.recording_duration
            )
        except Exception as e:
            logger.error(f"Failed to record video: {e}")
            return

        # Check file size and compress if needed
        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        logger.info(f"Recorded video size: {file_size_mb:.2f} MB")

        # Compress video if it exceeds Discord's limit
        video_path = self.video_compressor.compress_if_needed(video_path)

        # Post to Discord
        try:
            await channel.send(
                f"📹 Recording from {start_time.strftime('%Y-%m-%d %H:%M:%S')} in {platform.node()}",
                file=discord.File(video_path),
            )
            logger.info(f"Posted video to channel {self.config.channel_id}")
        except Exception as e:
            logger.error(f"Failed to post video to Discord: {e}")
        finally:
            self._cleanup_video(video_path)

    def _cleanup_video(self, video_path: Path) -> None:
        """Clean up video file after posting.

        Args:
            video_path: Path to video file to delete.
        """
        try:
            video_path.unlink()
            logger.info(f"Deleted video file: {video_path}")
        except Exception as e:
            logger.error(f"Failed to delete video file: {e}")


async def run_bot(config: Config) -> None:
    """Run the Discord bot.

    Args:
        config: Bot configuration.
    """
    bot = VideoRecordingBot(config)
    try:
        await bot.start(config.discord_token)
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    finally:
        await bot.close()
