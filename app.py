# ============================================================
# GEM Protocol v3 — Zero PII Quant Signal Dashboard
# ============================================================
"""
streamlit run app.py

3-tab dashboard: 종합 시그널, 주식 탐색, Warehouse LAA.
Reads pre-computed results from SQLite (populated by run_engines.py).
Falls back to live computation when DB cache is stale.
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

# Must be the first Streamlit command
st.set_page_config(
    page_title="GEM Protocol v3",
    page_icon="\U0001f48e",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from core.config import get_settings
from ui.styles import DARK_CSS

# Inject dark-mode CSS
st.markdown(DARK_CSS, unsafe_allow_html=True)


# ── DB-first data loaders ────────────────────────────────────

from services.cache_store import load_latest, FAST_SIGNALS, SLOW_STOCKS, WAREHOUSE
from services.data_fetcher import (
    MacroData, CryptoQuote, DXYData, FXIntraday,
)
from services.signal_engine import (
    TetherSignal, DollarSignal, FXSplitSignal, WarehouseSignal, MagicSignal,
)
from services.stock_analyst import AnalysisResult
from services.data_fetcher import StockQuote
from services.index_scanner import ScreenedStock


def _rebuild_dataclass(cls, d: dict):
    """Safely reconstruct a dataclass from a dict, ignoring extra keys."""
    import dataclasses
    fields = {f.name for f in dataclasses.fields(cls)}
    return cls(**{k: v for k, v in d.items() if k in fields})


@st.cache_data(ttl=60, show_spinner=False)
def _load_signals():
    """Read FAST signals from DB. Fallback to live fetch if stale."""
    cached = load_latest(FAST_SIGNALS, max_age_seconds=3600)  # 1h
    if cached:
        return {
            "crypto": _rebuild_dataclass(CryptoQuote, cached["crypto"]),
            "dxy": _rebuild_dataclass(DXYData, cached["dxy"]),
            "tether_sig": _rebuild_dataclass(TetherSignal, cached["tether_sig"]),
            "dollar_sig": _rebuild_dataclass(DollarSignal, cached["dollar_sig"]),
            "usd_split": _rebuild_dataclass(FXSplitSignal, cached["usd_split"]),
            "jpy_split": _rebuild_dataclass(FXSplitSignal, cached["jpy_split"]),
        }

    # Fallback: live computation
    from services.data_fetcher import (
        fetch_macro, fetch_usdt_premium,
        fetch_dxy, fetch_fx_intraday,
    )
    from services.signal_engine import (
        calc_tether_signal, calc_dollar_signal, calc_fx_split_signal,
    )

    cfg = get_settings()
    macro = fetch_macro()
    crypto = fetch_usdt_premium(macro.usd_krw)
    dxy = fetch_dxy()

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

    return {
        "crypto": crypto,
        "dxy": dxy,
        "tether_sig": tether_sig,
        "dollar_sig": dollar_sig,
        "usd_split": usd_split,
        "jpy_split": jpy_split,
    }


@st.cache_data(ttl=60, show_spinner=False)
def _load_heavy():
    """Read SLOW stock results from DB. Fallback to live if stale."""
    cached = load_latest(SLOW_STOCKS, max_age_seconds=86400)  # 24h — AI runs once/day
    if cached:
        return {
            "wl_quotes": [_rebuild_dataclass(StockQuote, q) for q in cached["wl_quotes"]],
            "magic_sigs": [_rebuild_dataclass(MagicSignal, s) for s in cached["magic_sigs"]],
            "screened": [_rebuild_dataclass(ScreenedStock, s) for s in cached["screened"]],
            "ai_top": [_rebuild_dataclass(AnalysisResult, r) for r in cached.get("ai_top", [])],
        }

    # Fallback: live screening only (no AI — AI runs via run_engines.py ai)
    from services.data_fetcher import fetch_stocks_batch
    from services.signal_engine import calc_magic_signals
    from services.index_scanner import screen_index_stocks

    cfg = get_settings()
    wl_quotes = fetch_stocks_batch(cfg.watchlist)
    magic_sigs = calc_magic_signals(wl_quotes)
    screened = screen_index_stocks(top_n=cfg.index_screen_top_n_ai * 4)

    return {
        "wl_quotes": wl_quotes,
        "magic_sigs": magic_sigs,
        "screened": screened,
        "ai_top": [],
    }


@st.cache_data(ttl=60, show_spinner=False)
def _load_warehouse():
    """Read WAREHOUSE from DB. Fallback to live if stale."""
    cached = load_latest(WAREHOUSE, max_age_seconds=3600)  # 1h
    if cached:
        return {
            "wh_quotes": [_rebuild_dataclass(StockQuote, q) for q in cached["wh_quotes"]],
            "wh_sigs": [_rebuild_dataclass(WarehouseSignal, s) for s in cached["wh_sigs"]],
        }

    # Fallback: live computation
    from services.data_fetcher import fetch_stocks_batch, fetch_macro
    from services.signal_engine import calc_warehouse_signals
    from services.portfolio_store import load_portfolio

    cfg = get_settings()
    macro = fetch_macro()
    portfolio = load_portfolio()

    wh_symbols = list(cfg.warehouse_allocations.keys())
    wh_quotes = fetch_stocks_batch(wh_symbols)
    wh_sigs = calc_warehouse_signals(wh_quotes, macro, portfolio.total_investment)

    return {
        "wh_quotes": wh_quotes,
        "wh_sigs": wh_sigs,
    }


# ── Header (compact, no sidebar) ─────────────────────────────

_hdr_l, _hdr_r = st.columns([8, 1])
with _hdr_l:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;padding:4px 0;">'
        f'<span style="font-size:22px;">\U0001f48e</span>'
        f'<span style="font-size:16px;font-weight:700;">GEM Protocol</span>'
        f'<span style="font-size:11px;color:#6e6e73;">{now}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
with _hdr_r:
    if st.button("\U0001f504", help="새로고침"):
        _load_signals.clear()
        _load_heavy.clear()
        _load_warehouse.clear()
        st.rerun()


# ── Load fast signal data ────────────────────────────────────

sig = _load_signals()

# ── Tabs ─────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs([
    "🚦 종합 시그널",
    "🔍 주식 탐색",
    "🏛️ Warehouse LAA",
])

with tab1:
    from ui.section_signals import render_signals
    # Pre-load warehouse + stock data for summary cards
    try:
        wh = _load_warehouse()
        wh_sigs = wh["wh_sigs"]
    except Exception:
        wh_sigs = None

    try:
        heavy = _load_heavy()
        ai_top = heavy["ai_top"]
    except Exception:
        ai_top = None

    render_signals(
        tether=sig["tether_sig"],
        crypto=sig["crypto"],
        dxy=sig["dxy"],
        dollar=sig["dollar_sig"],
        usd_split=sig["usd_split"],
        jpy_split=sig["jpy_split"],
        wh_signals=wh_sigs,
        ai_results=ai_top,
    )

with tab2:
    heavy = _load_heavy()
    from ui.section_stock import render_stock_explorer
    render_stock_explorer(
        wl_quotes=heavy["wl_quotes"],
        magic_signals=heavy["magic_sigs"],
        ai_results=heavy["ai_top"],
        screened=heavy["screened"],
    )

with tab3:
    wh = _load_warehouse()
    from ui.section_warehouse import render_warehouse
    render_warehouse(wh["wh_quotes"], wh["wh_sigs"])
