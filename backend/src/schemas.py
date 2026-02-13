"""Data contracts for Bitcoin transaction ingestion from Mempool.space API.

All models use Pydantic v2 with automatic camelCase ↔ snake_case mapping.
Monetary values are strictly int (Satoshis).
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase for API serialization."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class Prevout(BaseModel):
    """Previous output reference in a transaction input."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        strict=True,
    )

    scriptpubkey_address: Optional[str] = None
    value: int = Field(..., description="Value in Satoshis")


class Vin(BaseModel):
    """Transaction input (Vin) model."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        strict=True,
    )

    txid: str = Field(..., description="Transaction ID (hex string)")
    vout: int = Field(..., description="Output index")
    prevout: Optional[Prevout] = None
    scriptsig: Optional[str] = None
    witness: Optional[List[str]] = None
    is_coinbase: bool
    sequence: int

    @field_validator("txid")
    @classmethod
    def validate_txid_hex(cls, v: str) -> str:
        """Ensure txid is a valid hex string."""
        if not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError(f"txid must be a hex string, got: {v}")
        return v.lower()


class Vout(BaseModel):
    """Transaction output (Vout) model."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        strict=True,
    )

    scriptpubkey_address: Optional[str] = None
    value: int = Field(..., description="Value in Satoshis")


class Status(BaseModel):
    """Transaction confirmation status."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        strict=True,
    )

    confirmed: bool
    block_height: Optional[int] = None
    block_hash: Optional[str] = None
    block_time: Optional[int] = None


class Transaction(BaseModel):
    """Bitcoin transaction from Mempool.space API.
    
    Source: GET /api/block/:hash/txs
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        strict=True,
    )

    txid: str = Field(..., description="Transaction ID (hex string)")
    version: int
    locktime: int
    vin: List[Vin] = Field(..., min_length=1, description="Transaction inputs")
    vout: List[Vout] = Field(..., min_length=1, description="Transaction outputs")
    size: int
    weight: int
    fee: int = Field(..., description="Transaction fee in Satoshis")
    status: Status

    @field_validator("txid")
    @classmethod
    def validate_txid_hex(cls, v: str) -> str:
        """Ensure txid is a valid hex string."""
        if not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError(f"txid must be a hex string, got: {v}")
        return v.lower()


# ============================================================================
# Mempool WebSocket Event Models
# ============================================================================


class MempoolBlock(BaseModel):
    """Mempool block statistics from WebSocket events."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        strict=True,
    )

    block_size: int = Field(..., description="Block size in bytes")
    block_v_size: float = Field(..., description="Block virtual size")
    n_tx: int = Field(..., description="Number of transactions")
    total_fees: int = Field(..., description="Total fees in Satoshis")
    median_fee: float = Field(..., description="Median fee rate")
    fee_range: List[float] = Field(..., description="Fee rate range")


class MempoolInfo(BaseModel):
    """Mempool information from WebSocket stats event."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        strict=True,
    )

    size: int = Field(..., description="Number of transactions in mempool")
    bytes: int = Field(..., description="Total size in bytes")
    usage: Optional[int] = Field(None, description="Memory usage")
    total_fee: int = Field(..., description="Total fees in Satoshis")
    mempool_min_fee: Optional[float] = Field(None, description="Minimum fee rate")
    min_relay_tx_fee: Optional[float] = Field(None, description="Minimum relay fee rate")

    @field_validator("total_fee", mode="before")
    @classmethod
    def convert_btc_to_satoshis(cls, v: float | int) -> int:
        """Convert BTC float from API to Satoshis integer.

        The mempool.space API returns total_fee as BTC (float).
        We convert at the boundary to avoid IEEE 754 precision errors downstream.
        Uses round() before int() to prevent truncation (e.g. 0.29999... → 30000000).
        """
        if isinstance(v, float):
            return int(round(v * 100_000_000))
        return v


class MempoolStats(BaseModel):
    """Wrapper for mempool statistics WebSocket event."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        strict=True,
    )

    mempool_info: MempoolInfo = Field(..., description="Mempool information")


# ============================================================================
# Confirmed Block Models (REST API + WebSocket)
# ============================================================================


class ConfirmedBlockExtras(BaseModel):
    """Fee and mining metadata from confirmed blocks.
    
    Normalizes both REST API (backfill) and WebSocket (live) sources.
    All fields have defaults since extras may be partial.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    virtual_size: float = Field(default=0.0, description="Block virtual size in vBytes")
    total_fees: int = Field(default=0, description="Total fees in Satoshis")
    median_fee: float = Field(default=0.0, description="Median fee rate in sat/vB")
    fee_range: List[float] = Field(default_factory=list, description="Fee rate distribution")
    pool: Optional[dict] = Field(default=None, description="Mining pool info")


class ConfirmedBlock(BaseModel):
    """Confirmed (mined) block from mempool.space.
    
    Single model for both sources:
    - REST API: GET /api/v1/blocks/{startHeight}
    - WebSocket: block event (signal) + GET /api/v1/block/{hash}
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str = Field(..., description="Block hash")
    height: int = Field(..., description="Block height")
    timestamp: int = Field(..., description="Block timestamp (unix)")
    size: int = Field(..., description="Block size in bytes")
    tx_count: int = Field(..., description="Number of transactions")
    extras: ConfirmedBlockExtras = Field(
        default_factory=ConfirmedBlockExtras,
        description="Fee and mining metadata",
    )

