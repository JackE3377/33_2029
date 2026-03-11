# ============================================================
# GEM Protocol — Scheduler (Engine Orchestrator)
# ============================================================
"""
APScheduler-based orchestrator that runs each engine
at its configured interval, with risk gate checks.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.config import get_settings
from core.logger import get_logger
from core.models import AlertPriority, EngineType
from engines.engine1_tether import TetherEngine
from engines.engine2_magic_split import MagicSplitEngine
from engines.engine3_warehouse import WarehouseEngine
from services.alert_manager import Alert, AlertManager
from services.data_fetcher import DataFetcher
from services.risk_manager import RiskManager

logger = get_logger("scheduler")


class GEMScheduler:
    """
    Central scheduler that orchestrates all engines.
    
    Lifecycle:
      1. Pre-check: Fetch macro → Risk gate
      2. Execute: Run each engine cycle
      3. Post-check: Alerts, performance recording
    """

    def __init__(self):
        self.settings = get_settings()
        self.risk_manager = RiskManager()
        self.alert_manager = AlertManager()

        # Engines
        self.engine1 = TetherEngine()
        self.engine2 = MagicSplitEngine()
        self.engine3 = WarehouseEngine()

        # Scheduler
        self._scheduler = BackgroundScheduler(daemon=True)
        self._results: dict[str, dict] = {}
        self._lock = threading.Lock()

    @property
    def results(self) -> dict[str, dict]:
        with self._lock:
            return dict(self._results)

    @property
    def engine_statuses(self) -> dict:
        return {
            "engine1": {
                "is_running": self.engine1.status.is_running,
                "is_paused": self.engine1.status.is_paused,
                "last_run": str(self.engine1.status.last_run) if self.engine1.status.last_run else "",
                "last_error": self.engine1.status.last_error,
                "cycles": self.engine1.status.cycle_count,
            },
            "engine2": {
                "is_running": self.engine2.status.is_running,
                "is_paused": self.engine2.status.is_paused,
                "last_run": str(self.engine2.status.last_run) if self.engine2.status.last_run else "",
                "last_error": self.engine2.status.last_error,
                "cycles": self.engine2.status.cycle_count,
            },
            "engine3": {
                "is_running": self.engine3.status.is_running,
                "is_paused": self.engine3.status.is_paused,
                "last_run": str(self.engine3.status.last_run) if self.engine3.status.last_run else "",
                "last_error": self.engine3.status.last_error,
                "cycles": self.engine3.status.cycle_count,
            },
        }

    def start(self):
        """Start the scheduler with engine intervals."""
        logger.info("Starting GEM Scheduler...")

        self._scheduler.add_job(
            self._run_engine1,
            IntervalTrigger(seconds=self.settings.engine1_interval_sec),
            id="engine1",
            replace_existing=True,
        )
        self._scheduler.add_job(
            self._run_engine2,
            IntervalTrigger(seconds=self.settings.engine2_interval_sec),
            id="engine2",
            replace_existing=True,
        )
        self._scheduler.add_job(
            self._run_engine3,
            IntervalTrigger(seconds=self.settings.engine3_interval_sec),
            id="engine3",
            replace_existing=True,
        )

        self._scheduler.start()
        logger.info("GEM Scheduler started with all engines.")

    def stop(self):
        """Stop the scheduler."""
        self._scheduler.shutdown(wait=False)
        logger.info("GEM Scheduler stopped.")

    def run_all_once(self) -> dict:
        """Run all engines once (for manual trigger / testing)."""
        self._run_risk_gate()
        r1 = self._run_engine1()
        r2 = self._run_engine2()
        r3 = self._run_engine3()
        return {"engine1": r1, "engine2": r2, "engine3": r3}

    def _run_risk_gate(self) -> bool:
        """Fetch macro data and run risk evaluation. Returns True if blocked."""
        try:
            macro = DataFetcher.get_macro()
            state = self.risk_manager.evaluate(
                vix=macro.vix,
                sp500_daily_chg_pct=macro.sp500_daily_chg_pct,
                daily_pnl_pct=0,  # TODO: Calculate from today's trades
            )

            with self._lock:
                self._results["macro"] = {
                    "vix": macro.vix,
                    "usd_krw": macro.usd_krw,
                    "sp500_daily_chg_pct": macro.sp500_daily_chg_pct,
                    "nasdaq_daily_chg_pct": macro.nasdaq_daily_chg_pct,
                    "fed_funds_rate": macro.fed_funds_rate,
                }
                self._results["risk_state"] = {
                    "circuit_breaker_active": state.circuit_breaker_active,
                    "black_swan_active": state.black_swan_active,
                    "daily_pnl_pct": state.daily_pnl_pct,
                    "blocked_reasons": state.blocked_reasons,
                }

            # Send alerts if circuit breaker activated
            if state.circuit_breaker_active:
                self.alert_manager.send(Alert(
                    priority=AlertPriority.CRITICAL,
                    title="Circuit Breaker Activated",
                    message="\n".join(state.blocked_reasons),
                ))
                # Pause all engines
                self.engine1.pause()
                self.engine2.pause()
                self.engine3.pause()
                return True

            return False

        except Exception as e:
            logger.error(f"Risk gate error: {e}")
            return False

    def _run_engine1(self) -> dict:
        """Execute Engine 1 cycle with risk gate."""
        if self._run_risk_gate():
            return {"status": "blocked_by_risk"}

        result = self.engine1.execute()
        with self._lock:
            self._results["engine1"] = result

        # Check for actionable signals
        if result.get("action") == "sell":
            self.alert_manager.send(Alert(
                priority=AlertPriority.WARNING,
                title="Tether 매도 시그널",
                message=result.get("reason", "프리미엄 임계값 초과"),
                engine=EngineType.ENGINE1_TETHER,
            ))

        return result

    def _run_engine2(self) -> dict:
        """Execute Engine 2 cycle with risk gate."""
        if self._run_risk_gate():
            return {"status": "blocked_by_risk"}

        result = self.engine2.execute()
        with self._lock:
            self._results["engine2"] = result

        # Alert on stop-losses
        for sig in result.get("signals", []):
            if sig.get("action", "").startswith("sell_stop"):
                self.alert_manager.send(Alert(
                    priority=AlertPriority.CRITICAL,
                    title=f"손절 시그널: {sig['symbol']}",
                    message=sig.get("reason", ""),
                    engine=EngineType.ENGINE2_MAGIC,
                ))
            elif sig.get("action", "").startswith("sell_profit"):
                self.alert_manager.send(Alert(
                    priority=AlertPriority.WARNING,
                    title=f"익절 시그널: {sig['symbol']}",
                    message=sig.get("reason", ""),
                    engine=EngineType.ENGINE2_MAGIC,
                ))

        return result

    def _run_engine3(self) -> dict:
        """Execute Engine 3 cycle with risk gate."""
        if self._run_risk_gate():
            return {"status": "blocked_by_risk"}

        result = self.engine3.execute()
        with self._lock:
            self._results["engine3"] = result

        if result.get("should_rebalance"):
            self.alert_manager.send(Alert(
                priority=AlertPriority.WARNING,
                title="리밸런싱 필요",
                message="\n".join(result.get("trigger_reasons", [])),
                engine=EngineType.ENGINE3_WAREHOUSE,
            ))

        return result

    def pause_engine(self, engine_num: int):
        engines = {1: self.engine1, 2: self.engine2, 3: self.engine3}
        if engine_num in engines:
            engines[engine_num].pause()

    def resume_engine(self, engine_num: int):
        engines = {1: self.engine1, 2: self.engine2, 3: self.engine3}
        if engine_num in engines:
            engines[engine_num].resume()

    def pause_all(self):
        self.engine1.pause()
        self.engine2.pause()
        self.engine3.pause()

    def resume_all(self):
        self.engine1.resume()
        self.engine2.resume()
        self.engine3.resume()
