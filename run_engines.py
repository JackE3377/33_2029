# ============================================================
# GEM Protocol v3 — Engine Runner (Task Scheduler Entry Point)
# ============================================================
"""
Standalone script for Windows Task Scheduler.
No Streamlit dependency — fetches data, computes signals, saves to SQLite.

Usage:
    pythonw.exe run_engines.py fast     ← every 5 min (FX, tether, DXY, warehouse)
    pythonw.exe run_engines.py slow     ← every 30 min (stock screening only)
    pythonw.exe run_engines.py ai       ← once per day (screening + Gemini AI)
    python.exe  run_engines.py all      ← run all (for manual testing)
"""
from __future__ import annotations

import logging
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

# ── Logging ───────────────────────────────────────────────────

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "run_engines.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("gem.runner")


# ── Patch: remove @st.cache_data decorators at import time ────
# data_fetcher / news_fetcher use @st.cache_data which requires a
# running Streamlit server.  We monkey-patch st.cache_data to be a
# no-op decorator so these modules can be imported headlessly.

import types

_fake_st = types.ModuleType("streamlit")

def _noop_decorator(*args, **kwargs):
    """Return the function unchanged (strip @st.cache_data)."""
    if args and callable(args[0]):
        return args[0]
    return lambda fn: fn

_fake_st.cache_data = _noop_decorator
_fake_st.markdown = lambda *a, **kw: None
_fake_st.secrets = {}

# Only patch if streamlit is not already running
try:
    import streamlit as _real_st
    if not hasattr(_real_st, "_is_running_with_streamlit"):
        # Not inside `streamlit run`, safe to patch
        sys.modules["streamlit"] = _fake_st
except ImportError:
    sys.modules["streamlit"] = _fake_st


# ── Now safe to import project modules ────────────────────────

from core.config import get_settings
from services.cache_store import (
    FAST_SIGNALS, SLOW_STOCKS, WAREHOUSE,
    save_result, cleanup_old, load_latest,
)


def run_fast() -> None:
    """FAST group: signal data — runs every 5 min."""
    log.info("=== FAST group start ===")

    from services.data_fetcher import (
        fetch_macro, fetch_usdt_premium,
        fetch_dxy, fetch_jpy, fetch_fx_intraday,
    )
    from services.signal_engine import (
        calc_tether_signal, calc_dollar_signal, calc_fx_split_signal,
    )

    cfg = get_settings()

    macro = fetch_macro()
    crypto = fetch_usdt_premium(macro.usd_krw)
    dxy = fetch_dxy()
    jpy = fetch_jpy()

    usd_intraday = fetch_fx_intraday("KRW=X", "USD", 1.0)
    jpy_intraday = fetch_fx_intraday("JPYKRW=X", "JPY", 1.0)

    tether_sig = calc_tether_signal(macro, crypto)
    dollar_sig = calc_dollar_signal(dxy, macro)
    usd_split = calc_fx_split_signal(
        usd_intraday, cfg.fx_split_buy_interval_usd,
        cfg.fx_split_sell_interval_usd, dxy=dxy,
    )
    jpy_split = calc_fx_split_signal(
        jpy_intraday, cfg.fx_split_buy_interval_jpy,
        cfg.fx_split_sell_interval_jpy, dxy=dxy,
    )

    # Snapshot previous state for change detection
    prev_fast = load_latest(FAST_SIGNALS, max_age_seconds=600)
    prev_wh = load_latest(WAREHOUSE, max_age_seconds=600)
    prev_slow = load_latest(SLOW_STOCKS, max_age_seconds=86400)

    payload = {
        "macro": asdict(macro),
        "crypto": asdict(crypto),
        "dxy": asdict(dxy),
        "tether_sig": asdict(tether_sig),
        "dollar_sig": asdict(dollar_sig),
        "usd_split": asdict(usd_split),
        "jpy_split": asdict(jpy_split),
    }
    save_result(FAST_SIGNALS, payload)
    log.info("FAST group saved — USD ₩%.1f, DXY %.1f", macro.usd_krw, dxy.price)

    # Warehouse
    from services.data_fetcher import fetch_stocks_batch
    from services.signal_engine import calc_warehouse_signals
    from services.portfolio_store import load_portfolio

    portfolio = load_portfolio()
    wh_symbols = list(cfg.warehouse_allocations.keys())
    wh_quotes = fetch_stocks_batch(wh_symbols)
    wh_sigs = calc_warehouse_signals(wh_quotes, macro, portfolio.total_investment)

    wh_payload = {
        "wh_quotes": [asdict(q) for q in wh_quotes],
        "wh_sigs": [asdict(s) for s in wh_sigs],
    }
    save_result(WAREHOUSE, wh_payload)
    log.info("WAREHOUSE saved — %d signals", len(wh_sigs))

    cleanup_old(FAST_SIGNALS)
    cleanup_old(WAREHOUSE)

    # Telegram: notify signal changes
    try:
        from services.telegram_notifier import notify_signal_changes
        if prev_fast is not None:
            notify_signal_changes(
                new_fast=payload, new_wh=wh_payload,
                old_fast=prev_fast, old_wh=prev_wh,
                old_slow=prev_slow, new_slow=prev_slow,
            )
    except Exception:
        log.exception("Telegram signal notification failed")

    log.info("=== FAST group done ===")


def run_slow() -> None:
    """SLOW group: stock screening (no AI) — runs every 30 min."""
    log.info("=== SLOW group start ===")

    from services.data_fetcher import fetch_stocks_batch
    from services.signal_engine import calc_magic_signals
    from services.index_scanner import screen_index_stocks
    from services.cache_store import load_latest

    cfg = get_settings()

    wl_quotes = fetch_stocks_batch(cfg.watchlist)
    magic_sigs = calc_magic_signals(wl_quotes)
    screened = screen_index_stocks(top_n=cfg.index_screen_top_n_ai * 4)

    # Preserve previous AI results from last run_ai() execution
    prev = load_latest(SLOW_STOCKS, max_age_seconds=86400)
    prev_ai = prev.get("ai_top", []) if prev else []

    payload = {
        "wl_quotes": [asdict(q) for q in wl_quotes],
        "magic_sigs": [asdict(s) for s in magic_sigs],
        "screened": [asdict(s) for s in screened],
        "ai_top": prev_ai,
    }
    save_result(SLOW_STOCKS, payload)
    cleanup_old(SLOW_STOCKS)
    log.info("SLOW group saved — %d screened, %d AI preserved", len(screened), len(prev_ai))
    log.info("=== SLOW group done ===")


def run_ai() -> None:
    """AI group: screening + Gemini analysis — runs once per day."""
    log.info("=== AI group start ===")

    from services.data_fetcher import fetch_stocks_batch
    from services.news_fetcher import fetch_news
    from services.signal_engine import calc_magic_signals
    from services.stock_analyst import analyze_screened_stocks_batch
    from services.index_scanner import screen_index_stocks

    cfg = get_settings()

    wl_quotes = fetch_stocks_batch(cfg.watchlist)
    magic_sigs = calc_magic_signals(wl_quotes)

    screened = screen_index_stocks(top_n=cfg.index_screen_top_n_ai * 4)
    top_candidates = screened[:cfg.index_screen_top_n_ai]

    news_map = {}
    for s in top_candidates:
        news_map[s.symbol] = fetch_news(f"{s.symbol} stock")

    ai_top = analyze_screened_stocks_batch(
        screened, news_map, top_n=cfg.index_screen_top_n_ai,
    )

    payload = {
        "wl_quotes": [asdict(q) for q in wl_quotes],
        "magic_sigs": [asdict(s) for s in magic_sigs],
        "screened": [asdict(s) for s in screened],
        "ai_top": [asdict(r) if hasattr(r, "__dict__") else r.__dict__
                   for r in ai_top],
    }
    save_result(SLOW_STOCKS, payload)
    cleanup_old(SLOW_STOCKS)
    log.info("AI group saved — %d screened, %d AI results", len(screened), len(ai_top))

    # Telegram: send AI analysis results
    try:
        from services.telegram_notifier import notify_ai_results
        notify_ai_results(payload["ai_top"])
    except Exception:
        log.exception("Telegram AI notification failed")

    log.info("=== AI group done ===")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    mode = mode.lower().strip()

    log.info("run_engines started — mode=%s", mode)
    start = datetime.now(timezone.utc)

    if mode in ("fast", "all"):
        run_fast()
    if mode in ("slow", "all"):
        run_slow()
    if mode in ("ai", "all"):
        run_ai()

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    log.info("run_engines finished — %.1fs elapsed", elapsed)


if __name__ == "__main__":
    main()
