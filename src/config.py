from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Manages application settings and environment variables validation.
    
    Attributes:
        kafka_bootstrap_servers (str): Connection string for the Kafka broker.
        mempool_topic (str): Target Kafka topic for mempool events.
        mempool_ws_url (str): Source WebSocket URL for real-time mempool data.
    """
    kafka_bootstrap_servers: str = "localhost:9092"
    mempool_topic: str = "mempool-raw"
    mempool_ws_url: str = "wss://mempool.space/api/v1/ws"

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
