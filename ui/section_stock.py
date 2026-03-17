# ============================================================
# GEM Protocol v3 — Section 2: 주식 탐색 (Stock Explorer)
# ============================================================
from __future__ import annotations

import streamlit as st

from services.data_fetcher import StockQuote
from services.signal_engine import MagicSignal
from services.stock_analyst import AnalysisResult
from services.index_scanner import ScreenedStock
from ui.components import (
    section_title, data_table, alert_scout, alert_info,
    verdict_badge, analysis_card_v2,
)


def render_stock_explorer(
    wl_quotes: list[StockQuote],
    magic_signals: list[MagicSignal],
    ai_results: list[AnalysisResult],
    screened: list[ScreenedStock] | None = None,
):
    section_title("🔍 주식 탐색", "종목 스크리닝 + AI Bull/Bear/Synthesis 분석")

    # ── Scout / Watch alerts ──────────────────────────────────
    scouts = [s for s in magic_signals if s.action == "SCOUT"]
    watches = [s for s in magic_signals if s.action == "WATCH"]
    for s in scouts:
        alert_scout(f"<b>{s.symbol}</b> — {s.reason}")
    for s in watches:
        alert_info(f"{s.symbol} — {s.reason}")

    # ── AI Top 5 Analysis ─────────────────────────────────────
    st.markdown("##### 🤖 AI Top 5 추천")
    st.caption("Bull Agent + Bear Agent → Synthesis Agent (Gemini)")
    st.caption(f"현재 AI 결과: {len(ai_results)}건")

    if ai_results:

        for r in ai_results:
            badge = verdict_badge(r.verdict)
            score_color = (
                "#34c759" if r.score >= 70
                else "#ff9f0a" if r.score >= 40
                else "#ff453a"
            )
            header = (
                f"{r.symbol} ({r.name}) "
                f'<span class="badge" style="background:{score_color};'
                f'color:#000;font-weight:700;">{r.score}점</span> {badge}'
            )
            analysis_card_v2(
                header,
                bull=r.bull_summary[:400] if r.bull_summary else "",
                bear=r.bear_summary[:400] if r.bear_summary else "",
                synthesis=r.synthesis or "",
                source=r.source or "ai",
            )
    else:
        alert_info("AI 분석 결과가 없습니다. `run_engines.py ai` 실행 후 새로고침(🔄) 해주세요.")

    st.markdown("---")

    # ── Watchlist Table ────────────────────────────────────────
    st.markdown("##### 📋 관심종목 현황")

    headers = ["종목", "가격", "변동", "RSI(14)", "PER", "PEG", "상태"]
    rows = []
    for q in sorted(wl_quotes, key=lambda x: x.change_pct, reverse=True):
        if q.price <= 0:
            continue
        chg_icon = "🟢" if q.change_pct > 0 else ("🔴" if q.change_pct < 0 else "⚪")
        rsi_str = f"{q.rsi_14:.0f}" if q.rsi_14 is not None else "—"
        pe_str = f"{q.forward_pe:.1f}" if q.forward_pe is not None else "—"
        peg_str = f"{q.peg_ratio:.2f}" if q.peg_ratio is not None else "—"

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
    if rows:
        data_table(headers, rows)

    # ── Screened Candidates ───────────────────────────────────
    if screened:
        with st.expander(f"📊 인덱스 스크리닝 후보 ({len(screened)}종목)", expanded=False):
            s_headers = ["종목", "가격", "RSI", "고점대비", "점수"]
            s_rows = []
            for s in screened[:15]:
                rsi_str = f"{s.rsi_14:.0f}" if s.rsi_14 is not None else "—"
                s_rows.append([
                    f"<b>{s.symbol}</b>",
                    f"${s.price:,.2f}",
                    rsi_str,
                    f"{s.drawdown_pct:+.1f}%",
                    f"{s.rule_score}",
                ])
            data_table(s_headers, s_rows)
