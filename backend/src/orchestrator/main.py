"""
AI Orchestrator Service – Safe-Guarded AI Pattern

Hybrid Architecture:
├── Logic Layer (Python): Deterministic decisions, guaranteed correct
└── Narrative Layer (AI): Human-readable commentary, non-critical

This pattern ensures:
- Critical business logic (WAIT/BROADCAST) NEVER fails
- LLM generates explanatory text only
- Full graceful degradation if AI is unavailable
"""

import asyncio
import math
import os
from typing import TypedDict

from loguru import logger
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from src.config import settings
from src.orchestrator.schemas import AgentDecision, MempoolContext
from src.orchestrator.tools import get_market_context
from src.storage.agent_history import AgentDecisionRecord, AgentHistory


# =============================================================================
# CONFIGURATION
# =============================================================================

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
DECISION_INTERVAL = int(os.getenv("DECISION_INTERVAL", "60"))
AI_TIMEOUT = 30  # seconds to wait for AI commentary

# Fallback when AI is unavailable
FALLBACK_REASONING = "Market analysis unavailable."


# =============================================================================
# TYPED STRUCTURES
# =============================================================================

class MarketDecision(TypedDict):
    """Deterministic decision output from Python logic."""
    action: str
    recommended_fee: int
    confidence: float


# =============================================================================
# LAYER 1: DETERMINISTIC LOGIC (Critical Path)
# =============================================================================

def evaluate_market_rules(ctx: MempoolContext) -> MarketDecision:
    """Pure Python implementation of fee decision logic.
    
    This function is the CRITICAL PATH. It must never fail.
    All business rules are implemented here, not in the LLM.
    
    Rules:
    - If fee_premium_pct > 20: WAIT, recommend historical fee
    - If fee_premium_pct <= 20: BROADCAST, recommend current fee
    - Confidence scales with premium magnitude
    
    Args:
        ctx: Current market context from DuckDB.
        
    Returns:
        MarketDecision dict with action, recommended_fee, confidence.
    """
    premium = ctx.fee_premium_pct
    
    # Rule 1: Action based on fee premium threshold
    if premium > 20:
        action = "WAIT"
        recommended_fee = max(1, math.ceil(ctx.historical_median_fee))
    else:
        action = "BROADCAST"
        recommended_fee = max(1, math.ceil(ctx.current_median_fee))
    
    # Rule 2: Confidence based on premium magnitude
    abs_premium = abs(premium)
    if abs_premium > 30:
        confidence = 0.9
    elif abs_premium > 10:
        confidence = 0.7
    else:
        confidence = 0.5
    
    return MarketDecision(
        action=action,
        recommended_fee=recommended_fee,
        confidence=confidence,
    )


# =============================================================================
# LAYER 2: AI NARRATIVE (Non-Critical)
# =============================================================================

# System prompt for the "Market Commentator" role
COMMENTATOR_PROMPT = """You are a Bitcoin Market Commentator.
You receive market data and a decision that has ALREADY been made.
Your job is to explain WHY the decision fits the data.

RULES:
- Output a SINGLE SENTENCE (max 30 words).
- Be concise and professional.
- Do NOT suggest a different action.
- Do NOT output JSON, markdown, or formatting.
- Just plain text.

Example output:
"With fees 45% above historical average, waiting protects against overpaying during congestion."

Now explain the decision below in one sentence."""


def create_commentator_agent() -> Agent[None, str]:
    """Create an AI agent that generates narrative commentary.
    
    This agent outputs PLAIN TEXT, not structured data.
    It cannot fail the critical path - if it errors, we use fallback text.
    
    Returns:
        Agent that produces a string explanation.
    """
    ollama_provider = OpenAIProvider(
        base_url=f"{OLLAMA_HOST}/v1",
        api_key="ollama",
    )
    
    model = OpenAIChatModel(
        OLLAMA_MODEL,
        provider=ollama_provider,
    )
    
    model_settings = ModelSettings(
        temperature=0.3,  # Slight creativity for natural language
    )
    
    agent: Agent[None, str] = Agent(
        model,
        output_type=str,
        system_prompt=COMMENTATOR_PROMPT,
        retries=2,  # Limited retries for commentary
        model_settings=model_settings,
    )
    
    return agent


def format_commentary_prompt(ctx: MempoolContext, decision: MarketDecision) -> str:
    """Format the prompt for the AI commentator.
    
    Provides both market data AND the decision made by Python.
    """
    return f"""MARKET DATA:
- Current Fee: {ctx.current_median_fee:.2f} sat/vB
- Historical Fee: {ctx.historical_median_fee:.2f} sat/vB  
- Premium: {ctx.fee_premium_pct:+.1f}%
- Traffic: {ctx.traffic_level}

DECISION MADE:
- Action: {decision['action']}
- Recommended Fee: {decision['recommended_fee']} sat/vB

Explain this decision in one sentence:"""


async def get_ai_reasoning(
    agent: Agent[None, str],
    ctx: MempoolContext,
    decision: MarketDecision,
) -> str:
    """Get AI-generated reasoning for the decision.
    
    This is NON-CRITICAL. If the AI fails, returns fallback text.
    The main loop will NOT crash if this fails.
    
    Args:
        agent: The commentator agent.
        ctx: Market context.
        decision: The deterministic decision already made.
        
    Returns:
        AI reasoning string, or fallback if error/timeout.
    """
    try:
        prompt = format_commentary_prompt(ctx, decision)
        result = await asyncio.wait_for(
            agent.run(prompt),
            timeout=AI_TIMEOUT,
        )
        # Clean up any extra whitespace or quotes
        reasoning = result.output.strip().strip('"').strip("'")
        return reasoning if reasoning else FALLBACK_REASONING
        
    except asyncio.TimeoutError:
        logger.warning(f"⏱️ AI commentary timed out after {AI_TIMEOUT}s")
        return FALLBACK_REASONING
        
    except Exception as e:
        logger.warning(f"⚠️ AI commentary failed: {type(e).__name__}: {e}")
        return FALLBACK_REASONING


# =============================================================================
# DECISION LOOP
# =============================================================================

async def decision_loop(agent: Agent[None, str]) -> None:
    """Main decision loop with Safe-Guarded AI pattern.
    
    Flow:
    1. Get market context (DB)
    2. Calculate decision (Python - CRITICAL)
    3. Get AI reasoning (LLM - NON-CRITICAL, with fallback)
    4. Merge into final AgentDecision
    5. Log result
    6. Persist decision to history (NON-CRITICAL)
    """
    # Initialize persistence layer
    history = AgentHistory(settings.agent_history_path)
    logger.info(f"📂 Agent History initialized at {settings.agent_history_path}")
    
    logger.info("🧠 Bitcoin Treasury Agent starting...")
    logger.info("🔒 SAFE-GUARDED AI MODE: Deterministic logic + AI commentary")
    logger.info(f"   OLLAMA_HOST: {OLLAMA_HOST}")
    logger.info(f"   OLLAMA_MODEL: {OLLAMA_MODEL}")
    logger.info(f"   DECISION_INTERVAL: {DECISION_INTERVAL}s")
    logger.info(f"   AI_TIMEOUT: {AI_TIMEOUT}s")
    
    while True:
        try:
            logger.info("─" * 50)
            
            # Step A: Get market context from DuckDB
            context = get_market_context()
            logger.info(
                f"📊 Market: fee={context.current_median_fee:.2f} sat/vB, "
                f"premium={context.fee_premium_pct:+.1f}%, "
                f"traffic={context.traffic_level}"
            )
            
            # Step B: Calculate decision using DETERMINISTIC logic (never fails)
            decision = evaluate_market_rules(context)
            logger.debug(f"   Python decision: {decision}")
            
            # Step C: Get AI reasoning (graceful degradation if fails)
            reasoning = await get_ai_reasoning(agent, context, decision)
            
            # Step D: Construct final AgentDecision
            final_decision = AgentDecision(
                action=decision["action"],
                recommended_fee=decision["recommended_fee"],
                confidence=decision["confidence"],
                reasoning=reasoning,
            )
            
            # Step E: Log structured decision
            logger.success(
                f"🎯 Decision: {final_decision.action} | "
                f"Fee: {final_decision.recommended_fee} sat/vB | "
                f"Confidence: {final_decision.confidence:.0%}"
            )
            logger.info(f"   Reasoning: {final_decision.reasoning}")
            
            # Step F: Persist decision to history (silent, non-critical)
            try:
                record = AgentDecisionRecord(
                    action=final_decision.action,
                    current_fee=round(context.current_median_fee),
                    recommended_fee=final_decision.recommended_fee,
                    ai_confidence=final_decision.confidence,
                    ai_reasoning=final_decision.reasoning,
                    model_version="neuro-symbolic-v1",
                )
                history.save_decision(record)
                logger.debug("💾 Decision persisted to history.")
            except Exception as e:
                logger.warning(f"⚠️ Failed to persist decision: {type(e).__name__}: {e}")
            
        except RuntimeError as e:
            logger.error(f"❌ Data error: {e}")
                
        except Exception as e:
            logger.error(f"❌ Unexpected error: {type(e).__name__}: {e}")
        
        await asyncio.sleep(DECISION_INTERVAL)


# =============================================================================
# ENTRY POINTS
# =============================================================================

async def main_async() -> None:
    """Async entry point."""
    agent = create_commentator_agent()
    await decision_loop(agent)


def main() -> None:
    """Entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
