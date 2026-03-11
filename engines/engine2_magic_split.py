# ============================================================
# GEM Protocol — Engine 2: Magic Split System (Short-Term Trading)
# ============================================================
"""
목적: 단기 분할 매수/매도 시스템
  - 타겟 발굴: Forward PE ≤ 15, PEG ≤ 1.5, FCF 흑자, D/E 안전
  - 진입: RSI(14) < 30 → 자본 1~5% 1차 진입
  - 분할 매수: -5%, -10% 추가 하락 시 기계적 2차/3차 진입
  - 익절: 평단가 +3~5% → 즉시 매도
  - 손절: -20% 이하 → 기계적 손절 (Circuit Breaker)

외부 연동: Magic Split CSV/Excel → 현재 포지션 파싱
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from engines.base import BaseEngine
from core.models import (
    EngineType, OrderSide, TradeLog, TradeStatus, get_session,
)
from services.data_fetcher import DataFetcher, StockQuote
from services.csv_parser import parse_magic_split_file, MagicSplitPosition
from services.llm_router import LLMRouter, TaskComplexity


@dataclass
class SplitSignal:
    symbol: str
    action: str  # "buy_initial", "buy_split_N", "sell_profit", "sell_stop", "hold", "watch"
    reason: str
    target_price: float = 0.0
    position_pct: float = 0.0  # % of total capital
    split_number: int = 0


class MagicSplitEngine(BaseEngine):
    """Engine 2: Short-term split-buy/sell system."""

    def __init__(self):
        super().__init__(EngineType.ENGINE2_MAGIC)
        self._llm = LLMRouter()

    def run_cycle(self) -> dict:
        """
        1) Parse Magic Split CSV for current positions
        2) Check macro filters (VIX, USD/KRW)
        3) For each position: evaluate split buy/sell signals
        4) Scan for new targets (fundamentals screening)
        5) Generate AI-enhanced advice via LLM
        """
        macro = DataFetcher.get_macro()
        positions = parse_magic_split_file()

        signals: list[SplitSignal] = []
        ai_advice = ""

        # Macro filter check
        macro_blocked = self._check_macro_block(macro.vix, macro.usd_krw)

        # Evaluate existing positions
        for pos in positions:
            quote = self._safe_get_stock(pos.symbol)
            if quote is None:
                continue
            signal = self._evaluate_position(pos, quote, macro_blocked)
            signals.append(signal)
            if signal.action != "hold":
                self._record_trade(signal, quote.price)

        # LLM-enhanced advice (if positions exist)
        if positions:
            ai_advice = self._get_ai_advice(positions, signals, macro)

        summary = {
            "engine": "magic_split",
            "positions_count": len(positions),
            "signals": [
                {"symbol": s.symbol, "action": s.action, "reason": s.reason}
                for s in signals
            ],
            "macro_blocked": macro_blocked,
            "ai_advice": ai_advice,
            "vix": macro.vix,
        }

        self.logger.info(
            f"MagicSplit cycle: {len(positions)} positions, "
            f"{sum(1 for s in signals if s.action != 'hold')} active signals"
        )

        return summary

    def _check_macro_block(self, vix: float, usd_krw: float) -> bool:
        """Check if macro conditions block trading."""
        if vix >= self.settings.vix_leverage_block:
            self.logger.warning(f"VIX={vix:.1f} >= {self.settings.vix_leverage_block} → Leverage BLOCKED")
            return True
        if usd_krw >= self.settings.usdkrw_block_threshold:
            self.logger.warning(f"USD/KRW={usd_krw:.0f} >= {self.settings.usdkrw_block_threshold} → US stock BUY BLOCKED")
            return True
        return False

    def _evaluate_position(
        self,
        pos: MagicSplitPosition,
        quote: StockQuote,
        macro_blocked: bool,
    ) -> SplitSignal:
        """Evaluate a single position for buy/sell signals."""
        pnl_pct = ((quote.price - pos.avg_price) / pos.avg_price * 100) if pos.avg_price > 0 else 0

        # --- Stop-Loss ---
        if pnl_pct <= self.settings.stop_loss_pct:
            return SplitSignal(
                symbol=pos.symbol,
                action="sell_stop",
                reason=f"STOP-LOSS triggered: PnL {pnl_pct:.1f}% <= {self.settings.stop_loss_pct}%",
                target_price=quote.price,
            )

        # --- Take-Profit ---
        if pnl_pct >= self.settings.take_profit_pct:
            return SplitSignal(
                symbol=pos.symbol,
                action="sell_profit",
                reason=f"TAKE-PROFIT: PnL {pnl_pct:.1f}% >= +{self.settings.take_profit_pct}%",
                target_price=quote.price,
            )

        # --- Split Buy (if not macro-blocked) ---
        if not macro_blocked and pos.split_count < self.settings.max_split_count:
            for i, drop_pct in enumerate(self.settings.split_buy_drop_pcts):
                if pnl_pct <= drop_pct and pos.split_count == i + 1:
                    return SplitSignal(
                        symbol=pos.symbol,
                        action=f"buy_split_{i + 2}",
                        reason=f"Split buy #{i+2}: PnL {pnl_pct:.1f}% <= {drop_pct}%",
                        target_price=quote.price,
                        position_pct=self.settings.initial_position_pct,
                        split_number=i + 2,
                    )

        # --- Initial Entry (new target candidate) ---
        if (
            not macro_blocked
            and pos.split_count == 0
            and quote.rsi_14 is not None
            and quote.rsi_14 < self.settings.rsi_entry
        ):
            if self._passes_fundamental_screen(quote):
                return SplitSignal(
                    symbol=pos.symbol,
                    action="buy_initial",
                    reason=f"Initial entry: RSI={quote.rsi_14:.1f} < {self.settings.rsi_entry}, fundamentals pass",
                    target_price=quote.price,
                    position_pct=self.settings.initial_position_pct,
                    split_number=1,
                )

        return SplitSignal(
            symbol=pos.symbol,
            action="hold",
            reason=f"Hold: PnL={pnl_pct:.1f}%, RSI={quote.rsi_14}",
        )

    def _passes_fundamental_screen(self, quote: StockQuote) -> bool:
        """Check Forward PE, PEG, FCF, D/E filters."""
        checks = []
        if quote.forward_pe is not None:
            checks.append(quote.forward_pe <= self.settings.forward_pe_max)
        if quote.peg_ratio is not None:
            checks.append(quote.peg_ratio <= self.settings.peg_max)
        if quote.free_cash_flow is not None:
            checks.append(quote.free_cash_flow > 0)
        if quote.debt_to_equity is not None:
            checks.append(quote.debt_to_equity < 200)  # D/E < 200% as safe zone

        # If any data missing, pass with warning
        if not checks:
            self.logger.warning(f"No fundamental data for {quote.symbol} — allowing entry with caution")
            return True

        return all(checks)

    def _get_ai_advice(self, positions, signals, macro) -> str:
        """Use LLM to generate portfolio-aware investment advice."""
        pos_summary = "\n".join(
            f"- {p.symbol}: qty={p.quantity}, avg={p.avg_price}, "
            f"cur={p.current_price}, pnl={p.pnl_pct:.1f}%, splits={p.split_count}"
            for p in positions[:20]  # Limit to avoid token overflow
        )
        signal_summary = "\n".join(
            f"- {s.symbol}: {s.action} — {s.reason}"
            for s in signals if s.action != "hold"
        )

        prompt = f"""You are a quant analyst. Given the current portfolio and signals, 
provide concise actionable advice in Korean (한국어).

## Macro
- VIX: {macro.vix}, USD/KRW: {macro.usd_krw}

## Current Positions
{pos_summary}

## Active Signals
{signal_summary or "None"}

## Instructions
1. Prioritise risk management
2. Flag any positions that need immediate attention
3. Suggest optimal split-buy timing if applicable
4. Keep response under 300 words
"""

        try:
            return self._llm.query(prompt, TaskComplexity.HEAVY, task_type="magic_split_advice")
        except Exception as e:
            self.logger.error(f"AI advice generation failed: {e}")
            return ""

    def _record_trade(self, signal: SplitSignal, price: float):
        """Record trade signal to DB."""
        session = get_session()
        try:
            side = OrderSide.BUY if "buy" in signal.action else OrderSide.SELL
            trade = TradeLog(
                engine=self.engine_type,
                symbol=signal.symbol,
                side=side,
                quantity=0,  # TODO: Calculate from capital × position_pct
                price=price,
                total_value=0,
                status=TradeStatus.SIMULATED if self.is_paper else TradeStatus.PENDING,
                reason=signal.reason,
                is_paper=self.is_paper,
            )
            session.add(trade)
            session.commit()
        finally:
            session.close()

    def _safe_get_stock(self, symbol: str) -> Optional[StockQuote]:
        try:
            return DataFetcher.get_stock(symbol)
        except Exception as e:
            self.logger.warning(f"Failed to fetch {symbol}: {e}")
            return None
