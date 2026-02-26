"""Unit tests for configuration management.

Tests validate Pydantic-based settings loading, environment variable handling,
and field validators for the Settings class.
"""

import pytest
from pydantic import ValidationError

from src.core.config import Settings


class TestSettingsDefaults:
    """Test suite for default configuration values."""

    def test_default_values_loaded_correctly(self):
        """Verify Settings loads with correct default values when no env vars set."""
        settings = Settings(_env_file=None)
        
        assert settings.kafka_bootstrap_servers == "localhost:9092"
        assert settings.mempool_topic == "mempool-raw"
        assert settings.mempool_ws_url == "wss://mempool.space/api/v1/ws"
        assert settings.mempool_api_url == "https://mempool.space/api"
        assert settings.postgres_dsn == "postgresql+asyncpg://mempool:mempool@localhost:5432/mempool"
        assert settings.kafka_batch_size == 50

    def test_settings_types_are_correct(self):
        """Verify field types are enforced correctly."""
        settings = Settings(_env_file=None)
        
        assert isinstance(settings.kafka_bootstrap_servers, str)
        assert isinstance(settings.mempool_topic, str)
        assert isinstance(settings.mempool_ws_url, str)
        assert isinstance(settings.postgres_dsn, str)
        assert isinstance(settings.kafka_batch_size, int)


class TestEnvironmentVariableOverrides:
    """Test suite for environment variable overrides."""

    def test_env_var_overrides_default(self, monkeypatch):
        """Verify environment variables override default values."""
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "kafka.example.com:9093")
        monkeypatch.setenv("MEMPOOL_TOPIC", "custom-topic")
        monkeypatch.setenv("KAFKA_BATCH_SIZE", "100")
        monkeypatch.setenv("POSTGRES_DSN", "postgresql+asyncpg://user:pass@db:5432/prod")
        
        settings = Settings(_env_file=None)
        
        assert settings.kafka_bootstrap_servers == "kafka.example.com:9093"
        assert settings.mempool_topic == "custom-topic"
        assert settings.kafka_batch_size == 100
        assert settings.postgres_dsn == "postgresql+asyncpg://user:pass@db:5432/prod"

    def test_partial_env_var_override(self, monkeypatch):
        """Verify partial environment overrides work (some env vars set, others default)."""
        monkeypatch.setenv("MEMPOOL_WS_URL", "wss://custom.mempool.api/ws")
        
        settings = Settings(_env_file=None)
        
        assert settings.mempool_ws_url == "wss://custom.mempool.api/ws"
        assert settings.kafka_bootstrap_servers == "localhost:9092"
        assert settings.mempool_topic == "mempool-raw"


class TestWhitespaceValidator:
    """Test suite for whitespace stripping field validator."""

    def test_leading_whitespace_stripped(self, monkeypatch):
        """Verify leading whitespace is removed from string environment variables."""
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "   localhost:9092")
        monkeypatch.setenv("MEMPOOL_TOPIC", "\tmempool-raw")
        
        settings = Settings(_env_file=None)
        
        assert settings.kafka_bootstrap_servers == "localhost:9092"
        assert settings.mempool_topic == "mempool-raw"

    def test_trailing_whitespace_stripped(self, monkeypatch):
        """Verify trailing whitespace is removed from string environment variables."""
        monkeypatch.setenv("MEMPOOL_WS_URL", "wss://mempool.space/api/v1/ws   ")
        monkeypatch.setenv("POSTGRES_DSN", "postgresql+asyncpg://mempool:mempool@localhost:5432/mempool\t\n")
        
        settings = Settings(_env_file=None)
        
        assert settings.mempool_ws_url == "wss://mempool.space/api/v1/ws"
        assert settings.postgres_dsn == "postgresql+asyncpg://mempool:mempool@localhost:5432/mempool"

    def test_both_leading_and_trailing_whitespace_stripped(self, monkeypatch):
        """Verify both leading and trailing whitespace is removed."""
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "  kafka:9092  ")
        
        settings = Settings(_env_file=None)
        
        assert settings.kafka_bootstrap_servers == "kafka:9092"

    def test_integer_fields_not_affected_by_whitespace_validator(self, monkeypatch):
        """Verify integer fields are not affected by the string whitespace validator."""
        monkeypatch.setenv("KAFKA_BATCH_SIZE", "75")
        
        settings = Settings(_env_file=None)
        
        assert settings.kafka_batch_size == 75
        assert isinstance(settings.kafka_batch_size, int)


class TestInvalidConfiguration:
    """Test suite for invalid configuration scenarios."""

    def test_invalid_integer_type_raises_error(self, monkeypatch):
        """Verify ValidationError is raised for invalid integer values."""
        monkeypatch.setenv("KAFKA_BATCH_SIZE", "not_a_number")
        
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=None)
        
        error_msg = str(exc_info.value).lower()
        assert "kafka_batch_size" in error_msg or "kafkabatchsize" in error_msg

    def test_negative_batch_size_allowed(self, monkeypatch):
        """Verify negative integers are accepted (no min validation in current schema)."""
        monkeypatch.setenv("KAFKA_BATCH_SIZE", "-10")
        
        settings = Settings(_env_file=None)
        assert settings.kafka_batch_size == -10


class TestConfigModule:
    """Test suite for module-level settings singleton."""

    def test_settings_singleton_exists(self):
        """Verify the module exports a settings singleton."""
        from src.core.config import settings
        
        assert settings is not None
        assert isinstance(settings, Settings)

    def test_settings_singleton_has_expected_attributes(self):
        """Verify the singleton has all expected configuration attributes."""
        from src.core.config import settings
        
        assert hasattr(settings, 'kafka_bootstrap_servers')
        assert hasattr(settings, 'mempool_topic')
        assert hasattr(settings, 'mempool_ws_url')
        assert hasattr(settings, 'postgres_dsn')
        assert hasattr(settings, 'kafka_batch_size')
