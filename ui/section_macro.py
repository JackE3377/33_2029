# ============================================================
# GEM Protocol v2 — Section 1: Macro / Tether
# ============================================================
from __future__ import annotations

import streamlit as st

from services.data_fetcher import MacroData, CryptoQuote
from services.signal_engine import TetherSignal
from ui.components import (
    section_title, big_metric, metric_grid,
    alert_critical, alert_warning, alert_info,
)


def render_macro(macro: MacroData, crypto: CryptoQuote, tether: TetherSignal):
    section_title("📡 매크로 & 테더", "글로벌 시장 체크포인트")

    # ── Tether alerts first ───────────────────────────────────
    for msg in tether.alerts:
        if "🔴" in msg:
            alert_critical(msg)
        elif "🟢" in msg:
            alert_info(msg)
        else:
            alert_warning(msg)

    # ── Giant metrics row ─────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        prem_css = "down" if crypto.kimchi_premium_pct < 0 else ("up" if crypto.kimchi_premium_pct >= 3 else "")
        big_metric(
            "USDT 김치프리미엄",
            f"{crypto.kimchi_premium_pct:+.2f}%",
            f"USDT {crypto.price_krw:,.0f}원",
            css=prem_css,
        )
    with c2:
        krw_css = "up" if macro.usd_krw >= 1400 else ""
        big_metric(
            "USD/KRW",
            f"₩{macro.usd_krw:,.1f}",
            css=krw_css,
        )

    # ── Secondary metrics grid ────────────────────────────────
    vix_css = "up" if macro.vix >= 25 else ("down" if macro.vix < 15 else "")
    sp_css = "up" if macro.sp500_daily_chg_pct > 0 else ("down" if macro.sp500_daily_chg_pct < 0 else "")
    nq_css = "up" if macro.nasdaq_daily_chg_pct > 0 else ("down" if macro.nasdaq_daily_chg_pct < 0 else "")

    metrics = [
        {"label": "VIX", "value": f"{macro.vix:.1f}", "css": vix_css},
        {"label": "S&P 500", "value": f"{macro.sp500_daily_chg_pct:+.2f}%", "css": sp_css},
        {"label": "NASDAQ", "value": f"{macro.nasdaq_daily_chg_pct:+.2f}%", "css": nq_css},
    ]
    if macro.fed_funds_rate is not None:
        metrics.append({"label": "기준금리", "value": f"{macro.fed_funds_rate:.2f}%"})

    metric_grid(metrics)

    # ── Tether action ─────────────────────────────────────────
    action_map = {
        "SELL_USDT": ("🔴 테더 매도 타이밍", "김프 고점 — USDT → KRW 전환 고려"),
        "BUY_USDT": ("🟢 테더 매수 기회", "역프 발생 — KRW → USDT 전환 고려"),
        "HOLD": ("⚪ 중립 구간", "김치 프리미엄 정상 범위 — 관망"),
    }
    title, desc = action_map.get(tether.action, ("⚪ 중립", ""))
    st.markdown(f"**{title}** — {desc}")
