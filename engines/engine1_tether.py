# ============================================================
# GEM Protocol — Engine 1: Tether System (Kimchi Premium Bot)
# ============================================================
"""
목적: USDT 김치 프리미엄 모니터링 및 자동 매매
  - 프리미엄 +3~5% → USDT 매도 → KRW 확보
  - 역프리미엄 (-1% 이하) → USDT 매수 (홀딩)
  - 수수료 + 슬리피지 감안한 실질 수익률 기반 판단

거래소: Bithumb (KRW) — 공개 시세 API 사용
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from engines.base import BaseEngine
from core.models import (
    EngineType, OrderSide, TradeLog, TradeStatus, get_session,
)
from services.data_fetcher import DataFetcher

# Fee constants (빗썸 기준, 보수적 추정)
BITHUMB_FEE_PCT = 0.25   # 빗썸 기본 수수료 (쿠폰 미적용)
WITHDRAWAL_FEE_USDT = 1.0
SLIPPAGE_PCT = 0.15


@dataclass
class TetherSignal:
    raw_premium_pct: float
    net_premium_pct: float  # 수수료·슬리피지 차감 후 실질
    action: str  # "sell", "buy", "hold"
    reason: str


class TetherEngine(BaseEngine):
    """Engine 1: Kimchi premium arbitrage for USDT."""

    def __init__(self):
        super().__init__(EngineType.ENGINE1_TETHER)

    def run_cycle(self) -> dict:
        """
        1) Fetch macro (USD/KRW) + USDT prices
        2) Calculate net kimchi premium (after fees/slippage)
        3) Generate signal
        4) Execute (or simulate) trade
        """
        # Step 1: Get data
        macro = DataFetcher.get_macro()
        crypto = DataFetcher.get_usdt_premium(macro.usd_krw)

        # Step 2: Calculate net premium
        signal = self._evaluate(crypto.kimchi_premium_pct)

        # Step 3: Log and (optionally) execute
        summary = {
            "engine": "tether",
            "usd_krw": macro.usd_krw,
            "raw_premium_pct": crypto.kimchi_premium_pct,
            "net_premium_pct": signal.net_premium_pct,
            "action": signal.action,
            "reason": signal.reason,
        }

        if signal.action != "hold":
            self._record_trade(signal, crypto.price_krw)

        self.logger.info(
            f"Tether cycle: premium={crypto.kimchi_premium_pct:.2f}%, "
            f"net={signal.net_premium_pct:.2f}%, action={signal.action}"
        )

        return summary

    def _evaluate(self, raw_premium_pct: float) -> TetherSignal:
        """Evaluate whether to sell, buy, or hold based on net premium."""
        # Deduct fees from both sides + slippage
        total_fee_pct = BITHUMB_FEE_PCT + SLIPPAGE_PCT
        net_premium = raw_premium_pct - total_fee_pct

        sell_threshold = self.settings.kimchi_premium_sell_pct
        buy_threshold = self.settings.kimchi_premium_buy_pct

        if net_premium >= sell_threshold:
            return TetherSignal(
                raw_premium_pct=raw_premium_pct,
                net_premium_pct=net_premium,
                action="sell",
                reason=f"Net premium {net_premium:.2f}% >= {sell_threshold}% threshold → SELL USDT on Bithumb",
            )
        elif raw_premium_pct <= buy_threshold:
            return TetherSignal(
                raw_premium_pct=raw_premium_pct,
                net_premium_pct=net_premium,
                action="buy",
                reason=f"Reverse premium {raw_premium_pct:.2f}% <= {buy_threshold}% → BUY USDT",
            )
        else:
            return TetherSignal(
                raw_premium_pct=raw_premium_pct,
                net_premium_pct=net_premium,
                action="hold",
                reason=f"Premium {net_premium:.2f}% within range → HOLD",
            )

    def _record_trade(self, signal: TetherSignal, price_krw: float):
        """Record trade to DB (paper or live)."""
        session = get_session()
        try:
            trade = TradeLog(
                engine=self.engine_type,
                symbol="USDT",
                side=OrderSide.SELL if signal.action == "sell" else OrderSide.BUY,
                quantity=0,  # TODO: Calculate from available balance via exchange API
                price=price_krw,
                total_value=0,
                status=TradeStatus.SIMULATED if self.is_paper else TradeStatus.PENDING,
                reason=signal.reason,
                is_paper=self.is_paper,
            )

            if not self.is_paper:
                # TODO: Execute actual exchange API order
                # order_result = exchange_client.place_order(...)
                # trade.quantity = order_result.filled_qty
                # trade.total_value = order_result.total
                # trade.status = TradeStatus.FILLED
                self.logger.info("LIVE mode: Exchange order would be placed here")
            else:
                self.logger.info(f"PAPER mode: Simulated {signal.action} USDT @ ₩{price_krw:,.0f}")

            session.add(trade)
            session.commit()
        finally:
            session.close()
