# ============================================================
# GEM Protocol v3 — Telegram Push Notifications
# ============================================================
"""
Sends alerts to Telegram when:
  1) Traffic-light signals change to GO or URGENT
  2) AI stock analysis completes
"""
from __future__ import annotations

import logging
from typing import Any

import requests

from core.config import get_settings

log = logging.getLogger("gem.telegram")

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
_MAX_LEN = 4096  # Telegram message limit


# ── Low-level sender ────────────────────────────────────────

def send_message(text: str, parse_mode: str = "HTML") -> bool:
    """Send a message via Telegram Bot API.

    Returns True on success. Silently skips if token/chat_id are empty.
    Never raises — logs errors instead.
    """
    cfg = get_settings()
    token = cfg.telegram_bot_token
    chat_id = cfg.telegram_chat_id
    if not token or not chat_id:
        return False

    if len(text) > _MAX_LEN:
        text = text[: _MAX_LEN - 20] + "\n\n… (truncated)"

    try:
        resp = requests.post(
            _TELEGRAM_API.format(token=token),
            json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            timeout=10,
        )
        if resp.status_code != 200:
            log.warning("Telegram API %d: %s", resp.status_code, resp.text[:200])
            return False
        return True
    except Exception:
        log.exception("Telegram send failed")
        return False


# ── Urgency helpers ──────────────────────────────────────────

def _fx_urgency(sig_dict: dict | None) -> int:
    if not sig_dict:
        return 0
    return sig_dict.get("urgency", 0)


def _tether_urgency(crypto: dict | None) -> int:
    """Derive tether urgency from kimchi premium (matches section_signals logic)."""
    if not crypto:
        return 0
    prem = crypto.get("kimchi_premium_pct", 0.0)
    if prem >= 3.0 or prem <= -2.0:
        return 3
    if prem >= 2.0 or prem <= -0.5:
        return 2
    return 0


def _dxy_urgency(dollar: dict | None) -> int:
    if not dollar:
        return 0
    return dollar.get("urgency", 0)


def _stock_urgency(slow_data: dict | None) -> int:
    if not slow_data:
        return 0
    ai_top = slow_data.get("ai_top", [])
    buy_picks = [r for r in ai_top if r.get("verdict") == "BUY"]
    return 2 if buy_picks else 0


def _wh_urgency(wh_data: dict | None) -> int:
    if not wh_data:
        return 0
    sigs = wh_data.get("wh_sigs", [])
    if any(s.get("status") == "panic" for s in sigs):
        return 3
    if any(s.get("status") in ("hot", "cold", "momentum_off") for s in sigs):
        return 2
    return 0


# Card definitions: (key, icon, title, urgency_fn, detail_fn)
def _card_specs() -> list[tuple[str, str, str]]:
    return [
        ("usd_split", "💵", "달러 분할매매"),
        ("jpy_split", "💴", "엔화 분할매매"),
        ("tether",    "💰", "테더 김프/역프"),
        ("dxy",       "📊", "달러인덱스(DXY)"),
        ("stock",     "🚀", "매수의견 종목"),
        ("warehouse", "🏛️", "LAA 리밸런싱"),
    ]


def _extract_urgencies(
    fast: dict | None,
    wh: dict | None,
    slow: dict | None = None,
) -> dict[str, int]:
    """Extract urgency values for all 6 cards from payload dicts."""
    return {
        "usd_split":  _fx_urgency(fast.get("usd_split") if fast else None),
        "jpy_split":  _fx_urgency(fast.get("jpy_split") if fast else None),
        "tether":     _tether_urgency(fast.get("crypto") if fast else None),
        "dxy":        _dxy_urgency(fast.get("dollar_sig") if fast else None),
        "stock":      _stock_urgency(slow),
        "warehouse":  _wh_urgency(wh),
    }


def _detail_text(key: str, fast: dict | None, wh: dict | None) -> str:
    """Build a short detail string for a changed card."""
    if not fast:
        return ""
    if key == "usd_split":
        s = fast.get("usd_split", {})
        return f"진입점수 {s.get('entry_score', 0)}/100 · {s.get('label', '')}"
    if key == "jpy_split":
        s = fast.get("jpy_split", {})
        return f"진입점수 {s.get('entry_score', 0)}/100 · {s.get('label', '')}"
    if key == "tether":
        c = fast.get("crypto", {})
        prem = c.get("kimchi_premium_pct", 0.0)
        if prem >= 2.0:
            return f"김프 {prem:+.1f}% — USDT 매도 후 달러 매수"
        if prem <= -0.5:
            return f"역프 {prem:+.1f}% — 달러 → 테더 전환"
        return f"김프 {prem:+.1f}%"
    if key == "dxy":
        d = fast.get("dollar_sig", {})
        return d.get("detail", d.get("label", ""))
    if key == "warehouse" and wh:
        sigs = wh.get("wh_sigs", [])
        panic = [s for s in sigs if s.get("status") == "panic"]
        if panic:
            return panic[0].get("label", "패닉 리밸런싱")
        parts = []
        for s in sigs:
            st = s.get("status", "normal")
            if st in ("hot", "cold", "momentum_off"):
                parts.append(f"{s.get('symbol', '')}({st})")
        return ", ".join(parts[:4]) if parts else ""
    return ""


# ── Signal change notification ───────────────────────────────

def notify_signal_changes(
    new_fast: dict,
    new_wh: dict,
    old_fast: dict | None,
    old_wh: dict | None,
    old_slow: dict | None = None,
    new_slow: dict | None = None,
) -> bool:
    """Compare old vs new signal urgencies; send Telegram if GO transitions detected.

    Triggers:
      - GO transition: old urgency < 2  →  new urgency >= 2
      - URGENT transition: old urgency < 3  →  new urgency == 3
    """
    old_u = _extract_urgencies(old_fast, old_wh, old_slow)
    new_u = _extract_urgencies(new_fast, new_wh, new_slow)

    changes: list[tuple[str, str, str, int]] = []  # (key, icon, title, new_urgency)
    specs = {k: (icon, title) for k, icon, title in _card_specs()}

    for key in old_u:
        o, n = old_u[key], new_u[key]
        # GO transition (WAIT→GO)
        if o < 2 and n >= 2:
            icon, title = specs[key]
            changes.append((key, icon, title, n))
        # URGENT escalation (GO→GO! urgent)
        elif o < 3 and n >= 3:
            icon, title = specs[key]
            changes.append((key, icon, title, n))

    if not changes:
        return False

    lines = ["🚦 <b>GEM 신호 변경</b>\n"]
    for key, icon, title, urg in changes:
        badge = "GO‼️" if urg >= 3 else "GO!"
        lines.append(f"{icon} <b>{title}</b>: WAIT → <b>{badge}</b>")
        detail = _detail_text(key, new_fast, new_wh)
        if detail:
            lines.append(f"  {detail}")
        lines.append("")

    return send_message("\n".join(lines))


# ── AI results notification ──────────────────────────────────

_VERDICT_EMOJI = {"BUY": "🟢", "HOLD": "🟡", "AVOID": "🔴"}


def notify_ai_results(ai_top: list[dict[str, Any]]) -> bool:
    """Send AI analysis summary to Telegram."""
    if not ai_top:
        return False

    lines = [f"🤖 <b>GEM AI 분석 완료</b> ({len(ai_top)}종목)\n"]

    for i, r in enumerate(ai_top, 1):
        symbol = r.get("symbol", "?")
        score = r.get("score", 0)
        verdict = r.get("verdict", "HOLD")
        emoji = _VERDICT_EMOJI.get(verdict, "⚪")
        source = r.get("source", "rule")
        src_tag = " (AI)" if source == "ai" else " (Rule)"

        lines.append(f"{i}. <b>{symbol}</b> {score}점 {emoji} {verdict}{src_tag}")

        bull = (r.get("bull_summary") or "")[:80]
        bear = (r.get("bear_summary") or "")[:80]
        if bull:
            lines.append(f"  📈 {bull}")
        if bear:
            lines.append(f"  📉 {bear}")
        lines.append("")

    return send_message("\n".join(lines))
