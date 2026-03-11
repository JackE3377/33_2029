# ============================================================
# GEM Protocol — UI Component Library (Apple HIG)
# ============================================================
"""
Reusable Streamlit UI components with Apple-style rendering.
All components use st.markdown with HTML/CSS injection.
"""
from __future__ import annotations

import streamlit as st


def _html(html_str: str):
    """Render HTML via st.markdown, stripping leading whitespace to avoid code-block interpretation."""
    st.markdown(html_str.strip(), unsafe_allow_html=True)


# ---------- Cards ----------

def metric_card(label: str, value: str, subtitle: str = "", css_class: str = ""):
    """Apple-style metric card with glassmorphism."""
    value_class = f"gem-card-value {css_class}".strip()
    _html(
        f'<div class="gem-card">'
        f'<div class="gem-card-header">{label}</div>'
        f'<div class="{value_class}">{value}</div>'
        f'<div class="gem-card-subtitle">{subtitle}</div>'
        f'</div>'
    )


def metric_grid(metrics: list[dict]):
    """Render a responsive grid of metrics."""
    items = ""
    for m in metrics:
        direction = m.get("direction", "")
        change_class = f"gem-metric-change {direction}" if direction else "gem-metric-change"
        change_html = f'<div class="{change_class}">{m.get("change", "")}</div>' if m.get("change") else ""
        items += (
            f'<div class="gem-metric-item">'
            f'<div class="gem-metric-label">{m["label"]}</div>'
            f'<div class="gem-metric-value">{m["value"]}</div>'
            f'{change_html}'
            f'</div>'
        )
    _html(f'<div class="gem-metric-grid">{items}</div>')


def ai_insight_card(title: str, content: str):
    """Purple-tinted AI analysis card."""
    content_html = content.replace("\n", "<br>") if content else "<em>AI 분석 준비 중...</em>"
    _html(
        f'<div class="gem-ai-card">'
        f'<div class="gem-card-header">\U0001f916 {title}</div>'
        f'<div style="font-size:14px;line-height:1.7;color:var(--apple-text-primary);">'
        f'{content_html}</div>'
        f'</div>'
    )


# ---------- Alerts ----------

def alert_banner(priority: str, message: str, icon: str = ""):
    """Top-of-page alert banner (critical/warning/info)."""
    css_class = {
        "critical": "gem-alert-critical",
        "warning": "gem-alert-warning",
        "info": "gem-alert-info",
    }.get(priority, "gem-alert-info")
    default_icons = {"critical": "\U0001f534", "warning": "\U0001f7e1", "info": "\U0001f535"}
    icon = icon or default_icons.get(priority, "\u2139\ufe0f")
    _html(
        f'<div class="{css_class}">'
        f'<span style="font-size:20px;">{icon}</span>'
        f'<span>{message}</span>'
        f'</div>'
    )


# ---------- Status Indicators ----------

def engine_status_indicator(name: str, status: str, last_run: str = ""):
    """Traffic light status dot for engine health."""
    color = {"running": "green", "paused": "yellow", "error": "red", "idle": "yellow"}.get(status, "yellow")
    status_label = {"running": "정상 운행", "paused": "일시 정지", "error": "오류 발생", "idle": "대기 중"}.get(status, status)
    last_run_text = f' \u00b7 마지막: {last_run}' if last_run else ""
    _html(
        f'<div style="display:flex;align-items:center;padding:8px 0;">'
        f'<span class="gem-status-dot {color}"></span>'
        f'<span style="font-weight:500;font-size:14px;color:var(--apple-text-primary);">{name}</span>'
        f'<span style="margin-left:8px;font-size:12px;color:var(--apple-text-tertiary);">'
        f'{status_label}{last_run_text}</span>'
        f'</div>'
    )


# ---------- Section Headers ----------

def section_title(title: str, subtitle: str = ""):
    """Apple-style section header with optional subtitle."""
    _html(f'<div class="gem-section-title">{title}</div>')
    if subtitle:
        _html(f'<div class="gem-section-subtitle">{subtitle}</div>')


# ---------- Progress ----------

def goal_progress(current: float, target: float, label: str = ""):
    """Progress bar showing progress toward 33억 goal."""
    pct = min((current / target) * 100, 100) if target > 0 else 0
    label_text = label or f"\u20a9{current/1e8:,.1f}억 / \u20a9{target/1e8:,.1f}억 ({pct:.1f}%)"
    _html(
        f'<div class="gem-card">'
        f'<div class="gem-card-header">\U0001f3af 목표 달성률</div>'
        f'<div style="font-size:14px;margin-bottom:8px;color:var(--apple-text-secondary);">{label_text}</div>'
        f'<div class="gem-progress-container">'
        f'<div class="gem-progress-bar" style="width:{pct}%;"></div>'
        f'</div></div>'
    )


# ---------- Badges ----------

def badge(text: str, color: str = "blue") -> str:
    """Returns HTML for an inline badge. Use inside markdown."""
    return f'<span class="gem-badge {color}">{text}</span>'


# ---------- Data Table ----------

def styled_table(headers: list[str], rows: list[list[str]]):
    """Apple-style data table."""
    th = "".join(f"<th>{h}</th>" for h in headers)
    tbody = ""
    for row in rows:
        cells = "".join(f"<td>{cell}</td>" for cell in row)
        tbody += f"<tr>{cells}</tr>"
    _html(
        f'<table class="gem-table">'
        f'<thead><tr>{th}</tr></thead>'
        f'<tbody>{tbody}</tbody>'
        f'</table>'
    )


# ---------- Chart Container ----------

def chart_container(title: str):
    """Returns a context-like styled container wrapper for charts."""
    _html(f'<div class="gem-card"><div class="gem-card-header">{title}</div>')


def chart_container_end():
    _html("</div>")
