# ============================================================
# GEM Protocol — CrewAI Agent Definitions
# ============================================================
"""
6 specialised AI agents forming the GEM Protocol crew:

1. Macro Sentinel     — Monitors VIX, USD/KRW, Fed policy
2. Tether Arbitrageur — Kimchi premium trading decisions
3. Quant Screener     — Stock fundamental screening
4. Split Strategist   — Split buy/sell timing & execution
5. Portfolio Guardian — Warehouse rebalancing & risk
6. Report Synthesiser — Consolidates all signals into actionable report
"""
from __future__ import annotations

from crewai import Agent

from core.config import get_settings


def _get_llm_config(model: str = "gemini-flash") -> dict:
    """Build LLM configuration for CrewAI agents."""
    settings = get_settings()

    if model.startswith("gemini"):
        return {
            "model": "gemini/gemini-2.0-flash",
            "api_key": settings.gemini_api_key,
        }
    else:
        return {
            "model": "gpt-4o",
            "api_key": settings.openai_api_key,
        }


# ---------- Agent Definitions ----------

def create_macro_sentinel() -> Agent:
    return Agent(
        role="Macro Sentinel",
        goal=(
            "Monitor global macro indicators (VIX, USD/KRW, Fed Funds Rate, "
            "S&P500, NASDAQ) and issue real-time risk assessments. "
            "Detect regime changes and black swan events."
        ),
        backstory=(
            "You are a seasoned macro strategist at a top hedge fund. "
            "You specialize in cross-asset correlation analysis and regime detection. "
            "Your alerts have saved the fund from multiple market crashes."
        ),
        verbose=True,
        allow_delegation=False,
        llm=_get_llm_config("gemini-flash"),
    )


def create_tether_arbitrageur() -> Agent:
    return Agent(
        role="Tether Arbitrageur",
        goal=(
            "Maximize KRW returns from USDT kimchi premium arbitrage. "
            "Account for exchange fees, withdrawal costs, and slippage. "
            "Only recommend trades when net profit exceeds 2%."
        ),
        backstory=(
            "You are a crypto arbitrage specialist who has been exploiting "
            "cross-exchange price discrepancies for years. You never trade "
            "emotionally and always factor in hidden costs."
        ),
        verbose=True,
        allow_delegation=False,
        llm=_get_llm_config("gemini-flash-lite"),
    )


def create_quant_screener() -> Agent:
    return Agent(
        role="Quant Screener",
        goal=(
            "Screen stocks using strict quantitative filters: "
            "Forward PE <= 15, PEG <= 1.5, positive FCF, D/E < 200%. "
            "Rank candidates by risk-adjusted expected return."
        ),
        backstory=(
            "You are a quantitative analyst trained in factor investing. "
            "You believe in systematic, emotion-free stock selection "
            "based on fundamental value metrics."
        ),
        verbose=True,
        allow_delegation=False,
        llm=_get_llm_config("gemini-flash"),
    )


def create_split_strategist() -> Agent:
    return Agent(
        role="Split Strategist",
        goal=(
            "Optimise split-buy/sell timing for Engine 2 positions. "
            "Determine optimal entry points using RSI, support levels, "
            "and volume analysis. Enforce strict position sizing and stop-losses."
        ),
        backstory=(
            "You are a tactical trader who has perfected the art of dollar-cost "
            "averaging into high-conviction positions. You never exceed risk limits "
            "and always respect stop-losses at -20%."
        ),
        verbose=True,
        allow_delegation=False,
        llm=_get_llm_config("gpt"),
    )


def create_portfolio_guardian() -> Agent:
    return Agent(
        role="Portfolio Guardian",
        goal=(
            "Maintain optimal long-term asset allocation based on LAA/All-Weather "
            "principles. Monitor weight deviations, weekly RSI extremes, and market "
            "crashes. Execute tax-efficient rebalancing."
        ),
        backstory=(
            "You are a portfolio manager who manages institutional endowment funds. "
            "You prioritise capital preservation while maintaining growth exposure. "
            "You always consider tax implications (22% capital gains) before selling."
        ),
        verbose=True,
        allow_delegation=False,
        llm=_get_llm_config("gemini-flash"),
    )


def create_report_synthesiser() -> Agent:
    return Agent(
        role="Report Synthesiser",
        goal=(
            "Consolidate all engine outputs, risk assessments, and AI analyses "
            "into a concise, actionable daily report in Korean (한국어). "
            "Highlight urgent items and rank actions by priority."
        ),
        backstory=(
            "You are the chief investment officer who reviews all trading desks. "
            "You excel at distilling complex information into clear, actionable "
            "recommendations. Your reports are legendary for their clarity."
        ),
        verbose=True,
        allow_delegation=True,
        llm=_get_llm_config("gpt"),
    )
