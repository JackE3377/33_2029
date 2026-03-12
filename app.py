# ============================================================
# GEM Protocol v2 — Zero PII Quant Signal Dashboard
# ============================================================
"""
streamlit run app.py

4-tab dashboard: Signal, Macro, Magic Split, Warehouse LAA.
Zero personal data.
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

# Must be the first Streamlit command
st.set_page_config(
    page_title="GEM Protocol v2",
    page_icon="\U0001f48e",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from core.config import get_settings
from ui.styles import DARK_CSS

# Inject dark-mode CSS
st.markdown(DARK_CSS, unsafe_allow_html=True)


# ── Data loaders ─────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner="\uc2e0\ud638 \ub370\uc774\ud130 \ub85c\ub529 \uc911\u2026")
def _load_signals():
    """Fast path: signal dashboard data only (~5-8s)."""
    from services.data_fetcher import (
        fetch_macro, fetch_usdt_premium,
        fetch_dxy, fetch_bank_rates, fetch_jpy, fetch_bank_rates_jpy,
    )
    from services.signal_engine import (
        calc_tether_signal, calc_dollar_signal, calc_yen_signal,
    )

    macro = fetch_macro()
    crypto = fetch_usdt_premium(macro.usd_krw)
    dxy = fetch_dxy()
    bank_rates = fetch_bank_rates(macro.usd_krw)
    jpy = fetch_jpy()
    bank_rates_jpy = fetch_bank_rates_jpy(jpy.price) if jpy.price > 0 else []

    tether_sig = calc_tether_signal(macro, crypto)
    dollar_sig = calc_dollar_signal(dxy, macro)
    yen_sig = calc_yen_signal(jpy)

    return {
        "macro": macro,
        "crypto": crypto,
        "dxy": dxy,
        "bank_rates": bank_rates,
        "bank_rates_jpy": bank_rates_jpy,
        "tether_sig": tether_sig,
        "dollar_sig": dollar_sig,
        "yen_sig": yen_sig,
    }


@st.cache_data(ttl=300, show_spinner="\uc885\ubaa9 \ubd84\uc11d \uc911\u2026")
def _load_heavy():
    """Slow path: stock screening + AI (lazy, only when needed)."""
    from services.data_fetcher import fetch_stocks_batch
    from services.news_fetcher import fetch_news, NewsItem
    from services.signal_engine import calc_magic_signals, calc_warehouse_signals
    from services.stock_analyst import analyze_screened_stocks
    from services.index_scanner import screen_index_stocks

    cfg = get_settings()
    sig = _load_signals()
    macro = sig["macro"]

    wl_quotes = fetch_stocks_batch(cfg.watchlist)
    wh_symbols = list(cfg.warehouse_allocations.keys())
    wh_quotes = fetch_stocks_batch(wh_symbols)

    magic_sigs = calc_magic_signals(wl_quotes)
    wh_sigs = calc_warehouse_signals(wh_quotes, macro)

    screened = screen_index_stocks(top_n=cfg.index_screen_top_n_ai * 4)

    top_candidates = screened[: cfg.index_screen_top_n_ai]
    news_map: dict[str, list[NewsItem]] = {}
    for s in top_candidates:
        news_map[s.symbol] = fetch_news(f"{s.symbol} stock")

    ai_top = analyze_screened_stocks(
        screened, news_map, top_n=cfg.index_screen_top_n_ai,
    )

    return {
        "wl_quotes": wl_quotes,
        "magic_sigs": magic_sigs,
        "wh_quotes": wh_quotes,
        "wh_sigs": wh_sigs,
        "screened": screened,
        "ai_top": ai_top,
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
    if st.button("\U0001f504", help="\uc0c8\ub85c\uace0\uce68"):
        _load_signals.clear()
        _load_heavy.clear()
        st.rerun()


# ── Load fast signal data ────────────────────────────────────

sig = _load_signals()

# ── Tabs ─────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "\U0001f6a6 \uc885\ud569 \uc2dc\uadf8\ub110",
    "\U0001f4e1 \ub9e4\ud06c\ub85c & \ub2ec\ub7ec",
    "\U0001f3af Magic Split",
    "\U0001f3db\ufe0f Warehouse",
])

with tab1:
    from ui.section_signals import render_signals
    render_signals(
        tether=sig["tether_sig"],
        crypto=sig["crypto"],
        bank_rates=sig["bank_rates"],
        dxy=sig["dxy"],
        dollar=sig["dollar_sig"],
        yen=sig["yen_sig"],
        bank_rates_jpy=sig["bank_rates_jpy"],
    )

with tab2:
    from ui.section_macro import render_macro
    render_macro(
        sig["macro"], sig["crypto"], sig["tether_sig"],
        dxy=sig["dxy"],
        bank_rates=sig["bank_rates"],
    )

with tab3:
    heavy = _load_heavy()
    from ui.section_magic import render_magic
    render_magic(heavy["wl_quotes"], heavy["magic_sigs"], heavy["ai_top"])

with tab4:
    heavy = _load_heavy()
    from ui.section_warehouse import render_warehouse
    render_warehouse(heavy["wh_quotes"], heavy["wh_sigs"])
