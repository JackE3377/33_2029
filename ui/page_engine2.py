# ============================================================
# GEM Protocol — Dashboard Page: Engine 2 (Magic Split)
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


def render_engine2():
    """Render the Engine 2 (Magic Split) tab."""

    section_title("Engine 2: Magic Split", "단기 분할매수/매도 트레이딩 시스템")

    # ---- Active Signals ----
    signals = st.session_state.get("magic_signals", [])
    for s in signals:
        if s.get("action", "").startswith("sell_stop"):
            alert_banner("critical", f"🛑 {s['symbol']}: 손절 시그널 — {s['reason']}")
        elif s.get("action", "").startswith("sell_profit"):
            alert_banner("warning", f"💰 {s['symbol']}: 익절 시그널 — {s['reason']}", "🟢")
        elif s.get("action", "").startswith("buy"):
            alert_banner("info", f"🛒 {s['symbol']}: 매수 시그널 — {s['reason']}")

    # ---- Summary Metrics ----
    positions = st.session_state.get("magic_positions", [])
    total_positions = len(positions)
    profitable = sum(1 for p in positions if p.get("pnl_pct", 0) > 0)
    losing = sum(1 for p in positions if p.get("pnl_pct", 0) < 0)

    metric_grid([
        {"label": "총 포지션", "value": str(total_positions), "change": "활성 종목 수"},
        {"label": "수익 종목", "value": str(profitable), "change": "PnL > 0", "direction": "up"},
        {"label": "손실 종목", "value": str(losing), "change": "PnL < 0", "direction": "down"},
        {
            "label": "평균 PnL",
            "value": f"{sum(p.get('pnl_pct', 0) for p in positions) / max(total_positions, 1):+.1f}%",
            "direction": "up" if sum(p.get('pnl_pct', 0) for p in positions) > 0 else "down",
        },
    ])

    # ---- Positions Table ----
    section_title("현재 포지션", "Magic Split CSV 연동 데이터")

    if positions:
        rows = []
        for p in positions:
            pnl = p.get("pnl_pct", 0)
            pnl_badge = badge(f"{pnl:+.1f}%", "green" if pnl > 0 else "red")
            split_badge = badge(f"{p.get('split_count', 0)}/{3}", "blue")

            rows.append([
                p.get("symbol", ""),
                p.get("name", ""),
                f"{p.get('quantity', 0):,.0f}",
                f"${p.get('avg_price', 0):,.2f}",
                f"${p.get('current_price', 0):,.2f}",
                pnl_badge,
                split_badge,
                f"${p.get('target_buy_price', 0):,.2f}",
                f"${p.get('target_sell_price', 0):,.2f}",
            ])

        styled_table(
            headers=["종목코드", "종목명", "수량", "평균단가", "현재가", "수익률", "분할횟수", "목표매수가", "목표매도가"],
            rows=rows,
        )
    else:
        st.info("Magic Split CSV 파일에서 포지션을 로드 중... 파일 경로를 확인하세요.")

    # ---- Screening Filters ----
    section_title("퀀트 스크리닝 필터", "타겟 발굴 기준")

    col1, col2 = st.columns(2)
    with col1:
        styled_table(
            headers=["필터", "기준값", "상태"],
            rows=[
                ["Forward PE", "≤ 15.0", badge("Active", "green")],
                ["PEG Ratio", "≤ 1.5", badge("Active", "green")],
                ["FCF (Free Cash Flow)", "> 0 (흑자)", badge("Active", "green")],
                ["Debt/Equity", "< 200%", badge("Active", "green")],
                ["RSI(14) 진입", "< 30", badge("Active", "green")],
            ],
        )

    with col2:
        styled_table(
            headers=["매매 규칙", "설정값"],
            rows=[
                ["1차 진입 비중", "자본의 1~5%"],
                ["2차 분할매수", "평단 대비 -5%"],
                ["3차 분할매수", "평단 대비 -10%"],
                ["익절 기준", "평단 대비 +3~5%"],
                ["손절 기준", "평단 대비 -20%"],
                ["최대 분할 횟수", "3회"],
            ],
        )

    # ---- RSI Gauge Chart ----
    section_title("포지션별 RSI 현황", "")

    rsi_data = st.session_state.get("position_rsi", {})
    if rsi_data:
        symbols = list(rsi_data.keys())[:10]
        rsi_values = [rsi_data[s] for s in symbols]

        fig = go.Figure(go.Bar(
            x=symbols,
            y=rsi_values,
            marker_color=[
                "#ff3b30" if v < 30 else "#34c759" if v > 70 else "#0071e3"
                for v in rsi_values
            ],
        ))
        fig.add_hline(y=30, line_dash="dash", line_color="#ff3b30", annotation_text="과매도")
        fig.add_hline(y=70, line_dash="dash", line_color="#34c759", annotation_text="과매수")
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            height=280,
            yaxis_range=[0, 100],
            font=dict(family="Inter, -apple-system, sans-serif"),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("RSI 데이터 수집 중...")

    # ---- AI Advice ----
    ai_insight_card(
        "분할매매 AI 전략 조언",
        st.session_state.get("magic_ai_advice", "포지션 분석 중..."),
    )
