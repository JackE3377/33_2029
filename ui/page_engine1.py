# ============================================================
# GEM Protocol — Dashboard Page: Engine 1 (Tether)
# ============================================================
from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go

from ui.components import (
    section_title,
    metric_grid,
    metric_card,
    alert_banner,
    ai_insight_card,
    styled_table,
    badge,
)


def render_engine1():
    """Render the Engine 1 (Tether System) tab."""

    section_title("Engine 1: Tether System", "USDT 김치 프리미엄 차익거래 봇")

    # ---- Current Status ----
    tether_data = st.session_state.get("tether_data", {})
    raw_premium = tether_data.get("raw_premium_pct", 0)
    net_premium = tether_data.get("net_premium_pct", 0)
    action = tether_data.get("action", "hold")
    usd_krw = tether_data.get("usd_krw", 0)
    price_krw = tether_data.get("price_krw", 0)

    # Action alert
    if action == "sell":
        alert_banner("warning", f"💰 매도 시그널: 실질 프리미엄 {net_premium:+.2f}% — USDT 매도 추천", "🟢")
    elif action == "buy":
        alert_banner("info", f"🛒 매수 시그널: 역프리미엄 {raw_premium:+.2f}% — USDT 매수 기회")

    # Metrics
    metric_grid([
        {
            "label": "원시 프리미엄",
            "value": f"{raw_premium:+.2f}%",
            "change": "Bithumb vs 글로벌",
            "direction": "up" if raw_premium > 0 else "down",
        },
        {
            "label": "실질 프리미엄",
            "value": f"{net_premium:+.2f}%",
            "change": "수수료·슬리피지 차감 후",
            "direction": "up" if net_premium > 0 else "down",
        },
        {
            "label": "USDT/KRW",
            "value": f"₩{price_krw:,.0f}",
            "change": "빗썸 현재가",
            "direction": "",
        },
        {
            "label": "USD/KRW",
            "value": f"₩{usd_krw:,.0f}",
            "change": "기준 환율",
            "direction": "",
        },
    ])

    # ---- Fee Breakdown ----
    col1, col2 = st.columns(2)
    with col1:
        section_title("수수료 구조", "")
        styled_table(
            headers=["항목", "비율/금액"],
            rows=[
                ["Bithumb 거래 수수료", "0.25%"],
                ["슬리피지 (예상)", "0.15%"],
                ["출금 수수료", "1 USDT"],
                ["합계 (고정비)", "~0.40%"],
            ],
        )

    with col2:
        section_title("수익 시뮬레이션", "")
        # Simple calculator
        trade_amount = st.number_input("USDT 수량", value=10000, step=1000, key="tether_qty")
        if raw_premium > 0:
            gross_profit_krw = trade_amount * usd_krw * (raw_premium / 100)
            fee_cost_krw = trade_amount * usd_krw * 0.005 + usd_krw  # fees + withdrawal
            net_profit_krw = gross_profit_krw - fee_cost_krw
            metric_card(
                "예상 순이익",
                f"₩{net_profit_krw:,.0f}",
                f"수익률: {(net_profit_krw / (trade_amount * usd_krw)) * 100:.2f}%",
                css_class="positive" if net_profit_krw > 0 else "negative",
            )
        else:
            metric_card("예상 순이익", "해당없음", "프리미엄이 음수입니다")

    # ---- Premium History Chart ----
    section_title("프리미엄 추이", "시간별 김치 프리미엄 변화")

    premium_history = st.session_state.get("premium_history", [])
    if premium_history:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[p["time"] for p in premium_history],
            y=[p["premium"] for p in premium_history],
            mode="lines",
            line=dict(color="#ff9500", width=2),
            fill="tozeroy",
            fillcolor="rgba(255, 149, 0, 0.08)",
        ))
        fig.add_hline(y=3.0, line_dash="dash", line_color="#34c759", annotation_text="매도 임계")
        fig.add_hline(y=-1.0, line_dash="dash", line_color="#ff3b30", annotation_text="매수 임계")
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            height=280,
            yaxis_title="프리미엄 (%)",
            font=dict(family="Inter, -apple-system, sans-serif"),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("프리미엄 히스토리 데이터 수집 중...")

    # ---- Recent Trades ----
    section_title("최근 거래", "")
    trades = st.session_state.get("tether_trades", [])
    if trades:
        styled_table(
            headers=["시간", "액션", "수량", "가격", "상태"],
            rows=[
                [
                    t.get("time", ""),
                    badge(t.get("action", ""), "green" if t.get("action") == "SELL" else "blue"),
                    f"{t.get('quantity', 0):,.0f} USDT",
                    f"₩{t.get('price', 0):,.0f}",
                    badge(t.get("status", ""), "purple"),
                ]
                for t in trades[:10]
            ],
        )
    else:
        st.info("아직 거래 기록이 없습니다.")

    # ---- AI Insight ----
    ai_insight_card(
        "테더 봇 AI 분석",
        st.session_state.get("tether_ai_analysis", "분석 데이터 대기 중..."),
    )
