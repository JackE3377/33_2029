# ============================================================
# GEM Protocol — Dashboard Page: Settings & Control Panel
# ============================================================
from __future__ import annotations

import streamlit as st

from ui.components import (
    section_title,
    metric_grid,
    alert_banner,
    styled_table,
    badge,
    engine_status_indicator,
)


def render_settings():
    """Render the Settings & Control Panel tab."""

    section_title("제어판", "시스템 설정 및 엔진 제어")

    # ---- Engine Controls ----
    section_title("엔진 제어", "일시정지 / 재개")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown('<div class="gem-card"><div class="gem-card-header">Engine 1: Tether</div></div>', unsafe_allow_html=True)
        e1_col1, e1_col2 = st.columns(2)
        with e1_col1:
            if st.button("⏸ 일시정지", key="pause_e1"):
                st.session_state["engine1_paused"] = True
                st.success("Engine 1 일시정지됨")
        with e1_col2:
            if st.button("▶ 재개", key="resume_e1"):
                st.session_state["engine1_paused"] = False
                st.success("Engine 1 재개됨")

    with col2:
        st.markdown('<div class="gem-card"><div class="gem-card-header">Engine 2: Magic Split</div></div>', unsafe_allow_html=True)
        e2_col1, e2_col2 = st.columns(2)
        with e2_col1:
            if st.button("⏸ 일시정지", key="pause_e2"):
                st.session_state["engine2_paused"] = True
                st.success("Engine 2 일시정지됨")
        with e2_col2:
            if st.button("▶ 재개", key="resume_e2"):
                st.session_state["engine2_paused"] = False
                st.success("Engine 2 재개됨")

    with col3:
        st.markdown('<div class="gem-card"><div class="gem-card-header">Engine 3: Warehouse</div></div>', unsafe_allow_html=True)
        e3_col1, e3_col2 = st.columns(2)
        with e3_col1:
            if st.button("⏸ 일시정지", key="pause_e3"):
                st.session_state["engine3_paused"] = True
                st.success("Engine 3 일시정지됨")
        with e3_col2:
            if st.button("▶ 재개", key="resume_e3"):
                st.session_state["engine3_paused"] = False
                st.success("Engine 3 재개됨")

    st.divider()

    # ---- Emergency Controls ----
    section_title("비상 제어", "")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
        if st.button("🛑 전 엔진 즉시 정지", key="stop_all"):
            st.session_state["engine1_paused"] = True
            st.session_state["engine2_paused"] = True
            st.session_state["engine3_paused"] = True
            st.warning("모든 엔진이 정지되었습니다.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_b:
        if st.button("🟢 전 엔진 재개", key="resume_all"):
            st.session_state["engine1_paused"] = False
            st.session_state["engine2_paused"] = False
            st.session_state["engine3_paused"] = False
            st.success("모든 엔진이 재개되었습니다.")

    st.divider()

    # ---- Trading Mode ----
    section_title("트레이딩 모드", "")

    mode = st.session_state.get("trading_mode", "paper")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if mode == "paper":
            alert_banner("info", "📋 현재 모드: PAPER (시뮬레이션) — 실제 주문 없음")
        else:
            alert_banner("warning", "⚡ 현재 모드: LIVE — 실제 매매 실행 중!")

    with col_m2:
        new_mode = st.selectbox("모드 변경", ["paper", "live"], key="mode_select",
                                index=0 if mode == "paper" else 1)
        if new_mode != mode:
            if new_mode == "live":
                st.warning("⚠️ LIVE 모드 전환 시 실제 주문이 실행됩니다. 신중히 판단하세요.")
                if st.button("LIVE 모드 확인", key="confirm_live"):
                    st.session_state["trading_mode"] = "live"
                    st.rerun()
            else:
                st.session_state["trading_mode"] = "paper"
                st.rerun()

    st.divider()

    # ---- System Info ----
    section_title("시스템 정보", "")

    llm_spend = st.session_state.get("llm_monthly_spend", 0)
    llm_budget = st.session_state.get("llm_budget", 50.0)

    metric_grid([
        {"label": "LLM 월간 사용량", "value": f"${llm_spend:.2f}", "change": f"예산: ${llm_budget:.0f}"},
        {"label": "DB 크기", "value": st.session_state.get("db_size", "N/A")},
        {"label": "로그 크기", "value": st.session_state.get("log_size", "N/A")},
        {"label": "마지막 매크로 업데이트", "value": st.session_state.get("last_macro_update", "N/A")},
    ])

    # ---- Alert History ----
    section_title("알림 이력", "최근 20건")

    alert_history = st.session_state.get("alert_history", [])
    if alert_history:
        rows = []
        for a in alert_history[:20]:
            priority_badge = {
                "critical": badge("CRITICAL", "red"),
                "warning": badge("WARNING", "orange"),
                "info": badge("INFO", "blue"),
            }.get(a.get("priority", "info"), badge("INFO", "blue"))

            ack = badge("확인됨", "green") if a.get("acknowledged") else badge("미확인", "red")

            rows.append([
                a.get("timestamp", ""),
                priority_badge,
                a.get("title", ""),
                ack,
            ])

        styled_table(
            headers=["시간", "중요도", "제목", "확인"],
            rows=rows,
        )
    else:
        st.info("알림 이력이 없습니다.")
