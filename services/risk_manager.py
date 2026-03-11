# ============================================================
# GEM Protocol — Risk Management & Circuit Breaker
# ============================================================
"""
Global risk management layer that sits above all engines:
  - Daily max loss circuit breaker (전체 자산 -2% → 전 엔진 정지)
  - Single position concentration limit (10%)
  - Black Swan protocol (VIX 50+ or S&P -7% → 전 매수 차단, 현금화)
  - Cross-engine correlation monitoring
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from core.config import get_settings
from core.logger import get_logger
from core.models import PerformanceDaily, get_session

logger = get_logger("risk_manager")


@dataclass
class RiskState:
    """Current risk state of the system."""
    circuit_breaker_active: bool = False
    black_swan_active: bool = False
    daily_pnl_pct: float = 0.0
    vix: float = 0.0
    sp500_chg_pct: float = 0.0
    blocked_reasons: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RiskManager:
    """
    Global risk gate — checked BEFORE every engine cycle.
    
    Usage:
        risk = RiskManager()
        state = risk.evaluate(macro_data, portfolio_value, daily_pnl)
        if state.circuit_breaker_active:
            engine.pause()  # All engines stop
    """

    def __init__(self):
        self.settings = get_settings()
        self._state = RiskState()

    @property
    def state(self) -> RiskState:
        return self._state

    def evaluate(
        self,
        vix: float,
        sp500_daily_chg_pct: float,
        daily_pnl_pct: float,
        total_portfolio_value: float = 0,
        position_values: Optional[dict[str, float]] = None,
    ) -> RiskState:
        """
        Run all risk checks and update state.
        Returns the current RiskState.
        """
        reasons = []

        # --- Circuit Breaker: Daily Max Loss ---
        if daily_pnl_pct <= -self.settings.daily_max_loss_pct:
            reasons.append(
                f"CIRCUIT BREAKER: Daily loss {daily_pnl_pct:.1f}% "
                f"exceeds -{self.settings.daily_max_loss_pct}% limit"
            )

        # --- Black Swan Protocol ---
        if vix >= self.settings.circuit_breaker_vix:
            reasons.append(
                f"BLACK SWAN: VIX={vix:.1f} >= {self.settings.circuit_breaker_vix}"
            )

        if sp500_daily_chg_pct <= -self.settings.black_swan_sp500_drop_pct:
            reasons.append(
                f"BLACK SWAN: S&P500 crash {sp500_daily_chg_pct:.1f}% "
                f"<= -{self.settings.black_swan_sp500_drop_pct}%"
            )

        # --- Position Concentration Check ---
        if position_values and total_portfolio_value > 0:
            for symbol, value in position_values.items():
                weight = (value / total_portfolio_value) * 100
                if weight > self.settings.single_position_max_pct:
                    reasons.append(
                        f"CONCENTRATION: {symbol} = {weight:.1f}% "
                        f"> {self.settings.single_position_max_pct}% limit"
                    )

        # Update state
        self._state = RiskState(
            circuit_breaker_active=len(reasons) > 0,
            black_swan_active=any("BLACK SWAN" in r for r in reasons),
            daily_pnl_pct=daily_pnl_pct,
            vix=vix,
            sp500_chg_pct=sp500_daily_chg_pct,
            blocked_reasons=reasons,
        )

        if reasons:
            for reason in reasons:
                logger.critical(reason)

        return self._state

    def is_buy_allowed(self) -> bool:
        """Check if new buy orders are allowed."""
        return not self._state.circuit_breaker_active

    def is_leverage_allowed(self, vix: float) -> bool:
        """Check if leveraged positions are allowed."""
        return vix < self.settings.vix_leverage_block

    def record_daily_performance(
        self,
        total_asset_krw: float,
        daily_return_pct: float,
        cumulative_return_pct: float,
        max_drawdown_pct: float,
        sharpe_ratio: Optional[float] = None,
        engine1_pnl: float = 0.0,
        engine2_pnl: float = 0.0,
        engine3_pnl: float = 0.0,
    ):
        """Save daily performance snapshot to DB."""
        session = get_session()
        try:
            perf = PerformanceDaily(
                date=datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0),
                total_asset_krw=total_asset_krw,
                daily_return_pct=daily_return_pct,
                cumulative_return_pct=cumulative_return_pct,
                max_drawdown_pct=max_drawdown_pct,
                sharpe_ratio=sharpe_ratio,
                engine1_pnl=engine1_pnl,
                engine2_pnl=engine2_pnl,
                engine3_pnl=engine3_pnl,
            )
            session.merge(perf)  # Upsert by date
            session.commit()
        except Exception as e:
            logger.error(f"Failed to record performance: {e}")
            session.rollback()
        finally:
            session.close()
