# ============================================================
# GEM Protocol v2 — Zero PII Quant Signal Dashboard
# ============================================================
"""
streamlit run app.py

4-tab dashboard: Macro/Tether, Magic Split + AI Top 5,
Warehouse LAA, Signal Summary.  Zero personal data.
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

# Must be the first Streamlit command
st.set_page_config(
    page_title="GEM Protocol v2",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from core.config import get_settings
from ui.styles import DARK_CSS

# Inject dark-mode CSS
st.markdown(DARK_CSS, unsafe_allow_html=True)


# ── Data loader (cached via st.cache_data inside each fetcher) ──

@st.cache_data(ttl=300, show_spinner="데이터 로딩 중…")
def _load_all():
    from services.data_fetcher import fetch_macro, fetch_stocks_batch, fetch_usdt_premium
    from services.news_fetcher import fetch_news
    from services.signal_engine import calc_tether_signal, calc_magic_signals, calc_warehouse_signals
    from services.stock_analyst import analyze_watchlist, AnalysisResult
    from services.news_fetcher import NewsItem

    cfg = get_settings()

    # 1) Macro + Crypto
    macro = fetch_macro()
    crypto = fetch_usdt_premium(macro.usd_krw)

    # 2) Watchlist quotes
    wl_quotes = fetch_stocks_batch(cfg.watchlist)

    # 3) Warehouse quotes
    wh_symbols = list(cfg.warehouse_allocations.keys())
    wh_quotes = fetch_stocks_batch(wh_symbols)

    # 4) Signals
    tether_sig = calc_tether_signal(macro, crypto)
    magic_sigs = calc_magic_signals(wl_quotes)
    wh_sigs = calc_warehouse_signals(wh_quotes, macro)

    # 5) News for watchlist
    news_map: dict[str, list[NewsItem]] = {}
    for sym in cfg.watchlist[:10]:  # limit to avoid rate limits
        news_map[sym] = fetch_news(f"{sym} stock")

    # 6) AI analysis (top 5)
    ai_results = analyze_watchlist(wl_quotes, news_map, top_n=5)

    return {
        "macro": macro,
        "crypto": crypto,
        "tether_sig": tether_sig,
        "wl_quotes": wl_quotes,
        "magic_sigs": magic_sigs,
        "wh_quotes": wh_quotes,
        "wh_sigs": wh_sigs,
        "ai_results": ai_results,
    }


# ── Sidebar ───────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div style="text-align:center;padding:20px 0;">'
        '<div style="font-size:32px;">💎</div>'
        '<div style="font-size:18px;font-weight:700;margin-top:8px;">GEM Protocol v2</div>'
        '<div style="font-size:12px;color:#86868b;margin-top:4px;">Zero PII Quant Signal</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    if st.button("🔄 새로고침", use_container_width=True):
        _load_all.clear()
        st.rerun()

    st.divider()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    st.caption(f"v2.0 · {now}")


# ── Load data ─────────────────────────────────────────────────

data = _load_all()

# ── Tabs ──────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "📡 매크로 & 테더",
    "🎯 Magic Split",
    "🏛️ Warehouse LAA",
    "📊 종합 시그널",
])

with tab1:
    from ui.section_macro import render_macro
    render_macro(data["macro"], data["crypto"], data["tether_sig"])

with tab2:
    from ui.section_magic import render_magic
    render_magic(data["wl_quotes"], data["magic_sigs"], data["ai_results"])

with tab3:
    from ui.section_warehouse import render_warehouse
    render_warehouse(data["wh_quotes"], data["wh_sigs"])

with tab4:
    from ui.section_signals import render_signals
    render_signals(data["tether_sig"], data["magic_sigs"], data["wh_sigs"])
