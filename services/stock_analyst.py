# ============================================================
# GEM Protocol v3 — 3-Agent Stock Analyst (Bull / Bear / Synthesis)
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
import logging
import re
import time
from dataclasses import dataclass, field

import streamlit as st

from core.config import get_settings
from services.data_fetcher import StockQuote
from services.news_fetcher import NewsItem

logger = logging.getLogger(__name__)


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

# Module-level client & throttle
_gemini_client = None
_last_call_ts: float = 0.0
_MIN_CALL_INTERVAL = 4.0  # seconds between API calls
_exhausted_models: set[str] = set()  # models whose daily quota is gone


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        from google.genai.types import HttpOptions, HttpRetryOptions
        cfg = get_settings()
        # Disable SDK auto-retry on 429 — we handle it ourselves
        _gemini_client = genai.Client(
            api_key=cfg.gemini_api_key,
            http_options=HttpOptions(
                retry_options=HttpRetryOptions(attempts=1),
            ),
        )
    return _gemini_client


def _parse_retry_delay(err_str: str) -> float:
    """Extract 'Please retry in Xs' from a 429 error."""
    m = re.search(r"please retry in ([\d.]+)s", err_str, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r'"retryDelay":\s*"(\d+)s"', err_str)
    if m:
        return float(m.group(1))
    return 60.0  # conservative fallback


def _is_daily_quota(err_str: str) -> bool:
    """True if the 429 is a daily (RPD) limit, not a per-minute (RPM) limit."""
    return "PerDay" in err_str or "per_day" in err_str.lower()


def _call_gemini(prompt: str, use_lite: bool = False) -> str | None:
    """Call Gemini with auto-fallback on daily quota exhaustion.

    Free tier: 20 RPD per model. When primary model is exhausted,
    switches to fallback model (separate quota pool).
    Tier 1+: 1500 RPD — fallback rarely needed.
    """
    global _last_call_ts
    cfg = get_settings()
    if not cfg.gemini_api_key:
        logger.warning("Gemini API key not configured")
        return None
    try:
        from google import genai  # noqa: F811
    except ImportError:
        logger.error("google-genai package not installed")
        return None

    client = _get_gemini_client()

    # Build model chain: primary → fallback
    if use_lite:
        chain = [cfg.gemini_model_lite, cfg.gemini_model_lite_fallback]
    else:
        chain = [cfg.gemini_model, cfg.gemini_model_fallback]
    # Remove already-exhausted models, keep order
    chain = [m for m in chain if m not in _exhausted_models]
    if not chain:
        logger.error("All Gemini models exhausted for today")
        return None

    for model_name in chain:
        for attempt in range(3):
            elapsed = time.time() - _last_call_ts
            if elapsed < _MIN_CALL_INTERVAL:
                time.sleep(_MIN_CALL_INTERVAL - elapsed)
            try:
                resp = client.models.generate_content(
                    model=model_name, contents=prompt,
                )
                _last_call_ts = time.time()
                return resp.text
            except Exception as e:
                _last_call_ts = time.time()
                err_str = str(e)
                if "429" not in err_str and "RESOURCE_EXHAUSTED" not in err_str:
                    logger.error("Gemini API error: %s", e)
                    return None
                # Daily quota hit → mark model exhausted, try next
                if _is_daily_quota(err_str):
                    _exhausted_models.add(model_name)
                    logger.warning(
                        "%s daily quota exhausted, trying next model",
                        model_name,
                    )
                    break  # break attempt loop, try next model
                # RPM limit → wait and retry
                wait = _parse_retry_delay(err_str) + 2
                logger.warning(
                    "Gemini RPM limit on %s (attempt %d/3), waiting %.0fs",
                    model_name, attempt + 1, wait,
                )
                time.sleep(wait)
                _last_call_ts = time.time()
        else:
            # All 3 retry attempts failed (RPM)
            logger.error("%s failed after 3 RPM retries", model_name)
            continue

    logger.error("All models failed or exhausted")
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

    # Try AI pipeline — use lite model for bull/bear, full model for synthesis
    bull_text = _call_gemini(
        f"You are a bullish equity analyst. Analyse this stock and list 3-5 key "
        f"growth catalysts, competitive advantages, and positive signals "
        f"as numbered bullet points (one point per line, 1-2 sentences each). "
        f"Be specific and cite data. Answer in Korean.\n\n{ctx}",
        use_lite=True,
    )
    bear_text = _call_gemini(
        f"You are a bearish red-team analyst. Analyse this stock and list 3-5 key "
        f"risks, weaknesses, regulatory threats, and negative signals "
        f"as numbered bullet points (one point per line, 1-2 sentences each). "
        f"Be specific and cite data. Answer in Korean.\n\n{ctx}",
        use_lite=True,
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


def analyze_screened_stocks(
    screened: list,
    news_map: dict[str, list[NewsItem]],
    top_n: int = 5,
) -> list[AnalysisResult]:
    """AI analysis only for pre-screened top candidates (minimises Gemini calls)."""
    results: list[AnalysisResult] = []
    for s in screened[:top_n]:
        news_titles = [n.title for n in news_map.get(s.symbol, [])]
        raw = analyze_stock(
            symbol=s.symbol, price=s.price, change_pct=s.change_pct,
            rsi_14=s.rsi_14, weekly_rsi=s.weekly_rsi,
            forward_pe=s.forward_pe, peg_ratio=s.peg_ratio,
            free_cash_flow=s.free_cash_flow, debt_to_equity=s.debt_to_equity,
            name=s.name, news_titles=news_titles,
        )
        results.append(AnalysisResult(**raw))
    results.sort(key=lambda r: r.score, reverse=True)
    return results


# ── Batch analysis (3 Gemini calls total) ─────────────────────

def _build_batch_context(candidates: list, news_map: dict[str, list[NewsItem]]) -> str:
    """Build a single context block containing all candidates."""
    blocks = []
    for s in candidates:
        news = news_map.get(s.symbol, [])
        lines = [
            f"### {s.symbol} ({s.name})",
            f"Price: ${s.price:.2f}  Change: {s.change_pct:+.2f}%",
            f"RSI(14): {s.rsi_14}  Weekly RSI: {s.weekly_rsi}",
            f"Forward PE: {s.forward_pe}  PEG: {s.peg_ratio}",
            f"FCF: {s.free_cash_flow}  D/E: {s.debt_to_equity}",
            "Headlines:",
        ]
        for n in news[:4]:
            lines.append(f"- {n.title}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _parse_json_array(text: str) -> list[dict] | None:
    """Extract a JSON array from LLM response text."""
    if not text:
        return None
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def analyze_screened_stocks_batch(
    screened: list,
    news_map: dict[str, list[NewsItem]],
    top_n: int = 5,
) -> list[AnalysisResult]:
    """Batch AI analysis — all candidates in 3 Gemini calls (Bull, Bear, Synthesis)."""
    candidates = [s for s in screened[:top_n] if s.price > 0]
    if not candidates:
        return []

    symbols = [s.symbol for s in candidates]
    ctx = _build_batch_context(candidates, news_map)
    symbol_list = ", ".join(symbols)

    logger.info("Batch AI: %d candidates (%s)", len(candidates), symbol_list)

    # ── Call 1: Bull Agent (lite model) ──
    bull_prompt = (
        f"You are a bullish equity analyst. For EACH of the following {len(candidates)} stocks, "
        f"list 3-5 key growth catalysts, competitive advantages, and positive signals "
        f"as numbered bullet points (one point per line, 1-2 sentences each). "
        f"Be specific and cite data. Answer in Korean.\n\n"
        f"Respond ONLY as a JSON array (no markdown, no extra text):\n"
        f'[{{"symbol": "<TICKER>", "analysis": "<your bull analysis>"}}, ...]\n\n'
        f"{ctx}"
    )
    bull_raw = _call_gemini(bull_prompt, use_lite=True)
    bull_map: dict[str, str] = {}
    bull_items = _parse_json_array(bull_raw)
    if bull_items:
        for item in bull_items:
            sym = item.get("symbol", "").upper()
            if sym in symbols:
                bull_map[sym] = item.get("analysis", "")
    logger.info("Bull batch: %d/%d parsed", len(bull_map), len(candidates))

    # ── Call 2: Bear Agent (lite model) ──
    bear_prompt = (
        f"You are a bearish red-team analyst. For EACH of the following {len(candidates)} stocks, "
        f"list 3-5 key risks, weaknesses, regulatory threats, and negative signals "
        f"as numbered bullet points (one point per line, 1-2 sentences each). "
        f"Be specific and cite data. Answer in Korean.\n\n"
        f"Respond ONLY as a JSON array (no markdown, no extra text):\n"
        f'[{{"symbol": "<TICKER>", "analysis": "<your bear analysis>"}}, ...]\n\n'
        f"{ctx}"
    )
    bear_raw = _call_gemini(bear_prompt, use_lite=True)
    bear_map: dict[str, str] = {}
    bear_items = _parse_json_array(bear_raw)
    if bear_items:
        for item in bear_items:
            sym = item.get("symbol", "").upper()
            if sym in symbols:
                bear_map[sym] = item.get("analysis", "")
    logger.info("Bear batch: %d/%d parsed", len(bear_map), len(candidates))

    # ── Call 3: Synthesis Agent (full model) ──
    # Build synthesis input from bull/bear results
    synth_blocks = []
    for sym in symbols:
        bull_text = bull_map.get(sym, "분석 없음")
        bear_text = bear_map.get(sym, "분석 없음")
        synth_blocks.append(
            f"### {sym}\n"
            f"**Bull:** {bull_text}\n"
            f"**Bear:** {bear_text}"
        )
    synth_input = "\n\n".join(synth_blocks)

    synth_prompt = (
        f"You are a senior portfolio manager. Based on the Bull and Bear analyses below "
        f"for {len(candidates)} stocks, give a final investment verdict for EACH stock.\n\n"
        f"{synth_input}\n\n"
        f"Respond ONLY as a JSON array (no markdown, no extra text):\n"
        f'[{{"symbol": "<TICKER>", "score": <0-100>, "verdict": "<BUY|HOLD|AVOID>", '
        f'"summary": "<2~3 sentence Korean summary>"}}, ...]'
    )
    synth_raw = _call_gemini(synth_prompt, use_lite=False)
    synth_map: dict[str, dict] = {}
    synth_items = _parse_json_array(synth_raw)
    if synth_items:
        for item in synth_items:
            sym = item.get("symbol", "").upper()
            if sym in symbols:
                synth_map[sym] = item
    logger.info("Synthesis batch: %d/%d parsed", len(synth_map), len(candidates))

    # ── Assemble results ──
    results: list[AnalysisResult] = []
    for s in candidates:
        sym = s.symbol
        synth = synth_map.get(sym)
        bull_text = bull_map.get(sym, "")
        bear_text = bear_map.get(sym, "")

        if synth and bull_text and bear_text:
            results.append(AnalysisResult(
                symbol=sym,
                name=s.name,
                score=int(synth.get("score", 50)),
                verdict=synth.get("verdict", "HOLD"),
                bull_summary=bull_text,
                bear_summary=bear_text,
                synthesis=synth.get("summary", ""),
                source="ai",
            ))
        else:
            # Fallback: rule-based for this stock
            q = StockQuote(
                symbol=sym, name=s.name, price=s.price,
                change_pct=s.change_pct,
                rsi_14=s.rsi_14, weekly_rsi=s.weekly_rsi,
                forward_pe=s.forward_pe, peg_ratio=s.peg_ratio,
                free_cash_flow=s.free_cash_flow,
                debt_to_equity=s.debt_to_equity,
            )
            score = _rule_score(q)
            results.append(AnalysisResult(
                symbol=sym, name=s.name,
                score=score,
                verdict=_rule_verdict(score),
                bull_summary=bull_text or "AI 분석 불가 — 재무지표 기반 평가",
                bear_summary=bear_text or "AI 분석 불가 — 재무지표 기반 평가",
                synthesis=f"규칙 기반 점수: {score}/100",
                source="rule",
            ))

    results.sort(key=lambda r: r.score, reverse=True)
    return results
