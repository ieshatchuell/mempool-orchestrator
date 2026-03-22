
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Centralized application configuration via pydantic-settings.

    All values are loaded from environment variables (or .env file).
    Zero magic strings — every connection URL, topic name, and API endpoint
    is configurable.
    """
    # Kafka (Redpanda)
    kafka_bootstrap_servers: str = "localhost:9092"
    mempool_topic: str = "mempool-raw"
    block_signals_topic: str = "block-signals"

    # Mempool.space external APIs
    mempool_ws_url: str = "wss://mempool.space/api/v1/ws"
    mempool_api_url: str = "https://mempool.space/api"

    # Storage — PostgreSQL (async via asyncpg)
    postgres_dsn: str = "postgresql+asyncpg://mempool:mempool@localhost:5432/mempool"

    # Kafka consumer batch size
    kafka_batch_size: int = 50

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("*", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Sanitizes environment variables by removing leading/trailing whitespace."""
        if isinstance(v, str):
            return v.strip()
        return v

settings = Settings()
