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


def _fmt_body(text: str, force_list: bool = False) -> str:
    """Format AI analysis text and normalise bullet/list structures."""
    import re as _re

    def _highlight(t: str) -> str:
        # Numbers: $123, 12.5%, RSI 28, PEG 0.8, PE 15
        t = _re.sub(
            r'(\$[\d,.]+|[\d]+\.?\d*%|RSI\s*[\d.]+|PEG\s*[\d.]+|'
            r'P/?E\s*[\d.]+|EPS\s*[\d.]+|FCF\s*[\d,.]+|D/E\s*[\d.]+)',
            r'<span class="ac2-num">\1</span>', t, flags=_re.IGNORECASE,
        )
        # Positive keywords
        t = _re.sub(
            r'(과매도|저평가|상승세|성장|강세|반등|호재|개선|확대|돌파|매출 증가|순이익 증가)',
            r'<span class="ac2-pos">\1</span>', t,
        )
        # Negative keywords
        t = _re.sub(
            r'(과매수|고평가|하락|리스크|약세|위험|둔화|감소|적자|부채|하방|악재|축소)',
            r'<span class="ac2-neg">\1</span>', t,
        )
        return t

    raw_lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not raw_lines:
        return ""

    # Detect many list styles: "1.", "1)", "1:", "①", "-", "•", markdown-bolded forms.
    bullet_re = _re.compile(
        r'^\s*(?:\*\*|__)?\s*(?:\d+\s*[.)\-:]|[①②③④⑤⑥⑦⑧⑨⑩]|[-•▪▸])\s*(?:\*\*|__)?\s*'
    )
    number_only_re = _re.compile(
        r'^\s*(?:\*\*|__)?\s*(?:\d+\s*[.)\-:]|[①②③④⑤⑥⑦⑧⑨⑩])\s*(?:\*\*|__)?\s*$'
    )

    # Normalise "1." + next-line text into a single logical bullet line.
    normalized: list[str] = []
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        if number_only_re.match(line) and i + 1 < len(raw_lines):
            normalized.append(f"- {raw_lines[i + 1]}")
            i += 2
            continue
        normalized.append(line)
        i += 1

    # If model returns one long line like "1. ... 2. ...", split it first.
    if len(normalized) == 1:
        one = normalized[0]
        chunks = _re.split(r'\s+(?=(?:\d+\s*[.)\-:]|[①②③④⑤⑥⑦⑧⑨⑩])\s*)', one)
        if len(chunks) >= 2:
            normalized = [c.strip() for c in chunks if c.strip()]

    has_bullet = any(bullet_re.match(l) for l in normalized)
    as_list = force_list or has_bullet

    if as_list:
        items: list[str] = []
        cur = ""
        for line in normalized:
            if bullet_re.match(line):
                if cur:
                    items.append(cur)
                cur = bullet_re.sub('', line).strip()
            else:
                if cur:
                    # Continuation line: merge to remove wasted vertical space.
                    cur = f"{cur} {line}".strip()
                else:
                    cur = line
        if cur:
            items.append(cur)

        if not items:
            items = normalized

        return '<ul class="ac2-list">' + ''.join(
            f'<li>{_highlight(it)}</li>' for it in items if it
        ) + '</ul>'

    # Legacy prose fallback for synthesis/summary blocks.
    parts = _re.split(r'(?<=[.!?。])\s+', text.strip())
    if len(parts) <= 1:
        return _highlight(text)
    return ''.join(
        f'<p class="ac2-sent">{_highlight(p.strip())}</p>'
        for p in parts if p.strip()
    )


def analysis_card_v2(
    header: str,
    bull: str = "",
    bear: str = "",
    synthesis: str = "",
    source: str = "ai",
):
    """Structured AI analysis card with color-coded Bull / Bear / Synthesis sections."""
    sections = ""
    if bull:
        sections += (
            '<div class="ac2-sec ac2-bull">'
            '<div class="ac2-sec-title">🟢 Bull Agent</div>'
            f'<div class="ac2-sec-body">{_fmt_body(bull, force_list=True)}</div>'
            '</div>'
        )
    if bear:
        sections += (
            '<div class="ac2-sec ac2-bear">'
            '<div class="ac2-sec-title">🔴 Bear Agent</div>'
            f'<div class="ac2-sec-body">{_fmt_body(bear, force_list=True)}</div>'
            '</div>'
        )
    if synthesis:
        sections += (
            '<div class="ac2-sec ac2-synth">'
            '<div class="ac2-sec-title">⚖️ 종합 판단</div>'
            f'<div class="ac2-sec-body">{_fmt_body(synthesis)}</div>'
            '</div>'
        )
    footer = ""
    if source == "rule":
        footer = '<div class="ac2-footer">📊 규칙 기반 분석 (AI 비활성)</div>'

    _html(
        f'<div class="ac2">'
        f'<div class="ac2-header">🤖 {header}</div>'
        f'<div class="ac2-sections">{sections}</div>'
        f'{footer}'
        f'</div>'
    )


# ── Entry Gauge ──────────────────────────────────────────────

def entry_gauge_html(icon: str, label: str, score: int, rationale: str = "") -> str:
    """Return HTML for entry score gauge bar."""
    score = max(0, min(100, score))
    if score >= 60:
        level = "eg-high"
    elif score >= 30:
        level = "eg-mid"
    else:
        level = "eg-low"
    rat_html = f'<div class="eg-rationale">{rationale}</div>' if rationale else ""
    return (
        f'<div class="eg-wrap">'
        f'<div class="eg-header">'
        f'<span class="eg-label">{icon} {label} 진입점수</span>'
        f'<span class="eg-score {level}">{score}<small>/100</small></span>'
        f'</div>'
        f'<div class="eg-track"><div class="eg-fill {level}" style="width:{score}%"></div></div>'
        f'{rat_html}'
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

