# ============================================================
# GEM Protocol — Dashboard Authentication Gate
# ============================================================
"""Simple password gate for dashboard access."""
from __future__ import annotations

import hashlib
import streamlit as st
from core.config import get_settings


def check_auth() -> bool:
    """
    Render password form if not authenticated.
    Returns True if user is authenticated.
    """
    if st.session_state.get("authenticated", False):
        return True

    settings = get_settings()

    st.markdown("""
    <div style="display: flex; flex-direction: column; align-items: center; 
                justify-content: center; min-height: 60vh;">
        <div style="text-align: center; margin-bottom: 32px;">
            <div style="font-size: 48px; margin-bottom: 16px;">💎</div>
            <div style="font-size: 28px; font-weight: 700; letter-spacing: -0.02em; 
                        color: var(--apple-text-primary);">GEM Protocol</div>
            <div style="font-size: 15px; color: var(--apple-text-secondary); margin-top: 8px;">
                AI Asset Management System</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password = st.text_input("Password", type="password", key="login_pw")
        if st.button("Sign In", use_container_width=True):
            if password == settings.dashboard_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("잘못된 패스워드입니다.")

    return False
