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

