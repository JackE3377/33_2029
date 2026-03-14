# ============================================================
# GEM Protocol v2 — Index Stock Scanner
# ============================================================
"""
Fetches NASDAQ-100 + S&P 500 constituents, performs batch
technical screening (RSI, drawdown), then fetches fundamentals
only for the top candidates to minimize API calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import streamlit as st
import yfinance as yf

from core.config import get_settings


@dataclass
class ScreenedStock:
    symbol: str = ""
    name: str = ""
    price: float = 0.0
    change_pct: float = 0.0
    rsi_14: Optional[float] = None
    drawdown_pct: float = 0.0     # % from 52-week high
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    free_cash_flow: Optional[float] = None
    debt_to_equity: Optional[float] = None
    market_cap: Optional[float] = None
    weekly_rsi: Optional[float] = None
    rule_score: int = 50
    track: str = ""              # "A", "B", or ""


# ── Constituent Fetching ──────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)
def _fetch_sp500_tickers() -> list[str]:
    """Fetch S&P 500 tickers from Wikipedia."""
    try:
        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            attrs={"id": "constituents"},
        )
        if tables:
            syms = tables[0]["Symbol"].str.replace(".", "-", regex=False).tolist()
            return [s.strip() for s in syms if isinstance(s, str)]
    except Exception:
        pass
    return []


@st.cache_data(ttl=86400, show_spinner=False)
def _fetch_nasdaq100_tickers() -> list[str]:
    """Fetch NASDAQ-100 tickers from Wikipedia."""
    try:
        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/Nasdaq-100",
            match="Ticker",
        )
        for tbl in tables:
            if "Ticker" in tbl.columns:
                return tbl["Ticker"].str.strip().tolist()
    except Exception:
        pass
    return []


@st.cache_data(ttl=86400, show_spinner=False)
def get_index_constituents() -> list[str]:
    """Get deduplicated NASDAQ-100 + S&P 500 tickers."""
    sp = _fetch_sp500_tickers()
    nq = _fetch_nasdaq100_tickers()
    # Deduplicate, preserving order
    seen: set[str] = set()
    result: list[str] = []
    for sym in nq + sp:
        if sym not in seen:
            seen.add(sym)
            result.append(sym)
    # Fallback if both fetches fail
    if len(result) < 50:
        cfg = get_settings()
        result = list(set(result) | set(cfg.watchlist))
    return result


# ── RSI Calculation ───────────────────────────────────────────

def _calc_rsi(prices: pd.Series, period: int = 14) -> Optional[float]:
    if len(prices) < period + 1:
        return None
    deltas = prices.diff().dropna()
    gains = deltas.where(deltas > 0, 0.0)
    losses = (-deltas).where(deltas < 0, 0.0)
    avg_gain = gains.rolling(window=period, min_periods=period).mean().iloc[-1]
    avg_loss = losses.rolling(window=period, min_periods=period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


# ── Rule Score ────────────────────────────────────────────────

def _get_track(symbol: str) -> str:
    """Return track classification: 'A', 'B', or '' (unclassified)."""
    cfg = get_settings()
    if symbol in cfg.track_a:
        return "A"
    if symbol in cfg.track_b:
        return "B"
    return ""


def _death_check(
    symbol: str,
    fcf: Optional[float],
    de: Optional[float],
    mcap: Optional[float],
) -> bool:
    """Return True if stock FAILS death check (should be excluded)."""
    cfg = get_settings()
    # FCF 적자 = 즉시 탈락
    if fcf is not None and fcf <= 0:
        return True
    # 시가총액 최소 기준 미달
    if mcap is not None and mcap < cfg.market_cap_min:
        return True
    # Track A: D/E > 60% 탈락
    track = _get_track(symbol)
    if track == "A" and de is not None and de > cfg.debt_to_equity_max_a:
        return True
    return False


def _calc_rule_score(
    rsi: Optional[float],
    drawdown_pct: float,
    pe: Optional[float],
    peg: Optional[float],
    fcf: Optional[float],
    de: Optional[float] = None,
    track: str = "",
) -> int:
    score = 50
    if rsi is not None:
        if rsi < 30:
            score += 20
        elif rsi < 40:
            score += 10
        elif rsi > 70:
            score -= 15
    if drawdown_pct < -20:
        score += 10
    elif drawdown_pct < -10:
        score += 5
    # Track-aware scoring
    if track == "A":
        # 가치주: PE 중시
        if pe is not None:
            if pe < 15:
                score += 15
            elif pe < 20:
                score += 5
            elif pe > 35:
                score -= 10
        if de is not None and de <= 40:
            score += 5
    elif track == "B":
        # 성장주: PEG 중시
        if peg is not None:
            if peg < 1.0:
                score += 18
            elif peg < 1.5:
                score += 10
            elif peg > 3.0:
                score -= 10
        # D/E > 200% 경고 (감점)
        if de is not None and de > 200:
            score -= 8
    else:
        # 미분류: 일반 로직
        if peg is not None:
            if peg < 1.0:
                score += 15
            elif peg < 1.5:
                score += 8
            elif peg > 3.0:
                score -= 10
        if pe is not None:
            if pe < 15:
                score += 10
            elif pe < 20:
                score += 5
            elif pe > 35:
                score -= 10
    # FCF 흑자 보너스 (이미 death check 통과한 종목)
    if fcf is not None and fcf > 0:
        score += 5
    return max(0, min(100, score))


# ── Batch Screening Pipeline ─────────────────────────────────

@st.cache_data(ttl=600, show_spinner="인덱스 종목 스캔 중…")
def screen_index_stocks(top_n: int = 30) -> list[ScreenedStock]:
    """
    Phase 1: Batch download prices for all constituents (fast).
    Phase 2: Calculate RSI + drawdown, filter top candidates.
    Phase 3: Fetch fundamentals only for top candidates (slow but limited).
    Returns sorted list by rule_score descending.
    """
    cfg = get_settings()
    symbols = get_index_constituents()
    if not symbols:
        return []

    # Phase 1: Batch price download (yfinance batch API)
    try:
        price_data = yf.download(
            " ".join(symbols),
            period="1mo",
            group_by="ticker",
            threads=True,
            progress=False,
        )
    except Exception:
        return []

    # Phase 2: Calculate RSI + drawdown for each ticker
    candidates: list[dict] = []
    for sym in symbols:
        try:
            if len(symbols) > 1:
                close = price_data[sym]["Close"].dropna()
            else:
                close = price_data["Close"].dropna()
            if len(close) < 5:
                continue
            price = float(close.iloc[-1])
            prev = float(close.iloc[-2]) if len(close) >= 2 else price
            chg = round(((price - prev) / prev) * 100, 2) if prev else 0
            high_52w = float(close.max())
            drawdown = round(((price - high_52w) / high_52w) * 100, 2) if high_52w else 0
            rsi = _calc_rsi(close, 14)
            candidates.append({
                "symbol": sym, "price": price, "change_pct": chg,
                "rsi_14": rsi, "drawdown_pct": drawdown,
            })
        except Exception:
            continue

    # Sort by RSI ascending (most oversold first) for pre-screening
    candidates.sort(key=lambda c: c.get("rsi_14") or 50)

    # Take top_n with lowest RSI as primary candidates
    rsi_threshold = cfg.index_screen_rsi_max
    filtered = [c for c in candidates if (c.get("rsi_14") or 50) <= rsi_threshold]
    # If too few, relax threshold
    if len(filtered) < top_n:
        filtered = candidates[:top_n]

    # Phase 3: Fetch fundamentals for filtered candidates only
    # Fetch more than top_n to allow for death-check removals
    fetch_n = min(len(filtered), top_n * 3)
    results: list[ScreenedStock] = []
    sector_count: dict[str, int] = {}  # sector diversity tracking

    for c in filtered[:fetch_n]:
        sym = c["symbol"]
        try:
            info = yf.Ticker(sym).info or {}
        except Exception:
            info = {}

        pe = info.get("forwardPE")
        peg = info.get("pegRatio")
        fcf = info.get("freeCashflow")
        de = info.get("debtToEquity")
        mcap = info.get("marketCap")
        name = info.get("shortName", sym)
        sector = info.get("sector", "Unknown")

        # Death Check: FCF적자, 시총미달, Track A D/E 초과 → 탈락
        if _death_check(sym, fcf, de, mcap):
            continue

        # Sector diversity: 한 섹터 최대 max_per_sector 종목
        cur = sector_count.get(sector, 0)
        if cur >= cfg.max_per_sector:
            continue
        sector_count[sector] = cur + 1

        track = _get_track(sym)
        score = _calc_rule_score(
            c["rsi_14"], c["drawdown_pct"], pe, peg, fcf,
            de=de, track=track,
        )

        results.append(ScreenedStock(
            symbol=sym, name=name,
            price=c["price"], change_pct=c["change_pct"],
            rsi_14=c["rsi_14"], drawdown_pct=c["drawdown_pct"],
            forward_pe=pe, peg_ratio=peg,
            free_cash_flow=fcf, debt_to_equity=de,
            market_cap=mcap, rule_score=score,
            track=track,
        ))

        if len(results) >= top_n:
            break

    results.sort(key=lambda r: r.rule_score, reverse=True)
    return results
