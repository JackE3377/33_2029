# ============================================================
# GEM Protocol v2 — Section 2: Magic Split + AI Top 5
# ============================================================
from __future__ import annotations

import streamlit as st

from services.data_fetcher import StockQuote
from services.signal_engine import MagicSignal
from services.stock_analyst import AnalysisResult
from ui.components import (
    section_title, data_table, alert_scout, alert_info,
    verdict_badge, analysis_card,
)


def render_magic(
    quotes: list[StockQuote],
    magic_signals: list[MagicSignal],
    ai_results: list[AnalysisResult],
):
    section_title("🎯 Magic Split 스크리닝", "관심종목 밸류에이션 + AI 추천 Top 5")

    # ── Scout alerts ──────────────────────────────────────────
    scouts = [s for s in magic_signals if s.action == "SCOUT"]
    watches = [s for s in magic_signals if s.action == "WATCH"]

    for s in scouts:
        alert_scout(f"<b>{s.symbol}</b> — {s.reason}")
    for s in watches:
        alert_info(f"{s.symbol} — {s.reason}")

    # ── Watchlist table ────────────────────────────────────────
    st.markdown("##### 📋 관심종목 현황")

    headers = ["종목", "가격", "변동", "RSI(14)", "PER", "PEG", "상태"]
    rows = []
    for q in sorted(quotes, key=lambda x: x.change_pct, reverse=True):
        if q.price <= 0:
            continue
        chg_icon = "🟢" if q.change_pct > 0 else ("🔴" if q.change_pct < 0 else "⚪")
        rsi_str = f"{q.rsi_14:.0f}" if q.rsi_14 is not None else "—"
        pe_str = f"{q.forward_pe:.1f}" if q.forward_pe is not None else "—"
        peg_str = f"{q.peg_ratio:.2f}" if q.peg_ratio is not None else "—"

        # Determine status
        status = "—"
        for s in magic_signals:
            if s.symbol == q.symbol:
                status = "🎯 SCOUT" if s.action == "SCOUT" else "👀 WATCH"
                break

        rows.append([
            f"<b>{q.symbol}</b><br><span style='font-size:11px;color:#888;'>{q.name}</span>",
            f"${q.price:,.2f}",
            f"{chg_icon} {q.change_pct:+.2f}%",
            rsi_str,
            pe_str,
            peg_str,
            status,
        ])

    data_table(headers, rows)

    # ── AI Top 5 ──────────────────────────────────────────────
    if ai_results:
        st.markdown("---")
        st.markdown("##### 🤖 AI Top 5 추천")
        st.caption("Bull Agent + Bear Agent → Synthesis Agent (Gemini 2.0 Flash)")

        for r in ai_results:
            badge = verdict_badge(r.verdict)
            score_color = "#34c759" if r.score >= 70 else ("#ff9f0a" if r.score >= 40 else "#ff453a")
            header = (
                f"{r.symbol} ({r.name}) "
                f'<span class="badge" style="background:{score_color};color:#000;font-weight:700;">'
                f'{r.score}점</span> {badge}'
            )
            body_parts = []
            if r.bull_summary:
                body_parts.append(f"<b>🟢 Bull:</b> {r.bull_summary[:300]}")
            if r.bear_summary:
                body_parts.append(f"<b>🔴 Bear:</b> {r.bear_summary[:300]}")
            if r.synthesis:
                body_parts.append(f"<b>⚖️ 종합:</b> {r.synthesis}")
            if r.source == "rule":
                body_parts.append("<i>📊 규칙 기반 분석 (AI 비활성)</i>")

            analysis_card(header, "\n".join(body_parts))
