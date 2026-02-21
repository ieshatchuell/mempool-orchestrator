from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Manages application settings and environment variables validation.
    
    Attributes:
        kafka_bootstrap_servers (str): Connection string for the Kafka broker.
        mempool_topic (str): Target Kafka topic for mempool events.
        mempool_ws_url (str): Source WebSocket URL for real-time mempool data.
        mempool_api_url (str): Base URL for Mempool.space REST API.
        strategy_mode (str): PATIENT (treasury, saves 27.7%) or RELIABLE (time-sensitive, 94% hit rate).
    """
    kafka_bootstrap_servers: str = "localhost:9092"
    mempool_topic: str = "mempool-raw"
    mempool_ws_url: str = "wss://mempool.space/api/v1/ws"
    mempool_api_url: str = "https://mempool.space/api"

    # Storage - DuckDB
    duckdb_path: str = "../data/market/mempool_data.duckdb"
    duckdb_batch_size: int = 50  # Messages before commit

    # Agent History - Separate DB to avoid file lock conflicts
    agent_history_path: str = "../data/history/agent_history.duckdb"

    # Strategy Mode - Controls orchestrator fee logic
    strategy_mode: Literal["PATIENT", "RELIABLE"] = "PATIENT"

    # Redis - CQRS read layer (dashboard projections)
    redis_url: str = "redis://localhost:6379/0"

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
