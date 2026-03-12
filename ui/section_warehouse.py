# ============================================================
# GEM Protocol v2 — Section 3: Warehouse LAA
# ============================================================
from __future__ import annotations

import streamlit as st

from core.config import get_settings
from services.data_fetcher import StockQuote
from services.signal_engine import WarehouseSignal
from ui.components import (
    section_title, traffic_light, alert_critical, alert_warning, metric_grid,
)


def render_warehouse(
    quotes: list[StockQuote],
    signals: list[WarehouseSignal],
):
    section_title("🏛️ Warehouse LAA", "자산배분 리밸런싱 신호")

    cfg = get_settings()

    # ── Panic alert first ─────────────────────────────────────
    for sig in signals:
        if sig.status == "panic":
            alert_critical(sig.label)

    # ── Allocation overview ───────────────────────────────────
    st.markdown("##### 📊 목표 배분")
    alloc_metrics = []
    for sym, pct in cfg.warehouse_allocations.items():
        # Find matching quote
        q = next((x for x in quotes if x.symbol == sym), None)
        price_str = f"${q.price:,.2f}" if q and q.price > 0 else "—"
        alloc_metrics.append({
            "label": f"{sym} ({pct*100:.0f}%)",
            "value": price_str,
        })
    metric_grid(alloc_metrics)

    # ── Traffic light signals ─────────────────────────────────
    st.markdown("##### 🚦 RSI 신호등")
    for sig in signals:
        if sig.status == "panic":
            continue  # Already shown as alert
        traffic_light(sig.symbol, sig.status, sig.label)

    # ── Hot / Cold summary ────────────────────────────────────
    hot = [s for s in signals if s.status == "hot"]
    cold = [s for s in signals if s.status == "cold"]

    if hot:
        alert_warning(
            f"과열 자산: {', '.join(s.symbol for s in hot)} — 비중 축소 검토"
        )
    if cold:
        st.markdown(
            f"❄️ **침체 자산:** {', '.join(s.symbol for s in cold)} — 비중 확대 검토"
        )
