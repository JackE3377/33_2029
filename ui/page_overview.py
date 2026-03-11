# ============================================================
# GEM Protocol — Dashboard Page: Overview
# ============================================================
"""
Main overview dashboard showing:
  - Total asset & goal progress
  - Macro indicators (VIX, USD/KRW, etc.)
  - Engine health status (traffic lights)
  - Active alerts
  - AI daily report
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st
import plotly.graph_objects as go

from ui.components import (
    alert_banner,
    metric_grid,
    section_title,
    goal_progress,
    engine_status_indicator,
    ai_insight_card,
    metric_card,
)


def render_overview():
    """Render the main Overview tab."""

    # ---- Alert Banners (from session state) ----
    alerts = st.session_state.get("pending_alerts", [])
    for a in alerts:
        alert_banner(a.get("priority", "info"), a.get("message", ""))

    # ---- Goal Progress ----
    total_asset = st.session_state.get("total_asset_krw", 1_250_000_000)
    goal_progress(current=total_asset, target=3_300_000_000)

    # ---- Top Metrics Grid ----
    macro = st.session_state.get("macro_data", {})
    risk = st.session_state.get("risk_state", {})

    section_title("시장 현황", "실시간 매크로 지표")

    vix = macro.get("vix", 0)
    usd_krw = macro.get("usd_krw", 0)
    sp500_chg = macro.get("sp500_daily_chg_pct", 0)
    nasdaq_chg = macro.get("nasdaq_daily_chg_pct", 0)

    metric_grid([
        {
            "label": "VIX",
            "value": f"{vix:.1f}",
            "change": "레버리지 차단" if vix >= 30 else "정상",
            "direction": "down" if vix >= 30 else "up",
        },
        {
            "label": "USD/KRW",
            "value": f"₩{usd_krw:,.0f}",
            "change": "미국주식 매수 차단" if usd_krw >= 1400 else "정상",
            "direction": "down" if usd_krw >= 1400 else "up",
        },
        {
            "label": "S&P 500",
            "value": f"{sp500_chg:+.2f}%",
            "change": "일일 변동",
            "direction": "up" if sp500_chg >= 0 else "down",
        },
        {
            "label": "NASDAQ",
            "value": f"{nasdaq_chg:+.2f}%",
            "change": "일일 변동",
            "direction": "up" if nasdaq_chg >= 0 else "down",
        },
    ])

    # ---- Engine Health ----
    section_title("엔진 상태", "시스템 헬스 체크")

    col1, col2, col3 = st.columns(3)

    with col1:
        e1_status = st.session_state.get("engine1_status", {})
        status = "running" if e1_status.get("is_running") else ("paused" if e1_status.get("is_paused") else "idle")
        if e1_status.get("last_error"):
            status = "error"
        engine_status_indicator(
            "Engine 1: Tether",
            status,
            e1_status.get("last_run", ""),
        )
        metric_card(
            "김치 프리미엄",
            f"{st.session_state.get('kimchi_premium', 0):+.2f}%",
            "USDT 프리미엄 현황",
        )

    with col2:
        e2_status = st.session_state.get("engine2_status", {})
        status = "running" if e2_status.get("is_running") else ("paused" if e2_status.get("is_paused") else "idle")
        if e2_status.get("last_error"):
            status = "error"
        engine_status_indicator(
            "Engine 2: Magic Split",
            status,
            e2_status.get("last_run", ""),
        )
        metric_card(
            "활성 포지션",
            f"{st.session_state.get('active_positions', 0)}개",
            "분할매수 진행 중",
        )

    with col3:
        e3_status = st.session_state.get("engine3_status", {})
        status = "running" if e3_status.get("is_running") else ("paused" if e3_status.get("is_paused") else "idle")
        if e3_status.get("last_error"):
            status = "error"
        engine_status_indicator(
            "Engine 3: Warehouse",
            status,
            e3_status.get("last_run", ""),
        )
        metric_card(
            "리밸런싱",
            st.session_state.get("rebalance_status", "정상"),
            "포트폴리오 비중 상태",
        )

    # ---- Risk State ----
    if risk.get("circuit_breaker_active"):
        alert_banner("critical", "⚡ Circuit Breaker 작동 중 — 모든 엔진 매수 차단")
    if risk.get("black_swan_active"):
        alert_banner("critical", "🦢 Black Swan Protocol 발동 — 전 포지션 방어 태세")

    # ---- Portfolio Chart ----
    section_title("자산 추이", "일별 총 자산 변화")

    perf_data = st.session_state.get("performance_history", [])
    if perf_data:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[p["date"] for p in perf_data],
            y=[p["total_asset_krw"] / 1e8 for p in perf_data],
            mode="lines",
            line=dict(color="#0071e3", width=2.5),
            fill="tozeroy",
            fillcolor="rgba(0, 113, 227, 0.06)",
            name="총 자산 (억원)",
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
            height=300,
            font=dict(family="Inter, -apple-system, sans-serif"),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("자산 추이 데이터가 수집되면 차트가 표시됩니다.")

    # ---- AI Daily Report ----
    section_title("AI 데일리 리포트", "CrewAI 에이전트 분석 결과")
    daily_report = st.session_state.get("daily_report", "")
    ai_insight_card("오늘의 종합 분석", daily_report or "아직 분석 데이터가 없습니다. 엔진을 시작하면 AI 리포트가 생성됩니다.")
