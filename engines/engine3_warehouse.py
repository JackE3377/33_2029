# ============================================================
# GEM Protocol — Engine 3: Warehouse (Dynamic Rebalancing)
# ============================================================
"""
목적: LAA/올웨더 기반 장기 코어 자산 방어
  - 목표 비중: SPY/QQQ/TLT/IEF/GLD/SHY (Settings에서 정의)
  - 리밸런싱 트리거 조건:
      (1) 비중 ±5%p 이탈
      (2) 주간 RSI 70 초과 / 30 미만
      (3) 나스닥 일일 -3% 이상 폭락
  - 세금 효율화: 양도세(22%) 감안 세후 수익률 기반 판단
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from engines.base import BaseEngine
from core.models import (
    EngineType, OrderSide, TradeLog, TradeStatus, get_session,
)
from services.data_fetcher import DataFetcher, StockQuote


US_CAPITAL_GAINS_TAX = 0.22  # 미국주식 양도세 22%


@dataclass
class RebalanceAction:
    symbol: str
    current_weight: float
    target_weight: float
    deviation: float
    action: str  # "buy", "sell", "hold"
    reason: str
    pretax_pnl_pct: float = 0.0
    posttax_pnl_pct: float = 0.0


class WarehouseEngine(BaseEngine):
    """Engine 3: Long-term dynamic portfolio rebalancing."""

    def __init__(self):
        super().__init__(EngineType.ENGINE3_WAREHOUSE)

    def run_cycle(self) -> dict:
        """
        1) Fetch current prices for all warehouse assets
        2) Calculate current weights
        3) Check rebalance triggers
        4) Generate rebalance actions
        """
        macro = DataFetcher.get_macro()
        target_alloc = self.settings.warehouse_allocations
        symbols = list(target_alloc.keys())

        # Fetch quotes
        quotes: dict[str, StockQuote] = {}
        for sym in symbols:
            try:
                quotes[sym] = DataFetcher.get_stock(sym)
            except Exception as e:
                self.logger.warning(f"Failed to fetch {sym}: {e}")

        if not quotes:
            return {"engine": "warehouse", "status": "no_data"}

        # Check triggers
        trigger_reasons = self._check_triggers(macro, quotes)
        should_rebalance = len(trigger_reasons) > 0

        # Calculate current weights (assuming equal dollar investment initially)
        current_weights = self._calculate_weights(quotes)
        actions = self._generate_actions(current_weights, target_alloc, trigger_reasons)

        # Record trades for non-hold actions
        for action in actions:
            if action.action != "hold":
                self._record_trade(action, quotes.get(action.symbol))

        summary = {
            "engine": "warehouse",
            "should_rebalance": should_rebalance,
            "trigger_reasons": trigger_reasons,
            "actions": [
                {
                    "symbol": a.symbol,
                    "current": f"{a.current_weight:.1f}%",
                    "target": f"{a.target_weight:.1f}%",
                    "deviation": f"{a.deviation:+.1f}%p",
                    "action": a.action,
                    "reason": a.reason,
                }
                for a in actions
            ],
            "nasdaq_chg": macro.nasdaq_daily_chg_pct,
        }

        self.logger.info(
            f"Warehouse cycle: rebalance={'YES' if should_rebalance else 'NO'}, "
            f"triggers={len(trigger_reasons)}, actions={sum(1 for a in actions if a.action != 'hold')}"
        )

        return summary

    def _check_triggers(self, macro, quotes: dict[str, StockQuote]) -> list[str]:
        """Check all rebalance trigger conditions."""
        triggers = []

        # Trigger 1: NASDAQ daily crash >= -3%
        if macro.nasdaq_daily_chg_pct <= self.settings.nasdaq_crash_pct:
            triggers.append(
                f"NASDAQ crash: {macro.nasdaq_daily_chg_pct:.1f}% (threshold: {self.settings.nasdaq_crash_pct}%)"
            )

        # Trigger 2: Weekly RSI extremes
        for sym, q in quotes.items():
            if q.weekly_rsi is not None:
                if q.weekly_rsi >= self.settings.weekly_rsi_overbought:
                    triggers.append(f"{sym} weekly RSI {q.weekly_rsi:.0f} >= {self.settings.weekly_rsi_overbought} (overbought)")
                elif q.weekly_rsi <= self.settings.weekly_rsi_oversold:
                    triggers.append(f"{sym} weekly RSI {q.weekly_rsi:.0f} <= {self.settings.weekly_rsi_oversold} (oversold)")

        return triggers

    def _calculate_weights(self, quotes: dict[str, StockQuote]) -> dict[str, float]:
        """
        Calculate current portfolio weights.
        NOTE: In production, this should use actual position data from brokerage API.
        Skeleton uses equal-weight assumption for demonstration.
        """
        # TODO: Replace with actual portfolio position data from KIS API
        total_symbols = len(quotes)
        if total_symbols == 0:
            return {}

        # Placeholder: equal weight distribution
        # In production: weight = (qty × price) / total_portfolio_value
        return {sym: 100.0 / total_symbols for sym in quotes}

    def _generate_actions(
        self,
        current: dict[str, float],
        target: dict[str, float],
        triggers: list[str],
    ) -> list[RebalanceAction]:
        """Generate rebalance actions based on weight deviations."""
        actions = []

        for sym, target_pct in target.items():
            target_weight = target_pct * 100  # Convert 0.25 → 25%
            current_weight = current.get(sym, 0.0)
            deviation = current_weight - target_weight

            # Check if deviation exceeds threshold OR if triggered by other conditions
            deviation_exceeded = abs(deviation) >= self.settings.rebalance_deviation_pct
            forced_by_trigger = len(triggers) > 0

            if deviation_exceeded or forced_by_trigger:
                if deviation > 0:
                    # Overweight → sell some
                    action = "sell"
                    reason = f"Overweight by {deviation:+.1f}%p"
                elif deviation < 0:
                    # Underweight → buy some
                    action = "buy"
                    reason = f"Underweight by {deviation:+.1f}%p"
                else:
                    action = "hold"
                    reason = "On target"

                if forced_by_trigger and not deviation_exceeded:
                    reason += f" (forced by trigger: {triggers[0]})"
            else:
                action = "hold"
                reason = f"Within tolerance ({deviation:+.1f}%p)"

            actions.append(RebalanceAction(
                symbol=sym,
                current_weight=current_weight,
                target_weight=target_weight,
                deviation=deviation,
                action=action,
                reason=reason,
            ))

        return actions

    def _record_trade(self, action: RebalanceAction, quote: Optional[StockQuote]):
        """Record rebalance trade to DB."""
        if quote is None:
            return

        session = get_session()
        try:
            trade = TradeLog(
                engine=self.engine_type,
                symbol=action.symbol,
                side=OrderSide.BUY if action.action == "buy" else OrderSide.SELL,
                quantity=0,  # TODO: Calculate from deviation × portfolio value
                price=quote.price,
                total_value=0,
                status=TradeStatus.SIMULATED if self.is_paper else TradeStatus.PENDING,
                reason=action.reason,
                is_paper=self.is_paper,
            )
            session.add(trade)
            session.commit()
        finally:
            session.close()
