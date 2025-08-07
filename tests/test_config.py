"""Tests for configuration management."""

import os

import pytest
from pytest_mock import MockerFixture

from obs_rec.config import Config


class TestConfig:
    """Test suite for Config."""

    def test_config_dataclass(self) -> None:
        """Test Config dataclass initialization."""
        config = Config(
            discord_token="test_token",
            channel_id=123456789,
            obs_host="example.com",
            obs_port=1234,
            obs_password="secret",
            recording_duration=60.0,
            recording_interval=3600.0,
            video_max_size_mb=50.0,
        )

        assert config.discord_token == "test_token"
        assert config.channel_id == 123456789
        assert config.obs_host == "example.com"
        assert config.obs_port == 1234
        assert config.obs_password == "secret"
        assert config.recording_duration == 60.0
        assert config.recording_interval == 3600.0
        assert config.video_max_size_mb == 50.0

    def test_from_env_success(self, mocker: MockerFixture) -> None:
        """Test loading configuration from environment variables."""
        env_vars = {
            "DISCORD_BOT_TOKEN": "test_token",
            "DISCORD_CHANNEL_ID": "987654321",
            "OBS_HOST": "obs.example.com",
            "OBS_PORT": "5555",
            "OBS_PASSWORD": "secret123",
            "RECORDING_DURATION": "45",
            "RECORDING_INTERVAL": "900",
            "VIDEO_MAX_SIZE_MB": "30",
        }
        mocker.patch.dict(os.environ, env_vars, clear=True)

        config = Config.from_env()

        assert config.discord_token == "test_token"
        assert config.channel_id == 987654321
        assert config.obs_host == "obs.example.com"
        assert config.obs_port == 5555
        assert config.obs_password == "secret123"
        assert config.recording_duration == 45.0
        assert config.recording_interval == 900.0
        assert config.video_max_size_mb == 30.0

    def test_from_env_defaults(self, mocker: MockerFixture) -> None:
        """Test loading configuration with default values."""
        env_vars = {
            "DISCORD_BOT_TOKEN": "test_token",
            "DISCORD_CHANNEL_ID": "123456789",
        }
        mocker.patch.dict(os.environ, env_vars, clear=True)

        config = Config.from_env()

        assert config.discord_token == "test_token"
        assert config.channel_id == 123456789
        assert config.obs_host == "localhost"
        assert config.obs_port == 4455
        assert config.obs_password is None
        assert config.recording_duration == 30.0
        assert config.recording_interval == 1800.0
        assert config.video_max_size_mb == 25.0

    def test_from_env_missing_token(self, mocker: MockerFixture) -> None:
        """Test loading configuration with missing Discord token."""
        env_vars = {
            "DISCORD_CHANNEL_ID": "123456789",
        }
        mocker.patch.dict(os.environ, env_vars, clear=True)

        with pytest.raises(ValueError, match="DISCORD_BOT_TOKEN is not set"):
            Config.from_env()

    def test_from_env_missing_channel_id(self, mocker: MockerFixture) -> None:
        """Test loading configuration with missing channel ID."""
        env_vars = {
            "DISCORD_BOT_TOKEN": "test_token",
        }
        mocker.patch.dict(os.environ, env_vars, clear=True)

        with pytest.raises(ValueError, match="DISCORD_CHANNEL_ID is not set"):
            Config.from_env()

    def test_from_env_invalid_channel_id(self, mocker: MockerFixture) -> None:
        """Test loading configuration with invalid channel ID."""
        env_vars = {
            "DISCORD_BOT_TOKEN": "test_token",
            "DISCORD_CHANNEL_ID": "not_a_number",
        }
        mocker.patch.dict(os.environ, env_vars, clear=True)

        with pytest.raises(ValueError, match="Invalid DISCORD_CHANNEL_ID"):
            Config.from_env()
