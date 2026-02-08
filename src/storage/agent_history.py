"""Persistence layer for AI Agent decision history.

Stores Orchestrator decisions in a dedicated DuckDB database to avoid
file lock conflicts with the main storage process.
"""

from datetime import datetime, timezone
from typing import Optional

import duckdb
from pydantic import BaseModel, Field

from src.config import settings


class AgentDecisionRecord(BaseModel):
    """Record of a single decision made by the AI Orchestrator.

    Captures the decision action, market context (fees), and AI reasoning
    for historical analysis and model improvement.
    """

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the decision",
    )
    action: str = Field(..., description="Decision action (e.g., 'WAIT', 'BROADCAST')")
    current_fee: int = Field(..., description="Current transaction fee in sat/vB")
    recommended_fee: int = Field(..., description="Recommended fee from market data in sat/vB")
    ai_confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="AI confidence score (0.0-1.0)",
    )
    ai_reasoning: str = Field(..., description="LLM-generated explanation for the decision")
    model_version: str = Field(
        default="neuro-symbolic-v1",
        description="Version identifier of the decision model",
    )


class AgentHistory:
    """Manages persistence of AI agent decisions in DuckDB.

    Uses a separate database file (agent_history.duckdb) to avoid
    file locking conflicts with the main mempool data storage.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialize the agent history database connection.

        Args:
            db_path: Path to the DuckDB database file. Defaults to settings.agent_history_path.
        """
        self._db_path = db_path if db_path is not None else settings.agent_history_path
        self._init_db()

    def _init_db(self) -> None:
        """Create the decision_history table if it doesn't exist."""
        conn = duckdb.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decision_history (
                    timestamp TIMESTAMP NOT NULL,
                    action VARCHAR NOT NULL,
                    current_fee UBIGINT NOT NULL,
                    recommended_fee UBIGINT NOT NULL,
                    ai_confidence DOUBLE NOT NULL,
                    ai_reasoning VARCHAR NOT NULL,
                    model_version VARCHAR NOT NULL
                )
            """)
        finally:
            conn.close()

    def save_decision(self, record: AgentDecisionRecord) -> None:
        """Persist an agent decision record to DuckDB.

        Opens a new connection, inserts the record, and closes the connection
        to ensure proper resource cleanup and avoid file lock issues.

        Args:
            record: The decision record to persist.
        """
        conn = duckdb.connect(self._db_path)
        try:
            conn.execute(
                """
                INSERT INTO decision_history 
                    (timestamp, action, current_fee, recommended_fee, ai_confidence, ai_reasoning, model_version)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    record.timestamp,
                    record.action,
                    record.current_fee,
                    record.recommended_fee,
                    record.ai_confidence,
                    record.ai_reasoning,
                    record.model_version,
                ],
            )
        finally:
            conn.close()
