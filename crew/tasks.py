# ============================================================
# GEM Protocol — CrewAI Task Definitions
# ============================================================
"""
Task definitions for each agent in the GEM Protocol crew.
Tasks are composed into a Crew pipeline in crew_manager.py.
"""
from __future__ import annotations

from crewai import Task, Agent


def create_macro_analysis_task(agent: Agent, macro_data: dict) -> Task:
    return Task(
        description=f"""Analyse the following macro indicators and provide a risk assessment:

## Current Macro Data
- VIX: {macro_data.get('vix', 'N/A')}
- USD/KRW: {macro_data.get('usd_krw', 'N/A')}
- S&P500 Daily Change: {macro_data.get('sp500_daily_chg_pct', 'N/A')}%
- NASDAQ Daily Change: {macro_data.get('nasdaq_daily_chg_pct', 'N/A')}%
- Fed Funds Rate: {macro_data.get('fed_funds_rate', 'N/A')}

## Required Output
1. Overall market regime (Risk-On / Risk-Off / Neutral)
2. Whether leverage should be blocked (VIX >= 30)
3. Whether US stock purchases should be blocked (USD/KRW >= 1400)  
4. Black swan alert if applicable (VIX >= 50 or S&P -7%)
5. Recommended position sizing adjustment (0.5x / 1.0x / 1.5x)

Respond in Korean (한국어). Be concise and actionable.""",
        expected_output="Structured macro risk assessment with regime classification and recommended actions",
        agent=agent,
    )


def create_tether_analysis_task(agent: Agent, tether_data: dict) -> Task:
    return Task(
        description=f"""Evaluate the USDT kimchi premium for arbitrage opportunity:

## Market Data
- USDT Price (Bithumb/KRW): ₩{tether_data.get('price_krw', 'N/A')}
- USDT Price (글로벌/USD): ${tether_data.get('price_usd', 'N/A')}
- Raw Kimchi Premium: {tether_data.get('raw_premium_pct', 'N/A')}%
- Net Premium (after fees): {tether_data.get('net_premium_pct', 'N/A')}%
- Current USD/KRW: {tether_data.get('usd_krw', 'N/A')}

## Fee Structure
- Bithumb fee: 0.25%
- Withdrawal fee: 1 USDT, Slippage: ~0.15%

## Required Output
1. Recommendation: SELL / BUY / HOLD
2. Net profit estimate (in %)
3. Risk factors to consider
4. Optimal execution timing suggestion

Respond in Korean (한국어).""",
        expected_output="Tether arbitrage recommendation with profit/risk analysis",
        agent=agent,
    )


def create_stock_screening_task(agent: Agent, candidates: list[dict]) -> Task:
    candidate_str = "\n".join(
        f"- {c.get('symbol')}: PE={c.get('forward_pe')}, PEG={c.get('peg_ratio')}, "
        f"FCF={c.get('free_cash_flow')}, D/E={c.get('debt_to_equity')}, RSI={c.get('rsi_14')}"
        for c in candidates[:20]
    )

    return Task(
        description=f"""Screen the following stock candidates against our quantitative filters:

## Filters
- Forward PE <= 15
- PEG Ratio <= 1.5  
- Free Cash Flow > 0 (positive)
- Debt/Equity < 200%

## Candidates
{candidate_str or "No candidates provided"}

## Required Output
1. PASS/FAIL for each candidate with reasoning
2. Ranked list of passing candidates by risk-adjusted potential
3. Any red flags or concerns
4. Suggested initial position sizes (1-5% of capital)

Respond in Korean (한국어).""",
        expected_output="Ranked stock screening results with pass/fail analysis",
        agent=agent,
    )


def create_split_strategy_task(agent: Agent, positions: list[dict], signals: list[dict]) -> Task:
    pos_str = "\n".join(
        f"- {p.get('symbol')}: avg={p.get('avg_price')}, cur={p.get('current_price')}, "
        f"pnl={p.get('pnl_pct')}%, splits={p.get('split_count')}"
        for p in positions[:20]
    )
    sig_str = "\n".join(
        f"- {s.get('symbol')}: {s.get('action')} — {s.get('reason')}"
        for s in signals
    )

    return Task(
        description=f"""Optimize split buy/sell strategy for current positions:

## Current Positions
{pos_str or "No positions"}

## Active Signals
{sig_str or "No active signals"}

## Rules
- Initial entry: RSI(14) < 30, capital 1-5%
- Split buy #2: at -5% from avg price
- Split buy #3: at -10% from avg price  
- Take profit: +3~5% from avg price → immediate sell
- Stop loss: -20% → forced exit
- Max 3 splits per position

## Required Output
1. Prioritised action list (what to do NOW)
2. Upcoming trigger prices for each position
3. Position sizing recommendations
4. Risk warnings for any position near stop-loss

Respond in Korean (한국어).""",
        expected_output="Detailed split buy/sell execution plan with trigger prices",
        agent=agent,
    )


def create_rebalance_task(agent: Agent, portfolio: dict, triggers: list[str]) -> Task:
    alloc_str = "\n".join(
        f"- {sym}: current={info.get('current_weight', 0):.1f}%, target={info.get('target_weight', 0):.1f}%"
        for sym, info in portfolio.items()
    )

    return Task(
        description=f"""Evaluate portfolio rebalancing needs:

## Current Allocation vs Targets
{alloc_str or "No allocation data"}

## Active Triggers
{chr(10).join(f'- {t}' for t in triggers) if triggers else "No active triggers"}

## Rules
- Rebalance if any weight deviates by ±5%p
- Consider weekly RSI (overbought >70, oversold <30)
- Tax impact: 22% capital gains on US stock sales
- Prefer tax-loss harvesting when possible

## Required Output
1. Specific rebalance trades (BUY/SELL with amounts)
2. Tax impact estimate
3. Priority order of trades
4. Whether to execute immediately or wait

Respond in Korean (한국어).""",
        expected_output="Specific rebalancing trade recommendations with tax analysis",
        agent=agent,
    )


def create_daily_report_task(
    agent: Agent,
    macro_summary: str,
    engine_summaries: dict,
    risk_state: dict,
) -> Task:
    return Task(
        description=f"""Create the daily GEM Protocol report consolidating all systems:

## Macro Assessment
{macro_summary}

## Engine 1 (Tether) Summary
{engine_summaries.get('tether', 'No data')}

## Engine 2 (Magic Split) Summary
{engine_summaries.get('magic_split', 'No data')}

## Engine 3 (Warehouse) Summary
{engine_summaries.get('warehouse', 'No data')}

## Risk State
- Circuit Breaker: {'ACTIVE' if risk_state.get('circuit_breaker_active') else 'Normal'}
- Black Swan: {'ACTIVE' if risk_state.get('black_swan_active') else 'Normal'}
- Daily PnL: {risk_state.get('daily_pnl_pct', 0):.2f}%

## Required Output Format
Create a structured report with:
1. 📊 시장 상황 요약 (1-2 sentences)
2. 🔴 긴급 조치 사항 (if any)
3. 🟢 각 엔진별 status & 추천 액션
4. 📈 오늘의 핵심 수치
5. 🎯 내일 주시할 포인트

Keep it under 500 words. Use Korean (한국어).""",
        expected_output="Comprehensive daily portfolio report in Korean",
        agent=agent,
    )
