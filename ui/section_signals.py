# ============================================================
# GEM Protocol v3 — Section 1: 종합 시그널 (6-Card Grid)
# ============================================================
from __future__ import annotations

import streamlit as st

from services.signal_engine import (
    TetherSignal, DollarSignal, FXSplitSignal, WarehouseSignal,
)
from services.stock_analyst import AnalysisResult
from services.data_fetcher import CryptoQuote, DXYData, FXIntraday
from ui.components import signal_card_html, section_title, verdict_badge, analysis_card


def _html(s: str):
    st.markdown(s.strip(), unsafe_allow_html=True)


# ── Card builders ────────────────────────────────────────────

def _card_fx_split(sig: FXSplitSignal, currency_label: str) -> dict:
    icon = "💵" if sig.currency == "USD" else "💴"
    title = f"{currency_label} 분할매매"
    theme = "sc-dollar" if sig.currency == "USD" else "sc-yen"

    if not sig.market_open:
        return dict(icon=icon, title=title, label="시장 휴장", detail="", urgency=0, theme=theme)

    # Build detail with entry score
    detail = f"진입점수 {sig.entry_score}/100"
    if sig.entry_rationale and sig.entry_rationale != "특이사항 없음":
        detail += f" · {sig.entry_rationale}"

    return dict(
        icon=icon, title=title, theme=theme,
        urgency=sig.urgency,
        label=sig.label,
        detail=detail,
    )


def _card_tether(
    tether: TetherSignal,
    crypto: CryptoQuote | None,
) -> dict:
    icon, title, theme = "💰", "테더 김프/역프", "sc-tether"
    if crypto is None:
        return dict(icon=icon, title=title, label="데이터 없음", detail="", urgency=0, theme=theme)

    prem = crypto.kimchi_premium_pct

    if prem >= 2.0:
        urgency = 3 if prem >= 3.0 else 2
        return dict(
            icon=icon, title=title, theme=theme, urgency=urgency,
            label=f"테더 → 달러 전환 (김프 {prem:+.2f}%)",
            detail=f"김프 {prem:.1f}% — USDT 매도 후 달러 매수",
        )
    elif prem <= -0.5:
        urgency = 3 if prem <= -2.0 else 2
        return dict(
            icon=icon, title=title, theme=theme, urgency=urgency,
            label=f"달러 → 테더 전환 (역프 {prem:+.2f}%)",
            detail=f"역프 {prem:.1f}% — 달러 매도 후 USDT 매수",
        )
    else:
        return dict(
            icon=icon, title=title, theme=theme, urgency=0,
            label=f"관망 (김프 {prem:+.2f}%)",
            detail=f"USDT ₩{crypto.price_krw:,.0f}",
        )


def _card_dxy(dollar: DollarSignal | None, dxy: DXYData | None) -> dict:
    icon, title, theme = "📊", "달러인덱스(DXY)", "sc-dollar"
    if dollar is None:
        return dict(icon=icon, title=title, label="데이터 없음", detail="", urgency=0, theme=theme)

    detail = dollar.detail
    if dxy and dxy.bounce_score:
        detail += f" · 반등 {dxy.bounce_score}/100"

    return dict(
        icon=icon, title=title, theme=theme,
        urgency=dollar.urgency,
        label=dollar.label,
        detail=detail,
    )


def _card_stock_buy(ai_results: list[AnalysisResult] | None) -> dict:
    icon, title, theme = "🚀", "매수의견 종목", "sc-stock"
    if not ai_results:
        return dict(icon=icon, title=title, label="분석 대기", detail="", urgency=0, theme=theme)
    buy_picks = [r for r in ai_results if r.verdict == "BUY"]
    if not buy_picks:
        return dict(icon=icon, title=title, label="BUY 종목 없음", detail="관망 구간", urgency=0, theme=theme)
    names = ", ".join(r.symbol for r in buy_picks[:3])
    extra = f" 외 {len(buy_picks)-3}종목" if len(buy_picks) > 3 else ""
    best = buy_picks[0]
    return dict(
        icon=icon, title=title, theme=theme, urgency=2,
        label=f"BUY: {names}{extra}",
        detail=f"Top: {best.symbol} {best.score}점 — {(best.synthesis or best.bull_summary)[:80]}",
    )


def _card_laa_summary(wh_signals: list[WarehouseSignal] | None) -> dict:
    icon, title, theme = "🏛️", "LAA 리밸런싱", "sc-rebal"
    if not wh_signals:
        return dict(icon=icon, title=title, label="Warehouse 탭에서 확인", detail="", urgency=0, theme=theme)

    panic = [s for s in wh_signals if s.status == "panic"]
    hot = [s for s in wh_signals if s.status == "hot"]
    cold = [s for s in wh_signals if s.status == "cold"]
    mom_off = [s for s in wh_signals if s.status == "momentum_off"]

    if panic:
        return dict(icon=icon, title=title, theme=theme, urgency=3,
                    label="패닉 리밸런싱 검토", detail=panic[0].label)
    parts = []
    if mom_off:
        parts.append(f"모멘텀⚠️: {', '.join(s.symbol for s in mom_off)}")
    if hot:
        parts.append(f"과열: {', '.join(s.symbol for s in hot)}")
    if cold:
        parts.append(f"침체: {', '.join(s.symbol for s in cold)}")
    if parts:
        return dict(icon=icon, title=title, theme=theme, urgency=2,
                    label="리밸런싱 필요", detail=" · ".join(parts))
    return dict(icon=icon, title=title, theme=theme, urgency=0,
                label="정상 — 리밸런싱 불필요", detail="모든 자산 정상 범위")


# ── Main Render ──────────────────────────────────────────────

def render_signals(
    tether: TetherSignal,
    crypto: CryptoQuote | None = None,
    dxy: DXYData | None = None,
    dollar: DollarSignal | None = None,
    usd_split: FXSplitSignal | None = None,
    jpy_split: FXSplitSignal | None = None,
    wh_signals: list[WarehouseSignal] | None = None,
    ai_results: list[AnalysisResult] | None = None,
):
    section_title("신호등 대시보드", "GO / WAIT 상태를 즉시 확인하세요")

    cards = [
        _card_fx_split(usd_split, "달러") if usd_split else
            dict(icon="💵", title="달러 분할매매", label="데이터 없음", detail="", urgency=0, theme="sc-dollar"),
        _card_fx_split(jpy_split, "엔화") if jpy_split else
            dict(icon="💴", title="엔화 분할매매", label="데이터 없음", detail="", urgency=0, theme="sc-yen"),
        _card_tether(tether, crypto),
        _card_dxy(dollar, dxy),
        _card_stock_buy(ai_results),
        _card_laa_summary(wh_signals),
    ]

    # Sort by urgency descending
    cards.sort(key=lambda c: c["urgency"], reverse=True)

    grid_html = '<div class="sc-grid">'
    for c in cards:
        grid_html += signal_card_html(**c)
    grid_html += '</div>'
    _html(grid_html)

    # ── FX Split Level Details ────────────────────────────────
    for fx_sig, label in [(usd_split, "💵 달러"), (jpy_split, "💴 엔화")]:
        if fx_sig and fx_sig.market_open and fx_sig.current > 0:
            with st.expander(f"{label} 분할매매 레벨 상세", expanded=False):
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("현재가", f"₩{fx_sig.current:,.1f}")
                with c2:
                    score_delta = fx_sig.entry_score - 50
                    st.metric("진입점수", f"{fx_sig.entry_score}/100",
                              delta=f"{score_delta:+d}" if score_delta != 0 else None)
                with c3:
                    rsi_str = f"{fx_sig.rsi_5m:.0f}" if fx_sig.rsi_5m is not None else "—"
                    st.metric("RSI(5분)", rsi_str)
                with c4:
                    st.metric("지지/저항", f"₩{fx_sig.support:,.1f} / ₩{fx_sig.resistance:,.1f}")

                if fx_sig.entry_rationale:
                    st.caption(f"📐 진입 근거: {fx_sig.entry_rationale}")

                buy_col, sell_col = st.columns(2)
                with buy_col:
                    st.markdown("**📥 분할 매수 레벨** (지지선 기반)")
                    for i, lvl in enumerate(fx_sig.buy_levels, 1):
                        st.markdown(f"- {i}차: **₩{lvl:,.1f}**")
                with sell_col:
                    st.markdown("**📤 분할 매도 레벨** (저항선 기반)")
                    for i, lvl in enumerate(fx_sig.sell_levels, 1):
                        st.markdown(f"- {i}차: **₩{lvl:,.1f}**")

    # ── BUY Stock Detail ──────────────────────────────────────
    buy_picks = [r for r in (ai_results or []) if r.verdict == "BUY"]
    if buy_picks:
        with st.expander(f"🚀 BUY 종목 상세 ({len(buy_picks)}종목)", expanded=False):
            for r in buy_picks:
                badge = verdict_badge(r.verdict)
                score_color = "#34c759" if r.score >= 70 else ("#ff9f0a" if r.score >= 40 else "#ff453a")
                header = (
                    f"{r.symbol} ({r.name}) "
                    f'<span class="badge" style="background:{score_color};'
                    f'color:#000;font-weight:700;">{r.score}점</span> {badge}'
                )
                body_parts = []
                if r.bull_summary:
                    body_parts.append(f"<b>🟢 Bull:</b> {r.bull_summary[:300]}")
                if r.bear_summary:
                    body_parts.append(f"<b>🔴 Bear:</b> {r.bear_summary[:300]}")
                if r.synthesis:
                    body_parts.append(f"<b>⚖️ 종합:</b> {r.synthesis}")
                analysis_card(header, "\n".join(body_parts))
