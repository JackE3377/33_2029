# ============================================================
# GEM Protocol v2 — Section 4: Signal Summary
# ============================================================
from __future__ import annotations

import streamlit as st

from services.signal_engine import TetherSignal, MagicSignal, WarehouseSignal
from ui.components import (
    section_title, data_table, alert_critical, alert_warning, alert_info,
)


def render_signals(
    tether: TetherSignal,
    magic: list[MagicSignal],
    warehouse: list[WarehouseSignal],
):
    section_title("📊 종합 시그널", "전 엔진 신호 요약")

    # ── Collect all alerts ────────────────────────────────────
    all_rows: list[list[str]] = []

    # Engine 1: Tether
    for msg in tether.alerts:
        if "🔴" in msg:
            level = "🔴 긴급"
        elif "🟢" in msg:
            level = "🟢 기회"
        else:
            level = "⚠️ 주의"
        all_rows.append([level, "테더", msg])

    if tether.action != "HOLD" and not tether.alerts:
        all_rows.append(["ℹ️ 참고", "테더", f"Action: {tether.action}"])

    # Engine 2: Magic Split
    for s in magic:
        if s.action == "SCOUT":
            all_rows.append(["🎯 스카우트", "매직스플릿", f"<b>{s.symbol}</b> — {s.reason}"])
        else:
            all_rows.append(["👀 관망", "매직스플릿", f"{s.symbol} — {s.reason}"])

    # Engine 3: Warehouse
    for s in warehouse:
        if s.status == "panic":
            all_rows.append(["🚨 패닉", "웨어하우스", s.label])
        elif s.status == "hot":
            all_rows.append(["🔥 과열", "웨어하우스", f"<b>{s.symbol}</b> — {s.label}"])
        elif s.status == "cold":
            all_rows.append(["❄️ 침체", "웨어하우스", f"<b>{s.symbol}</b> — {s.label}"])

    # ── Render table ──────────────────────────────────────────
    if all_rows:
        data_table(["등급", "엔진", "내용"], all_rows)
    else:
        alert_info("현재 발동된 신호 없음 — 시장 정상 구간")

    # ── Summary stats ─────────────────────────────────────────
    n_critical = sum(1 for r in all_rows if "긴급" in r[0] or "패닉" in r[0])
    n_scout = sum(1 for r in all_rows if "스카우트" in r[0])
    n_warning = sum(1 for r in all_rows if "과열" in r[0] or "주의" in r[0])

    cols = st.columns(4)
    cols[0].metric("총 신호", f"{len(all_rows)}건")
    cols[1].metric("🚨 긴급", f"{n_critical}건")
    cols[2].metric("🎯 스카우트", f"{n_scout}건")
    cols[3].metric("⚠️ 주의", f"{n_warning}건")
