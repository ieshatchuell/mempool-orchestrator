"""SQLAlchemy 2.0 ORM models for PostgreSQL persistence.

Mapped from domain schemas. Uses DeclarativeBase + Mapped typed columns.
"""

from datetime import datetime, timezone

from sqlalchemy import String, Float, Integer, BigInteger, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class BlockRecord(Base):
    """Confirmed block record."""

    __tablename__ = "blocks"

    height: Mapped[int] = mapped_column(Integer, primary_key=True)
    hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tx_count: Mapped[int] = mapped_column(Integer, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    median_fee: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_fees: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    pool_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fee_range: Mapped[list | None] = mapped_column(JSONB, nullable=True)


class MempoolSnapshot(Base):
    """Point-in-time mempool state capture."""

    __tablename__ = "mempool_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    tx_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_fee_sats: Mapped[int] = mapped_column(BigInteger, nullable=False)
    median_fee: Mapped[float] = mapped_column(Float, nullable=False)


class MempoolBlockProjection(Base):
    """Projected mempool block from WebSocket mempool-blocks events.

    Snapshot pattern: all rows are replaced (DELETE + INSERT) on each
    mempool-blocks event. The block_index field preserves ordering
    (0 = next block, 1 = second block, etc.).
    """

    __tablename__ = "mempool_block_projections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    block_index: Mapped[int] = mapped_column(Integer, nullable=False)
    block_size: Mapped[int] = mapped_column(Integer, nullable=False)
    block_v_size: Mapped[float] = mapped_column(Float, nullable=False)
    n_tx: Mapped[int] = mapped_column(Integer, nullable=False)
    total_fees: Mapped[int] = mapped_column(BigInteger, nullable=False)
    median_fee: Mapped[float] = mapped_column(Float, nullable=False)
    fee_range: Mapped[list | None] = mapped_column(JSONB, nullable=True)


class AdvisoryRecord(Base):
    """Persisted fee advisory (RBF/CPFP recommendation)."""

    __tablename__ = "advisories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    txid: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    current_fee_rate: Mapped[float] = mapped_column(Float, nullable=False)
    target_fee_rate: Mapped[float] = mapped_column(Float, nullable=False)
    rbf_fee_sats: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    cpfp_fee_sats: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
