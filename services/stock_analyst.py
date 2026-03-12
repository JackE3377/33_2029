# ============================================================
# GEM Protocol v2 — 3-Agent Stock Analyst (Bull / Bear / Synthesis)
# ============================================================
"""
Uses Google Gemini to run a 3-agent analysis pipeline:
  1. Bull Agent  — identifies growth catalysts & strengths
  2. Bear Agent  — identifies risks, weaknesses, red flags
  3. Synthesis   — merges both views → score 0-100 + verdict

Falls back to a purely rule-based score when Gemini is unavailable.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import streamlit as st

from core.config import get_settings
from services.data_fetcher import StockQuote
from services.news_fetcher import NewsItem


@dataclass
class AnalysisResult:
    symbol: str = ""
    name: str = ""
    score: int = 50           # 0-100
    verdict: str = "HOLD"     # BUY / HOLD / AVOID
    bull_summary: str = ""
    bear_summary: str = ""
    synthesis: str = ""
    source: str = "rule"      # "ai" or "rule"


# ── Gemini helper ─────────────────────────────────────────────

def _call_gemini(prompt: str) -> str | None:
    """Call Gemini Flash and return text. Returns None on any failure."""
    api_key = get_settings().gemini_api_key
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        resp = model.generate_content(prompt)
        return resp.text
    except Exception:
        return None


# ── Rule-based fallback scoring ───────────────────────────────

def _rule_score(q: StockQuote) -> int:
    """Simple weighted score from financial metrics (0-100)."""
    score = 50
    if q.rsi_14 is not None:
        if q.rsi_14 < 30:
            score += 20
        elif q.rsi_14 < 40:
            score += 10
        elif q.rsi_14 > 70:
            score -= 15
    if q.peg_ratio is not None:
        if q.peg_ratio < 1.0:
            score += 15
        elif q.peg_ratio < 1.5:
            score += 8
        elif q.peg_ratio > 3.0:
            score -= 10
    if q.forward_pe is not None:
        if q.forward_pe < 15:
            score += 10
        elif q.forward_pe > 30:
            score -= 10
    if q.free_cash_flow is not None and q.free_cash_flow > 0:
        score += 5
    return max(0, min(100, score))


def _rule_verdict(score: int) -> str:
    if score >= 70:
        return "BUY"
    if score <= 35:
        return "AVOID"
    return "HOLD"


# ── Main analysis pipeline ────────────────────────────────────

def _build_context(q: StockQuote, news: list[NewsItem]) -> str:
    """Build a concise context block for LLM prompts."""
    lines = [
        f"Symbol: {q.symbol} ({q.name})",
        f"Price: ${q.price:.2f}  Change: {q.change_pct:+.2f}%",
        f"RSI(14): {q.rsi_14}  Weekly RSI: {q.weekly_rsi}",
        f"Forward PE: {q.forward_pe}  PEG: {q.peg_ratio}",
        f"FCF: {q.free_cash_flow}  D/E: {q.debt_to_equity}",
        "",
        "Recent Headlines:",
    ]
    for n in news[:6]:
        lines.append(f"- {n.title}")
    return "\n".join(lines)


@st.cache_data(ttl=1800, show_spinner=False)
def analyze_stock(
    symbol: str,
    price: float,
    change_pct: float,
    rsi_14: float | None,
    weekly_rsi: float | None,
    forward_pe: float | None,
    peg_ratio: float | None,
    free_cash_flow: float | None,
    debt_to_equity: float | None,
    name: str,
    news_titles: list[str],
) -> dict:
    """Run 3-agent analysis. Returns dict for cache serialisation."""
    q = StockQuote(
        symbol=symbol, price=price, change_pct=change_pct,
        rsi_14=rsi_14, weekly_rsi=weekly_rsi,
        forward_pe=forward_pe, peg_ratio=peg_ratio,
        free_cash_flow=free_cash_flow, debt_to_equity=debt_to_equity,
        name=name,
    )
    news = [NewsItem(title=t, link="", published="") for t in news_titles]
    ctx = _build_context(q, news)

    # Try AI pipeline
    bull_text = _call_gemini(
        f"You are a bullish equity analyst. Analyse this stock and list 3-5 key "
        f"growth catalysts, competitive advantages, and positive signals in 4-5 sentences. "
        f"Be specific and cite data. Answer in Korean.\n\n{ctx}"
    )
    bear_text = _call_gemini(
        f"You are a bearish red-team analyst. Analyse this stock and list 3-5 key "
        f"risks, weaknesses, regulatory threats, and negative signals in 4-5 sentences. "
        f"Be specific and cite data. Answer in Korean.\n\n{ctx}"
    )

    if bull_text and bear_text:
        synth_prompt = (
            f"You are a senior portfolio manager. Based on the Bull and Bear analyses below, "
            f"give a final investment verdict.\n\n"
            f"## Bull Analysis\n{bull_text}\n\n"
            f"## Bear Analysis\n{bear_text}\n\n"
            f"Respond ONLY in this JSON format (no markdown):\n"
            f'{{"score": <0-100>, "verdict": "<BUY|HOLD|AVOID>", "summary": "<2~3 sentence Korean summary>"}}'
        )
        synth_text = _call_gemini(synth_prompt)
        if synth_text:
            try:
                # Extract JSON from response
                match = re.search(r'\{.*\}', synth_text, re.DOTALL)
                if match:
                    parsed = json.loads(match.group())
                    return AnalysisResult(
                        symbol=symbol, name=name,
                        score=int(parsed.get("score", 50)),
                        verdict=parsed.get("verdict", "HOLD"),
                        bull_summary=bull_text,
                        bear_summary=bear_text,
                        synthesis=parsed.get("summary", ""),
                        source="ai",
                    ).__dict__
            except (json.JSONDecodeError, ValueError):
                pass

    # Fallback: rule-based
    score = _rule_score(q)
    return AnalysisResult(
        symbol=symbol, name=name,
        score=score,
        verdict=_rule_verdict(score),
        bull_summary=bull_text or "AI 분석 불가 — 재무지표 기반 평가",
        bear_summary=bear_text or "AI 분석 불가 — 재무지표 기반 평가",
        synthesis=f"규칙 기반 점수: {score}/100",
        source="rule",
    ).__dict__


def analyze_watchlist(quotes: list[StockQuote], news_map: dict[str, list[NewsItem]], top_n: int = 5) -> list[AnalysisResult]:
    """Analyse all watchlist stocks and return top N by score."""
    results: list[AnalysisResult] = []
    for q in quotes:
        if q.price <= 0:
            continue
        news_titles = [n.title for n in news_map.get(q.symbol, [])]
        raw = analyze_stock(
            symbol=q.symbol, price=q.price, change_pct=q.change_pct,
            rsi_14=q.rsi_14, weekly_rsi=q.weekly_rsi,
            forward_pe=q.forward_pe, peg_ratio=q.peg_ratio,
            free_cash_flow=q.free_cash_flow, debt_to_equity=q.debt_to_equity,
            name=q.name, news_titles=news_titles,
        )
        results.append(AnalysisResult(**raw))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_n]
