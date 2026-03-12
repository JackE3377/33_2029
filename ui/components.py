# ============================================================
# GEM Protocol v2 — Reusable UI Components
# ============================================================
from __future__ import annotations

import streamlit as st


def _html(s: str):
    st.markdown(s.strip(), unsafe_allow_html=True)


# ── Cards & Metrics ───────────────────────────────────────────

def metric_card(label: str, value: str, sub: str = "", css: str = ""):
    cls = f"gc-value {css}".strip()
    _html(
        f'<div class="gc">'
        f'<div class="gc-label">{label}</div>'
        f'<div class="{cls}">{value}</div>'
        f'<div class="gc-sub">{sub}</div>'
        f'</div>'
    )


def big_metric(label: str, value: str, sub: str = "", css: str = ""):
    cls = f"gc-value big {css}".strip()
    _html(
        f'<div class="gc">'
        f'<div class="gc-label">{label}</div>'
        f'<div class="{cls}">{value}</div>'
        f'<div class="gc-sub">{sub}</div>'
        f'</div>'
    )


def metric_grid(metrics: list[dict]):
    items = ""
    for m in metrics:
        v_cls = f"gc-value {m.get('css', '')}".strip()
        items += (
            f'<div class="gc">'
            f'<div class="gc-label">{m["label"]}</div>'
            f'<div class="{v_cls}">{m["value"]}</div>'
            f'<div class="gc-sub">{m.get("sub", "")}</div>'
            f'</div>'
        )
    _html(f'<div class="mg">{items}</div>')


# ── Alerts ────────────────────────────────────────────────────

def alert_critical(msg: str):
    _html(f'<div class="al-crit"><span style="font-size:20px;">🚨</span><span>{msg}</span></div>')


def alert_warning(msg: str):
    _html(f'<div class="al-warn"><span style="font-size:20px;">⚠️</span><span>{msg}</span></div>')


def alert_info(msg: str):
    _html(f'<div class="al-info"><span style="font-size:20px;">ℹ️</span><span>{msg}</span></div>')


def alert_scout(msg: str):
    _html(f'<div class="al-scout"><span style="font-size:20px;">🎯</span><span>{msg}</span></div>')


# ── Section Headers ───────────────────────────────────────────

def section_title(title: str, subtitle: str = ""):
    _html(f'<div class="st">{title}</div>')
    if subtitle:
        _html(f'<div class="st-sub">{subtitle}</div>')


# ── Traffic Light ─────────────────────────────────────────────

def traffic_light(label: str, status: str, detail: str = ""):
    color = {"hot": "r", "cold": "g", "panic": "r", "normal": "g"}.get(status, "y")
    _html(
        f'<div style="display:flex;align-items:center;padding:6px 0;">'
        f'<span class="dot {color}"></span>'
        f'<span style="font-weight:600;font-size:14px;">{label}</span>'
        f'<span style="margin-left:10px;font-size:12px;color:var(--text-3);">{detail}</span>'
        f'</div>'
    )


# ── Table ────────────────────────────────────────────────────

def data_table(headers: list[str], rows: list[list[str]]):
    th = "".join(f"<th>{h}</th>" for h in headers)
    body = ""
    for row in rows:
        body += "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
    _html(f'<table class="gt"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>')


# ── Badge ────────────────────────────────────────────────────

def verdict_badge(verdict: str) -> str:
    css = {"BUY": "buy", "HOLD": "hold", "AVOID": "avoid"}.get(verdict, "hold")
    return f'<span class="badge {css}">{verdict}</span>'


# ── AI Analysis Card ─────────────────────────────────────────

def analysis_card(title: str, body: str):
    body_html = body.replace("\n", "<br>") if body else "<em>분석 대기 중...</em>"
    _html(
        f'<div class="ac">'
        f'<div class="ac-title">🤖 {title}</div>'
        f'<div class="ac-body">{body_html}</div>'
        f'</div>'
    )


# ── Signal Card (OFF / ON / URGENT) ──────────────────────────

def signal_card(
    icon: str,
    title: str,
    label: str,
    detail: str = "",
    urgency: int = 0,
    theme: str = "",
):
    """Render a signal card with urgency-based styling.

    urgency: 0=OFF (grey), 1=관심, 2=액션(ON), 3=긴급(URGENT)
    theme: sc-tether | sc-dollar | sc-bank | sc-stock | sc-rebal
    """
    if urgency >= 3:
        state_cls = "sc-urgent"
    elif urgency >= 1:
        state_cls = "sc-on"
    else:
        state_cls = ""
    detail_html = f'<div class="sc-detail">{detail}</div>' if detail else ""
    _html(
        f'<div class="sc {state_cls} {theme}">'
        f'<div class="sc-icon">{icon}</div>'
        f'<div class="sc-title">{title}</div>'
        f'<div class="sc-label">{label}</div>'
        f'{detail_html}'
        f'</div>'
    )


def signal_card_html(
    icon: str,
    title: str,
    label: str,
    detail: str = "",
    urgency: int = 0,
    theme: str = "",
) -> str:
    """Return compact signal card HTML with GO/WAIT badge."""
    if urgency >= 3:
        state_cls = "sc-urgent"
        badge = '<span class="sc-badge sc-badge-go-urgent">GO</span>'
    elif urgency >= 2:
        state_cls = "sc-on"
        badge = '<span class="sc-badge sc-badge-go">GO</span>'
    elif urgency >= 1:
        state_cls = "sc-on"
        badge = '<span class="sc-badge sc-badge-wait">관심</span>'
    else:
        state_cls = ""
        badge = '<span class="sc-badge sc-badge-wait">WAIT</span>'
    detail_html = f'<div class="sc-detail">{detail}</div>' if detail else ""
    return (
        f'<div class="sc {state_cls} {theme}">'
        f'<div class="sc-left"><span class="sc-icon">{icon}</span></div>'
        f'<div class="sc-body">'
        f'<div class="sc-title">{title}</div>'
        f'<div class="sc-label">{label}</div>'
        f'{detail_html}'
        f'</div>'
        f'{badge}'
        f'</div>'
    )

