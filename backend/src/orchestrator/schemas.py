"""Pydantic models for the AI Orchestrator Agent.

Defines structured input/output contracts for the fee decision agent.
"""

from typing import Literal

from pydantic import BaseModel, Field


class MempoolContext(BaseModel):
    """Market context passed to the LLM for fee analysis.

    Contains current mempool conditions and historical reference points.
    """

    current_median_fee: float = Field(
        ...,
        description="Current median fee rate (sat/vB) for next block",
        ge=0.0,
    )
    historical_median_fee: float = Field(
        ...,
        description="Historical median fee rate (sat/vB) over recent period",
        ge=0.0,
    )
    mempool_size: int = Field(
        ...,
        description="Number of unconfirmed transactions in mempool",
        ge=0,
    )
    mempool_bytes: int = Field(
        ...,
        description="Total size of mempool in bytes",
        ge=0,
    )
    fee_premium_pct: float = Field(
        ...,
        description="Percentage by which current fee exceeds historical median",
    )
    traffic_level: Literal["LOW", "NORMAL", "HIGH"] = Field(
        ...,
        description="Qualitative assessment of mempool traffic",
    )


class AgentDecision(BaseModel):
    """Structured output from the fee decision agent.

    Represents the agent's recommendation for transaction broadcast timing.
    """

    action: Literal["BROADCAST", "WAIT"] = Field(
        ...,
        description="Recommended action: BROADCAST now or WAIT for lower fees",
    )
    recommended_fee: int = Field(
        ...,
        description="Recommended fee rate in sat/vB",
        ge=1,
    )
    confidence: float = Field(
        ...,
        description="Confidence score for this recommendation (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of the decision rationale",
        max_length=500,
    )
