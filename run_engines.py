#!/usr/bin/env python
"""
GEM Protocol — Standalone Engine Runner
========================================
Windows 작업 스케줄러에서 호출되는 독립 실행 스크립트.

사용법:
  python run_engines.py --group fast     # Engine 1 + 2 (5분 주기)
  python run_engines.py --group slow     # Engine 3      (1시간 주기)
  python run_engines.py --group all      # 전체 (수동/테스트)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from core.config import get_settings
from core.logger import setup_logging, get_logger
from core.models import (
    EngineResult, EngineType, MacroSnapshot,
    get_session, get_db_engine,
)
from services.data_fetcher import DataFetcher
from services.risk_manager import RiskManager
from services.alert_manager import AlertManager, Alert
from core.models import AlertPriority

setup_logging()
logger = get_logger("run_engines")


def save_engine_result(engine_type: EngineType, result: dict, status: str = "ok"):
    """엔진 결과를 DB에 저장."""
    session = get_session()
    try:
        row = EngineResult(
            engine=engine_type,
            timestamp=datetime.now(timezone.utc),
            result_json=json.dumps(result, ensure_ascii=False, default=str),
            status=status,
        )
        session.add(row)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to save engine result: {e}")
    finally:
        session.close()


def save_macro_snapshot(macro):
    """매크로 데이터를 DB에 저장."""
    session = get_session()
    try:
        row = MacroSnapshot(
            timestamp=datetime.now(timezone.utc),
            usd_krw=macro.usd_krw,
            vix=macro.vix,
            sp500_daily_chg_pct=macro.sp500_daily_chg_pct,
            nasdaq_daily_chg_pct=macro.nasdaq_daily_chg_pct,
            fed_funds_rate=macro.fed_funds_rate,
        )
        session.add(row)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to save macro snapshot: {e}")
    finally:
        session.close()


def run_risk_gate(alert_mgr: AlertManager) -> tuple[bool, dict, dict]:
    """매크로 조회 + 리스크 판단. Returns (blocked, macro_dict, risk_dict)."""
    macro = DataFetcher.get_macro()
    save_macro_snapshot(macro)

    risk_mgr = RiskManager()
    state = risk_mgr.evaluate(
        vix=macro.vix,
        sp500_daily_chg_pct=macro.sp500_daily_chg_pct,
        daily_pnl_pct=0,
    )

    macro_dict = {
        "vix": macro.vix,
        "usd_krw": macro.usd_krw,
        "sp500_daily_chg_pct": macro.sp500_daily_chg_pct,
        "nasdaq_daily_chg_pct": macro.nasdaq_daily_chg_pct,
        "fed_funds_rate": macro.fed_funds_rate,
    }
    risk_dict = {
        "circuit_breaker_active": state.circuit_breaker_active,
        "black_swan_active": state.black_swan_active,
        "blocked_reasons": state.blocked_reasons,
    }

    # Save macro/risk as pseudo-engine results for dashboard
    save_engine_result(EngineType.ENGINE1_TETHER, {"_macro": macro_dict, "_risk": risk_dict}, status="macro")

    if state.circuit_breaker_active:
        alert_mgr.send(Alert(
            priority=AlertPriority.CRITICAL,
            title="Circuit Breaker Activated",
            message="\n".join(state.blocked_reasons),
        ))
        logger.warning(f"RISK BLOCKED: {state.blocked_reasons}")
        return True, macro_dict, risk_dict

    return False, macro_dict, risk_dict


def run_fast(alert_mgr: AlertManager):
    """Engine 1 (Tether) + Engine 2 (Magic Split) — 5분 주기."""
    logger.info("=== FAST group start (Engine 1 + 2) ===")

    blocked, macro_dict, risk_dict = run_risk_gate(alert_mgr)
    if blocked:
        save_engine_result(EngineType.ENGINE1_TETHER, {"status": "blocked_by_risk"}, "blocked")
        save_engine_result(EngineType.ENGINE2_MAGIC, {"status": "blocked_by_risk"}, "blocked")
        return

    # Engine 1: Tether
    try:
        from engines.engine1_tether import TetherEngine
        e1 = TetherEngine()
        r1 = e1.execute()
        save_engine_result(EngineType.ENGINE1_TETHER, r1)
        logger.info(f"Engine 1 done: action={r1.get('action')}, premium={r1.get('raw_premium_pct', 0):.2f}%")

        if r1.get("action") == "sell":
            alert_mgr.send(Alert(
                priority=AlertPriority.WARNING,
                title="Tether 매도 시그널",
                message=r1.get("reason", "프리미엄 임계값 초과"),
                engine=EngineType.ENGINE1_TETHER,
            ))
    except Exception as e:
        logger.error(f"Engine 1 failed: {e}", exc_info=True)
        save_engine_result(EngineType.ENGINE1_TETHER, {"error": str(e)}, "error")

    # Engine 2: Magic Split
    try:
        from engines.engine2_magic_split import MagicSplitEngine
        e2 = MagicSplitEngine()
        r2 = e2.execute()
        save_engine_result(EngineType.ENGINE2_MAGIC, r2)
        signals = r2.get("signals", [])
        logger.info(f"Engine 2 done: positions={r2.get('positions_count', 0)}, signals={len(signals)}")

        for sig in signals:
            action = sig.get("action", "")
            if action.startswith("sell_stop"):
                alert_mgr.send(Alert(
                    priority=AlertPriority.CRITICAL,
                    title=f"손절 시그널: {sig['symbol']}",
                    message=sig.get("reason", ""),
                    engine=EngineType.ENGINE2_MAGIC,
                ))
            elif action.startswith("sell_profit"):
                alert_mgr.send(Alert(
                    priority=AlertPriority.WARNING,
                    title=f"익절 시그널: {sig['symbol']}",
                    message=sig.get("reason", ""),
                    engine=EngineType.ENGINE2_MAGIC,
                ))
    except Exception as e:
        logger.error(f"Engine 2 failed: {e}", exc_info=True)
        save_engine_result(EngineType.ENGINE2_MAGIC, {"error": str(e)}, "error")


def run_slow(alert_mgr: AlertManager):
    """Engine 3 (Warehouse) — 1시간 주기."""
    logger.info("=== SLOW group start (Engine 3) ===")

    blocked, macro_dict, risk_dict = run_risk_gate(alert_mgr)
    if blocked:
        save_engine_result(EngineType.ENGINE3_WAREHOUSE, {"status": "blocked_by_risk"}, "blocked")
        return

    try:
        from engines.engine3_warehouse import WarehouseEngine
        e3 = WarehouseEngine()
        r3 = e3.execute()
        save_engine_result(EngineType.ENGINE3_WAREHOUSE, r3)
        logger.info(f"Engine 3 done: rebalance={r3.get('should_rebalance')}")

        if r3.get("should_rebalance"):
            alert_mgr.send(Alert(
                priority=AlertPriority.WARNING,
                title="리밸런싱 필요",
                message="\n".join(r3.get("trigger_reasons", [])),
                engine=EngineType.ENGINE3_WAREHOUSE,
            ))
    except Exception as e:
        logger.error(f"Engine 3 failed: {e}", exc_info=True)
        save_engine_result(EngineType.ENGINE3_WAREHOUSE, {"error": str(e)}, "error")


def main():
    parser = argparse.ArgumentParser(description="GEM Protocol Engine Runner")
    parser.add_argument(
        "--group",
        choices=["fast", "slow", "all"],
        default="all",
        help="fast=Engine1+2 (5분), slow=Engine3 (1시간), all=전체",
    )
    args = parser.parse_args()

    alert_mgr = AlertManager()

    if args.group in ("fast", "all"):
        run_fast(alert_mgr)
    if args.group in ("slow", "all"):
        run_slow(alert_mgr)

    logger.info(f"=== {args.group.upper()} group complete ===")


if __name__ == "__main__":
    main()
