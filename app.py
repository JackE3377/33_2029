# ============================================================
# GEM Protocol v3 — Zero PII Quant Signal Dashboard
# ============================================================
"""
streamlit run app.py

3-tab dashboard: 종합 시그널, 주식 탐색, Warehouse LAA.
Reads pre-computed results from SQLite (populated by run_engines.py).
No live computation — DB only.
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

from ui.styles import DARK_CSS

# Inject dark-mode CSS
st.markdown(DARK_CSS, unsafe_allow_html=True)


# ── DB-only data loaders (no live computation) ───────────────

from services.cache_store import load_latest, FAST_SIGNALS, SLOW_STOCKS, WAREHOUSE
from services.data_fetcher import CryptoQuote, DXYData
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


_NO_AGE_LIMIT = 999_999  # accept any DB data regardless of age


@st.cache_data(ttl=60, show_spinner=False)
def _load_signals() -> dict | None:
    """Read FAST signals from DB. Returns None if no data."""
    cached = load_latest(FAST_SIGNALS, max_age_seconds=_NO_AGE_LIMIT)
    if not cached:
        return None
    return {
        "crypto": _rebuild_dataclass(CryptoQuote, cached["crypto"]),
        "dxy": _rebuild_dataclass(DXYData, cached["dxy"]),
        "tether_sig": _rebuild_dataclass(TetherSignal, cached["tether_sig"]),
        "dollar_sig": _rebuild_dataclass(DollarSignal, cached["dollar_sig"]),
        "usd_split": _rebuild_dataclass(FXSplitSignal, cached["usd_split"]),
        "jpy_split": _rebuild_dataclass(FXSplitSignal, cached["jpy_split"]),
    }


@st.cache_data(ttl=60, show_spinner=False)
def _load_heavy() -> dict | None:
    """Read SLOW stock results from DB. Returns None if no data."""
    cached = load_latest(SLOW_STOCKS, max_age_seconds=_NO_AGE_LIMIT)
    if not cached:
        return None
    return {
        "wl_quotes": [_rebuild_dataclass(StockQuote, q) for q in cached["wl_quotes"]],
        "magic_sigs": [_rebuild_dataclass(MagicSignal, s) for s in cached["magic_sigs"]],
        "screened": [_rebuild_dataclass(ScreenedStock, s) for s in cached["screened"]],
        "ai_top": [_rebuild_dataclass(AnalysisResult, r) for r in cached.get("ai_top", [])],
    }


@st.cache_data(ttl=60, show_spinner=False)
def _load_warehouse() -> dict | None:
    """Read WAREHOUSE from DB. Returns None if no data."""
    cached = load_latest(WAREHOUSE, max_age_seconds=_NO_AGE_LIMIT)
    if not cached:
        return None
    return {
        "wh_quotes": [_rebuild_dataclass(StockQuote, q) for q in cached["wh_quotes"]],
        "wh_sigs": [_rebuild_dataclass(WarehouseSignal, s) for s in cached["wh_sigs"]],
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


# ── Load data from DB ────────────────────────────────────────

sig = _load_signals()
heavy = _load_heavy()
wh = _load_warehouse()

_NO_DATA_MSG = "⏳ 데이터 없음 — `run_engines.py all` 실행 후 새로고침하세요."

# ── Tabs ─────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs([
    "🚦 종합 시그널",
    "🔍 주식 탐색",
    "🏛️ Warehouse LAA",
])

with tab1:
    if sig:
        from ui.section_signals import render_signals
        render_signals(
            tether=sig["tether_sig"],
            crypto=sig["crypto"],
            dxy=sig["dxy"],
            dollar=sig["dollar_sig"],
            usd_split=sig["usd_split"],
            jpy_split=sig["jpy_split"],
            wh_signals=wh["wh_sigs"] if wh else None,
            ai_results=heavy["ai_top"] if heavy else None,
        )
    else:
        st.info(_NO_DATA_MSG)

with tab2:
    if heavy:
        from ui.section_stock import render_stock_explorer
        render_stock_explorer(
            wl_quotes=heavy["wl_quotes"],
            magic_signals=heavy["magic_sigs"],
            ai_results=heavy["ai_top"],
            screened=heavy["screened"],
        )
    else:
        st.info(_NO_DATA_MSG)

with tab3:
    if wh:
        from ui.section_warehouse import render_warehouse
        render_warehouse(wh["wh_quotes"], wh["wh_sigs"])
    else:
        st.info(_NO_DATA_MSG)
