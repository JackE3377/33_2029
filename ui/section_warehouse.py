# ============================================================
# GEM Protocol v3 — Section 3: Warehouse LAA (Dynamic Rebalancing)
# ============================================================
from __future__ import annotations

import streamlit as st

from core.config import get_settings
from services.data_fetcher import StockQuote
from services.signal_engine import WarehouseSignal
from services.portfolio_store import load_portfolio, save_portfolio
from ui.components import (
    section_title, traffic_light, alert_critical, alert_warning, metric_grid,
)


def render_warehouse(
    quotes: list[StockQuote],
    signals: list[WarehouseSignal],
):
    section_title("🏛️ Warehouse LAA", "동적 리밸런싱 — Dual Momentum + RSI")

    cfg = get_settings()
    portfolio = load_portfolio()

    # ── Total Investment Input ────────────────────────────────
    st.markdown("##### 💰 총 투자금 설정")
    total = st.number_input(
        "총 투자금 (원)",
        min_value=0,
        value=int(portfolio.total_investment),
        step=1_000_000,
        format="%d",
        key="laa_total_investment",
    )
    if total != portfolio.total_investment:
        portfolio.total_investment = float(total)
        save_portfolio(portfolio)

    # ── Panic alert ───────────────────────────────────────────
    for sig in signals:
        if sig.status == "panic":
            alert_critical(sig.label)

    # ── Allocation Table ──────────────────────────────────────
    st.markdown("##### 📊 목표 배분 + 투입 금액")

    alloc_metrics = []
    for sym, pct in cfg.warehouse_allocations.items():
        q = next((x for x in quotes if x.symbol == sym), None)
        price_str = f"${q.price:,.2f}" if q and q.price > 0 else "—"
        if total > 0:
            target_krw = total * pct
            alloc_metrics.append({
                "label": f"{sym} ({pct*100:.0f}%)",
                "value": price_str,
                "sub": f"목표: ₩{target_krw:,.0f}",
            })
        else:
            alloc_metrics.append({
                "label": f"{sym} ({pct*100:.0f}%)",
                "value": price_str,
            })
    metric_grid(alloc_metrics)

    # ── Momentum + 200MA Status ───────────────────────────────
    st.markdown("##### 📈 모멘텀 & 200일 이평선")
    asset_signals = [s for s in signals if s.symbol not in ("NASDAQ", "NASDAQ-200MA")]

    for sig in asset_signals:
        cols = st.columns([2, 2, 2, 3])
        with cols[0]:
            st.markdown(f"**{sig.symbol}** ({sig.target_pct*100:.0f}%)")
        with cols[1]:
            if sig.momentum_12m is not None:
                color = "green" if sig.momentum_12m > 0 else "red"
                st.markdown(f"12M: :{color}[{sig.momentum_12m:+.1f}%]")
            else:
                st.markdown("12M: —")
        with cols[2]:
            if sig.above_200dma is not None:
                st.markdown("200MA: ✅ 상회" if sig.above_200dma else "200MA: ⚠️ 하회")
            else:
                st.markdown("200MA: —")
        with cols[3]:
            if total > 0 and sig.invest_amount > 0:
                st.markdown(f"투입: **₩{sig.invest_amount:,.0f}**")

    # ── Traffic Light Signals ─────────────────────────────────
    st.markdown("##### 🚦 RSI 신호등")
    for sig in signals:
        if sig.status == "panic":
            continue
        traffic_light(sig.symbol, sig.status, sig.label)

    # ── Hot / Cold / Momentum Summary ─────────────────────────
    hot = [s for s in signals if s.status == "hot"]
    cold = [s for s in signals if s.status == "cold"]
    mom_off = [s for s in signals if s.status == "momentum_off"]

    if mom_off:
        alert_warning(
            f"모멘텀 음수: {', '.join(s.symbol for s in mom_off)} — SHY(단기채) 대체 검토"
        )
    if hot:
        alert_warning(
            f"과열 자산: {', '.join(s.symbol for s in hot)} — 비중 축소 검토"
        )
    if cold:
        st.markdown(
            f"❄️ **침체 자산:** {', '.join(s.symbol for s in cold)} — 비중 확대 검토"
        )
