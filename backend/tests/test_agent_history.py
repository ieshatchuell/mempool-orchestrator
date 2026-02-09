"""Unit tests for AgentHistory persistence layer.

Tests database initialization, record insertion, and Pydantic validation
using isolated temporary databases.
"""

from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pytest
from pydantic import ValidationError

from src.storage.agent_history import AgentDecisionRecord, AgentHistory


class TestAgentHistoryInit:
    """Tests for AgentHistory database initialization."""

    def test_init_creates_table(self, tmp_path: Path) -> None:
        """Verify that initializing AgentHistory creates the decision_history table."""
        db_path = str(tmp_path / "test_agent.duckdb")
        
        # Initialize AgentHistory (should create table)
        AgentHistory(db_path=db_path)
        
        # Verify table exists
        conn = duckdb.connect(db_path, read_only=True)
        try:
            result = conn.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'decision_history'
            """).fetchone()
            
            assert result is not None, "decision_history table should exist"
            assert result[0] == "decision_history"
        finally:
            conn.close()

    def test_init_creates_correct_schema(self, tmp_path: Path) -> None:
        """Verify that the decision_history table has the correct columns."""
        db_path = str(tmp_path / "test_schema.duckdb")
        
        AgentHistory(db_path=db_path)
        
        conn = duckdb.connect(db_path, read_only=True)
        try:
            columns = conn.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'decision_history'
                ORDER BY ordinal_position
            """).fetchall()
            
            expected_columns = [
                ("timestamp", "TIMESTAMP"),
                ("action", "VARCHAR"),
                ("current_fee", "UBIGINT"),
                ("recommended_fee", "UBIGINT"),
                ("ai_confidence", "DOUBLE"),
                ("ai_reasoning", "VARCHAR"),
                ("model_version", "VARCHAR"),
            ]
            
            assert len(columns) == len(expected_columns), "Should have 7 columns"
            for (actual_name, actual_type), (expected_name, expected_type) in zip(
                columns, expected_columns
            ):
                assert actual_name == expected_name, f"Column name mismatch: {actual_name}"
                assert actual_type == expected_type, f"Column type mismatch for {actual_name}"
        finally:
            conn.close()


class TestAgentHistorySave:
    """Tests for AgentHistory.save_decision() method."""

    def test_save_and_retrieve_decision(self, tmp_path: Path) -> None:
        """Verify that saved decisions can be retrieved with all fields intact."""
        db_path = str(tmp_path / "test_save.duckdb")
        history = AgentHistory(db_path=db_path)
        
        # Create a sample record with all fields
        test_timestamp = datetime(2026, 2, 8, 12, 0, 0, tzinfo=timezone.utc)
        record = AgentDecisionRecord(
            timestamp=test_timestamp,
            action="WAIT",
            current_fee=25,
            recommended_fee=15,
            ai_confidence=0.85,
            ai_reasoning="Fees are 40% above historical average, waiting is optimal.",
            model_version="neuro-symbolic-v1",
        )
        
        # Save the record
        history.save_decision(record)
        
        # Retrieve and verify
        conn = duckdb.connect(db_path, read_only=True)
        try:
            row = conn.execute(
                "SELECT * FROM decision_history LIMIT 1"
            ).fetchone()
            
            assert row is not None, "Should have one record"
            
            # Unpack row (order matches schema)
            (
                db_timestamp,
                db_action,
                db_current_fee,
                db_recommended_fee,
                db_confidence,
                db_reasoning,
                db_model_version,
            ) = row
            
            assert db_action == "WAIT"
            assert db_current_fee == 25
            assert db_recommended_fee == 15
            assert db_confidence == 0.85
            assert db_reasoning == "Fees are 40% above historical average, waiting is optimal."
            assert db_model_version == "neuro-symbolic-v1"
            # Timestamp comparison (DuckDB returns timezone-naive)
            assert db_timestamp.year == 2026
            assert db_timestamp.month == 2
            assert db_timestamp.day == 8
        finally:
            conn.close()

    def test_save_multiple_decisions(self, tmp_path: Path) -> None:
        """Verify that multiple decisions can be saved and retrieved."""
        db_path = str(tmp_path / "test_multi.duckdb")
        history = AgentHistory(db_path=db_path)
        
        # Save two different records
        record1 = AgentDecisionRecord(
            action="WAIT",
            current_fee=30,
            recommended_fee=20,
            ai_reasoning="High congestion detected.",
        )
        record2 = AgentDecisionRecord(
            action="BROADCAST",
            current_fee=15,
            recommended_fee=15,
            ai_reasoning="Fees are within normal range.",
        )
        
        history.save_decision(record1)
        history.save_decision(record2)
        
        # Verify count
        conn = duckdb.connect(db_path, read_only=True)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM decision_history"
            ).fetchone()[0]
            
            assert count == 2, "Should have two records"
        finally:
            conn.close()


class TestAgentDecisionRecordValidation:
    """Tests for AgentDecisionRecord Pydantic validation."""

    def test_valid_record_creation(self) -> None:
        """Verify that valid records can be created with required fields."""
        record = AgentDecisionRecord(
            action="BROADCAST",
            current_fee=10,
            recommended_fee=10,
            ai_reasoning="Normal market conditions.",
        )
        
        assert record.action == "BROADCAST"
        assert record.current_fee == 10
        assert record.ai_confidence == 1.0  # Default value
        assert record.model_version == "neuro-symbolic-v1"  # Default value

    def test_missing_required_field_raises_error(self) -> None:
        """Verify that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AgentDecisionRecord(
                action="WAIT",
                # Missing: current_fee, recommended_fee, ai_reasoning
            )
        
        errors = exc_info.value.errors()
        missing_fields = {e["loc"][0] for e in errors}
        
        assert "current_fee" in missing_fields
        assert "recommended_fee" in missing_fields
        assert "ai_reasoning" in missing_fields

    def test_invalid_type_raises_error(self) -> None:
        """Verify that incorrect types raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AgentDecisionRecord(
                action="WAIT",
                current_fee="not_an_int",  # Should be int
                recommended_fee=10,
                ai_reasoning="Test",
            )
        
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "current_fee" for e in errors)

    def test_confidence_bounds_validation(self) -> None:
        """Verify that ai_confidence must be between 0.0 and 1.0."""
        # Above 1.0 should fail
        with pytest.raises(ValidationError) as exc_info:
            AgentDecisionRecord(
                action="WAIT",
                current_fee=10,
                recommended_fee=10,
                ai_reasoning="Test",
                ai_confidence=1.5,
            )
        
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "ai_confidence" for e in errors)
        
        # Below 0.0 should fail
        with pytest.raises(ValidationError):
            AgentDecisionRecord(
                action="WAIT",
                current_fee=10,
                recommended_fee=10,
                ai_reasoning="Test",
                ai_confidence=-0.1,
            )

    def test_timestamp_defaults_to_utc_now(self) -> None:
        """Verify that timestamp defaults to current UTC time."""
        before = datetime.now(timezone.utc)
        
        record = AgentDecisionRecord(
            action="BROADCAST",
            current_fee=10,
            recommended_fee=10,
            ai_reasoning="Test",
        )
        
        after = datetime.now(timezone.utc)
        
        assert before <= record.timestamp <= after
        assert record.timestamp.tzinfo == timezone.utc
