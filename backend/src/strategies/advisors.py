"""RBF & CPFP Fee Advisors — Pure deterministic functions.

Evaluate stuck transactions and calculate optimal replacement/child fees.
No I/O, no DuckDB — fully testable with plain values.

Reference:
- RBF: BIP-125 (https://github.com/bitcoin/bips/blob/master/bip-0125.mediawiki)
- CPFP: Bitcoin Ops (https://bitcoinops.org/en/topics/cpfp/)

Usage:
    The `target_fee_rate` parameter comes from `evaluate_market_rules()` in the
    orchestrator. This ensures advisors respect the active strategy mode
    (PATIENT or RELIABLE).
"""

import math

from pydantic import BaseModel, Field


# =============================================================================
# CONSTANTS
# =============================================================================

# Estimated child transaction virtual size for CPFP calculations.
# Based on a standard P2WPKH (Pay-to-Witness-Public-Key-Hash) spend:
#   1 input (41 vB) + 1 output (31 vB) + overhead (10.5 vB) + witness (~58.5 vB) ≈ 141 vB
ESTIMATED_CHILD_VSIZE: float = 141.0

# Bitcoin Core default minimum relay transaction fee rate.
# Transactions below this rate won't be relayed by most nodes.
MIN_RELAY_FEE_RATE: float = 1.0  # sat/vB


# =============================================================================
# MODELS
# =============================================================================

class RBFAdvice(BaseModel):
    """Advice for replacing a stuck transaction via RBF (Sender strategy)."""

    is_stuck: bool = Field(
        ...,
        description="Whether the original tx fee rate is below the target",
    )
    original_fee_rate: float = Field(
        ...,
        description="Original transaction fee rate (sat/vB)",
    )
    original_fee_sats: int = Field(
        ...,
        description="Original transaction fee (satoshis)",
    )
    target_fee_rate: float = Field(
        ...,
        description="Recommended replacement fee rate (sat/vB)",
    )
    target_fee_sats: int = Field(
        ...,
        description="Recommended replacement fee (satoshis), BIP-125 compliant",
    )


class CPFPAdvice(BaseModel):
    """Advice for unsticking a parent tx via CPFP (Receiver strategy)."""

    is_stuck: bool = Field(
        ...,
        description="Whether the parent tx fee rate is below the target",
    )
    parent_fee_rate: float = Field(
        ...,
        description="Parent transaction fee rate (sat/vB)",
    )
    parent_fee_sats: int = Field(
        ...,
        description="Parent transaction fee (satoshis)",
    )
    child_fee_sats: int = Field(
        ...,
        description="Required child transaction fee (satoshis)",
    )
    package_fee_rate: float = Field(
        ...,
        description="Effective package fee rate after CPFP (sat/vB)",
    )


# =============================================================================
# RBF ADVISOR (Sender Strategy)
# =============================================================================

def evaluate_rbf(
    original_fee_sats: int,
    original_fee_rate: float,
    original_vsize: float,
    target_fee_rate: float,
) -> RBFAdvice:
    """Evaluate whether a SENDER tx needs RBF and calculate replacement fee.

    BIP-125 Rules enforced:
    1. Rate rule: new_rate >= max(target, original + MinRelayTxFee)
    2. Absolute fee rule (Rule 3): new_fee_sats > original_fee_sats

    Args:
        original_fee_sats: Original transaction fee in satoshis.
        original_fee_rate: Original transaction fee rate (sat/vB).
        original_vsize: Original transaction virtual size (vBytes).
        target_fee_rate: Target fee rate from evaluate_market_rules() (sat/vB).

    Returns:
        RBFAdvice with stuck status and replacement fee calculation.
    """
    # Stuck detection: original rate below target
    is_stuck = original_fee_rate < target_fee_rate

    # Rate rule: max(target, original + minrelaytxfee)
    # This ensures the replacement pays for its own bandwidth (BIP-125 relay rule)
    new_rate = max(target_fee_rate, original_fee_rate + MIN_RELAY_FEE_RATE)

    # Floor: never recommend below minrelaytxfee
    new_rate = max(new_rate, MIN_RELAY_FEE_RATE)

    # Fee calculation: ceil to guarantee inclusion
    new_fee_sats = math.ceil(new_rate * original_vsize)

    # BIP-125 Rule 3 safety guard:
    # The absolute fee of the replacement MUST be strictly greater than the original.
    # This catches edge cases where rate * vsize could round down to <= original.
    new_fee_sats = max(new_fee_sats, original_fee_sats + 1)

    return RBFAdvice(
        is_stuck=is_stuck,
        original_fee_rate=original_fee_rate,
        original_fee_sats=original_fee_sats,
        target_fee_rate=new_rate,
        target_fee_sats=new_fee_sats,
    )


# =============================================================================
# CPFP ADVISOR (Receiver Strategy)
# =============================================================================

def evaluate_cpfp(
    parent_fee_sats: int,
    parent_vsize: float,
    target_fee_rate: float,
    child_vsize: float = ESTIMATED_CHILD_VSIZE,
) -> CPFPAdvice:
    """Evaluate whether a RECEIVER tx needs CPFP and calculate child fee.

    Package relay: miners evaluate (parent + child) as a unit.
    PackageFeeRate = (ParentFee + ChildFee) / (ParentVSize + ChildVSize)

    Args:
        parent_fee_sats: Parent transaction fee in satoshis.
        parent_vsize: Parent transaction virtual size (vBytes).
        target_fee_rate: Target fee rate from evaluate_market_rules() (sat/vB).
        child_vsize: Estimated child tx virtual size (default: 141 vB for P2WPKH).

    Returns:
        CPFPAdvice with stuck status and child fee calculation.
    """
    # Parent fee rate
    parent_fee_rate = parent_fee_sats / parent_vsize if parent_vsize > 0 else 0.0

    # Stuck detection: parent rate below target
    is_stuck = parent_fee_rate < target_fee_rate

    # Package fee calculation:
    # ChildFee = ceil(TargetRate × (ParentVSize + ChildVSize)) - ParentFee
    package_vsize = parent_vsize + child_vsize
    child_fee_sats = math.ceil(target_fee_rate * package_vsize) - parent_fee_sats

    # Floor: child tx must pay at least minrelaytxfee for its own relay
    min_child_fee = math.ceil(MIN_RELAY_FEE_RATE * child_vsize)
    child_fee_sats = max(child_fee_sats, min_child_fee)

    # Resulting package fee rate
    package_fee_rate = (parent_fee_sats + child_fee_sats) / package_vsize

    return CPFPAdvice(
        is_stuck=is_stuck,
        parent_fee_rate=parent_fee_rate,
        parent_fee_sats=parent_fee_sats,
        child_fee_sats=child_fee_sats,
        package_fee_rate=package_fee_rate,
    )
