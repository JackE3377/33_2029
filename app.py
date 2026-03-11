# ============================================================
# GEM Protocol — Main Streamlit Application Entry Point
# ============================================================
"""
streamlit run app.py

This is the main entry point for the GEM Protocol dashboard.
Integrates all UI pages, CSS injection, authentication,
scheduler, and state management.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

# Must be the first Streamlit command
st.set_page_config(
    page_title="GEM Protocol",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from core.config import get_settings
from core.logger import setup_logging, get_logger
from ui.apple_css import APPLE_CSS
from ui.auth import check_auth
from ui.page_overview import render_overview
from ui.page_engine1 import render_engine1
from ui.page_engine2 import render_engine2
from ui.page_engine3 import render_engine3
from ui.page_settings import render_settings

# ---------- Init ----------

# Setup logging (once)
if "logging_init" not in st.session_state:
    setup_logging()
    st.session_state["logging_init"] = True

logger = get_logger("app")

# Inject Apple CSS
st.markdown(APPLE_CSS, unsafe_allow_html=True)

# ---------- Authentication Gate ----------
if not check_auth():
    st.stop()

# ---------- Initial Data Load (DB에서 최신 결과 로드, 없으면 실시간 조회) ----------
if "data_loaded" not in st.session_state:
    st.session_state["data_loaded"] = True
    st.session_state["trading_mode"] = get_settings().trading_mode.value
    _load_latest_from_db()
    # DB에 데이터가 없으면 실시간 조회 (Streamlit Cloud 등)
    if "macro_data" not in st.session_state:
        try:
            from services.data_fetcher import DataFetcher
            macro = DataFetcher.get_macro()
            st.session_state["macro_data"] = {
                "vix": macro.vix, "usd_krw": macro.usd_krw,
                "sp500_daily_chg_pct": macro.sp500_daily_chg_pct,
                "nasdaq_daily_chg_pct": macro.nasdaq_daily_chg_pct,
                "fed_funds_rate": macro.fed_funds_rate,
            }
            crypto = DataFetcher.get_usdt_premium(macro.usd_krw)
            st.session_state["kimchi_premium"] = crypto.kimchi_premium_pct
            st.session_state["tether_data"] = {
                "raw_premium_pct": crypto.kimchi_premium_pct,
                "net_premium_pct": crypto.kimchi_premium_pct - 0.40,
                "action": "hold", "usd_krw": macro.usd_krw,
                "price_krw": crypto.price_krw,
            }
        except Exception:
            pass

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown(
        '<div style="text-align:center;padding:20px 0;">'
        '<div style="font-size:32px;">💎</div>'
        '<div style="font-size:18px;font-weight:700;margin-top:8px;letter-spacing:-0.01em;">GEM Protocol</div>'
        '<div style="font-size:12px;color:var(--apple-text-tertiary);margin-top:4px;">AI Asset Management System</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # Trading mode indicator
    mode = st.session_state.get("trading_mode", "paper")
    mode_color = "#34c759" if mode == "paper" else "#ff3b30"
    mode_label = "PAPER" if mode == "paper" else "LIVE"
    st.markdown(
        f'<div style="text-align:center;padding:8px;background:{mode_color}22;'
        f'border-radius:8px;font-size:12px;font-weight:600;color:{mode_color};">'
        f'● {mode_label} MODE</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # Refresh data from DB
    if st.button("🔄 새로고침 (DB에서 최신 데이터)", use_container_width=True, key="refresh_db"):
        _load_latest_from_db()
        st.success("최신 데이터 로드 완료!")
        st.rerun()

    # Manual engine run
    if st.button("▶ 수동 엔진 실행 (전체)", use_container_width=True, key="manual_run"):
        with st.spinner("엔진을 실행하고 있습니다..."):
            _run_engines_manual()
        st.success("실행 완료! 결과가 DB에 저장되었습니다.")
        _load_latest_from_db()
        st.rerun()

    # Last update time
    last_ts = st.session_state.get("last_engine_run", "")
    if last_ts:
        st.caption(f"마지막 업데이트: {last_ts}")

    st.divider()
    st.caption(f"v1.0.0 · {mode_label} Mode")
    if st.button("🚪 로그아웃", use_container_width=True, key="logout"):
        st.session_state["authenticated"] = False
        st.rerun()


# ---------- Main Content (Tabs) ----------
tab_overview, tab_e1, tab_e2, tab_e3, tab_settings = st.tabs([
    "📊 Overview",
    "💱 Engine 1: Tether",
    "📈 Engine 2: Magic Split",
    "🏛 Engine 3: Warehouse",
    "⚙️ Settings",
])

with tab_overview:
    render_overview()

with tab_e1:
    render_engine1()

with tab_e2:
    render_engine2()

with tab_e3:
    render_engine3()

with tab_settings:
    render_settings()


# ---------- DB Data Loading ----------

def _load_latest_from_db():
    """DB에서 각 엔진의 최신 결과를 읽어 session_state에 반영."""
    import json
    from core.models import EngineResult, EngineType, MacroSnapshot, get_session
    from sqlalchemy import desc

    session = get_session()
    try:
        # 최신 매크로 스냅샷
        macro_row = session.query(MacroSnapshot).order_by(desc(MacroSnapshot.timestamp)).first()
        if macro_row:
            st.session_state["macro_data"] = {
                "vix": macro_row.vix or 0,
                "usd_krw": macro_row.usd_krw or 0,
                "sp500_daily_chg_pct": macro_row.sp500_daily_chg_pct or 0,
                "nasdaq_daily_chg_pct": macro_row.nasdaq_daily_chg_pct or 0,
                "fed_funds_rate": macro_row.fed_funds_rate or 0,
            }

        # Engine 1 최신 결과
        e1_row = (
            session.query(EngineResult)
            .filter(EngineResult.engine == EngineType.ENGINE1_TETHER, EngineResult.status == "ok")
            .order_by(desc(EngineResult.timestamp))
            .first()
        )
        if e1_row:
            e1 = json.loads(e1_row.result_json)
            st.session_state["tether_data"] = {
                "raw_premium_pct": e1.get("raw_premium_pct", 0),
                "net_premium_pct": e1.get("net_premium_pct", 0),
                "action": e1.get("action", "hold"),
                "usd_krw": e1.get("usd_krw", 0),
                "price_krw": 0,
            }
            st.session_state["kimchi_premium"] = e1.get("raw_premium_pct", 0)
            st.session_state["last_engine_run"] = str(e1_row.timestamp)[:19]
            st.session_state["engine1_status"] = {
                "is_running": False, "is_paused": False,
                "last_run": str(e1_row.timestamp)[:19], "last_error": None,
            }

        # Engine 2 최신 결과
        e2_row = (
            session.query(EngineResult)
            .filter(EngineResult.engine == EngineType.ENGINE2_MAGIC, EngineResult.status == "ok")
            .order_by(desc(EngineResult.timestamp))
            .first()
        )
        if e2_row:
            e2 = json.loads(e2_row.result_json)
            st.session_state["magic_signals"] = e2.get("signals", [])
            st.session_state["magic_ai_advice"] = e2.get("ai_advice", "")
            st.session_state["active_positions"] = e2.get("positions_count", 0)
            st.session_state["engine2_status"] = {
                "is_running": False, "is_paused": False,
                "last_run": str(e2_row.timestamp)[:19], "last_error": None,
            }

        # Engine 3 최신 결과
        e3_row = (
            session.query(EngineResult)
            .filter(EngineResult.engine == EngineType.ENGINE3_WAREHOUSE, EngineResult.status == "ok")
            .order_by(desc(EngineResult.timestamp))
            .first()
        )
        if e3_row:
            e3 = json.loads(e3_row.result_json)
            st.session_state["warehouse_data"] = e3
            st.session_state["rebalance_status"] = "조정 필요" if e3.get("should_rebalance") else "정상"
            st.session_state["engine3_status"] = {
                "is_running": False, "is_paused": False,
                "last_run": str(e3_row.timestamp)[:19], "last_error": None,
            }

        # CSV 포지션 (항상 최신 파일에서 로드)
        try:
            from services.csv_parser import parse_magic_split_file
            positions = parse_magic_split_file()
            st.session_state["magic_positions"] = [
                {
                    "symbol": p.symbol, "name": p.name,
                    "quantity": p.quantity, "avg_price": p.avg_price,
                    "current_price": p.current_price, "pnl_pct": p.pnl_pct,
                    "split_count": p.split_count,
                    "target_buy_price": p.target_buy_price,
                    "target_sell_price": p.target_sell_price,
                }
                for p in positions
            ]
            st.session_state["active_positions"] = len(positions)
        except Exception as e:
            logger.warning(f"CSV load failed: {e}")

    except Exception as e:
        logger.error(f"DB load failed: {e}")
    finally:
        session.close()


def _run_engines_manual():
    """수동으로 전체 엔진 1회 실행 (run_engines.py와 동일 로직)."""
    import subprocess
    venv_python = str(Path(__file__).parent / ".venv" / "Scripts" / "python.exe")
    script = str(Path(__file__).parent / "run_engines.py")
    subprocess.run([venv_python, script, "--group", "all"], cwd=str(Path(__file__).parent))
