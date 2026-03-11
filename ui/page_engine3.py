# ============================================================
# GEM Protocol — Dashboard Page: Engine 3 (Warehouse)
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


def render_engine3():
    """Render the Engine 3 (Warehouse / Dynamic Rebalancing) tab."""

    section_title("Engine 3: Warehouse", "LAA/올웨더 기반 장기 코어 자산 동적 리밸런싱")

    # ---- Rebalance Alerts ----
    warehouse_data = st.session_state.get("warehouse_data", {})
    triggers = warehouse_data.get("trigger_reasons", [])

    if warehouse_data.get("should_rebalance"):
        alert_banner("warning", "🔄 리밸런싱 트리거 발동 — 포트폴리오 조정 필요")
        for t in triggers:
            alert_banner("info", f"📌 {t}")

    # ---- Allocation Doughnut Chart ----
    col1, col2 = st.columns([3, 2])

    actions = warehouse_data.get("actions", [])

    with col1:
        section_title("현재 vs 목표 배분", "")

        if actions:
            symbols = [a["symbol"] for a in actions]
            current_weights = [float(a["current"].replace("%", "")) for a in actions]
            target_weights = [float(a["target"].replace("%", "")) for a in actions]

            fig = go.Figure()

            # Target (outer ring)
            fig.add_trace(go.Pie(
                labels=symbols,
                values=target_weights,
                hole=0.65,
                name="목표",
                marker=dict(colors=[
                    "#0071e3", "#5ac8fa", "#34c759", "#ff9500", "#af52de", "#ff3b30"
                ]),
                textinfo="label+percent",
                textposition="outside",
                domain=dict(x=[0, 0.48]),
            ))

            # Current (inner ring)
            fig.add_trace(go.Pie(
                labels=symbols,
                values=current_weights,
                hole=0.65,
                name="현재",
                marker=dict(colors=[
                    "#4da3ff", "#8dd8fc", "#6ddc8c", "#ffb84d", "#cc85e8", "#ff6b6b"
                ]),
                textinfo="label+percent",
                textposition="outside",
                domain=dict(x=[0.52, 1]),
            ))

            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=30, b=0),
                height=350,
                font=dict(family="Inter, -apple-system, sans-serif"),
                showlegend=False,
                annotations=[
                    dict(text="목표", x=0.18, y=0.5, font_size=14, showarrow=False),
                    dict(text="현재", x=0.82, y=0.5, font_size=14, showarrow=False),
                ],
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("배분 데이터 로딩 중...")

    with col2:
        section_title("리밸런싱 트리거 조건", "")
        styled_table(
            headers=["조건", "임계값", "상태"],
            rows=[
                ["비중 이탈", "±5%p", badge("상시감시", "blue")],
                ["주간 RSI 과매수", "> 70", badge("상시감시", "blue")],
                ["주간 RSI 과매도", "< 30", badge("상시감시", "blue")],
                ["NASDAQ 일일 폭락", "≤ -3%", badge("상시감시", "blue")],
            ],
        )

        # Tax impact note
        st.markdown(
            '<div class="gem-card" style="margin-top:16px;">'
            '<div class="gem-card-header">💰 세금 고려</div>'
            '<div style="font-size:13px;color:var(--apple-text-secondary);line-height:1.6;">'
            '미국주식 양도세 <strong>22%</strong> 적용<br>'
            '매도 시 세후 수익률 기반으로 판단<br>'
            '가능한 경우 세금 손실 수확(Tax-Loss Harvesting) 적용'
            '</div></div>',
            unsafe_allow_html=True,
        )

    # ---- Rebalance Actions Table ----
    section_title("리밸런싱 액션", "개별 자산 조정 계획")

    if actions:
        rows = []
        for a in actions:
            action_text = a.get("action", "hold")
            if action_text == "buy":
                action_badge = badge("매수", "green")
            elif action_text == "sell":
                action_badge = badge("매도", "red")
            else:
                action_badge = badge("유지", "blue")

            deviation = a.get("deviation", "0")

            rows.append([
                a.get("symbol", ""),
                a.get("current", ""),
                a.get("target", ""),
                deviation,
                action_badge,
                a.get("reason", ""),
            ])

        styled_table(
            headers=["자산", "현재 비중", "목표 비중", "편차", "액션", "사유"],
            rows=rows,
        )
    else:
        st.info("리밸런싱 데이터 로딩 중...")

    # ---- Performance Metrics ----
    section_title("성과 지표", "장기 포트폴리오 성과")

    perf = st.session_state.get("warehouse_performance", {})
    metric_grid([
        {"label": "누적 수익률", "value": f"{perf.get('cumulative_return', 0):+.1f}%", "direction": "up" if perf.get('cumulative_return', 0) > 0 else "down"},
        {"label": "MDD", "value": f"{perf.get('max_drawdown', 0):.1f}%", "direction": "down"},
        {"label": "Sharpe Ratio", "value": f"{perf.get('sharpe_ratio', 0):.2f}"},
        {"label": "연환산 수익률", "value": f"{perf.get('annualized_return', 0):+.1f}%", "direction": "up" if perf.get('annualized_return', 0) > 0 else "down"},
    ])

    # ---- AI Insight ----
    ai_insight_card(
        "리밸런싱 AI 분석",
        st.session_state.get("warehouse_ai_analysis", "분석 데이터 대기 중..."),
    )
