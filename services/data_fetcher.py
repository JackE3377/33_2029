# ============================================================
# GEM Protocol v3 — Market Data Fetcher
# ============================================================
"""
Data sources:
  Primary   → Yahoo Finance (yfinance)
  Secondary → Alpha Vantage
  Tertiary  → FRED (macro only)
  Crypto    → Bithumb public API
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

from core.config import get_settings


# ── Data Classes ──────────────────────────────────────────────

@dataclass
class MacroData:
    usd_krw: float = 0.0
    vix: float = 0.0
    sp500_daily_chg_pct: float = 0.0
    nasdaq_daily_chg_pct: float = 0.0
    fed_funds_rate: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class StockQuote:
    symbol: str = ""
    price: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    rsi_14: Optional[float] = None
    weekly_rsi: Optional[float] = None
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    free_cash_flow: Optional[float] = None
    debt_to_equity: Optional[float] = None
    market_cap: Optional[float] = None
    name: str = ""


@dataclass
class CryptoQuote:
    symbol: str = "USDT"
    price_krw: float = 0.0
    kimchi_premium_pct: float = 0.0


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


def _find_support_resistance(close: pd.Series, window: int = 20) -> tuple[float, float]:
    """Find short-term support/resistance from rolling min/max."""
    if len(close) < window:
        recent = close
    else:
        recent = close.iloc[-window:]
    support = float(recent.min())
    resistance = float(recent.max())
    return support, resistance


# ── Fetchers ──────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_macro() -> MacroData:
    """Fetch macro indicators (cached 5 min)."""
    data = MacroData()
    try:
        tickers = yf.Tickers("KRW=X ^VIX ^GSPC ^IXIC")

        fx_hist = tickers.tickers["KRW=X"].history(period="2d")
        if not fx_hist.empty:
            data.usd_krw = float(fx_hist["Close"].iloc[-1])

        vix_hist = tickers.tickers["^VIX"].history(period="2d")
        if not vix_hist.empty:
            data.vix = float(vix_hist["Close"].iloc[-1])

        sp_hist = tickers.tickers["^GSPC"].history(period="5d")
        if len(sp_hist) >= 2:
            prev, curr = float(sp_hist["Close"].iloc[-2]), float(sp_hist["Close"].iloc[-1])
            data.sp500_daily_chg_pct = round(((curr - prev) / prev) * 100, 2) if prev else 0

        nq_hist = tickers.tickers["^IXIC"].history(period="5d")
        if len(nq_hist) >= 2:
            prev, curr = float(nq_hist["Close"].iloc[-2]), float(nq_hist["Close"].iloc[-1])
            data.nasdaq_daily_chg_pct = round(((curr - prev) / prev) * 100, 2) if prev else 0
    except Exception:
        pass

    # FRED fallback for Fed Funds Rate
    settings = get_settings()
    if settings.fred_api_key:
        try:
            resp = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    "series_id": "FEDFUNDS",
                    "api_key": settings.fred_api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 1,
                },
                timeout=10,
            )
            obs = resp.json().get("observations", [])
            if obs:
                data.fed_funds_rate = float(obs[0]["value"])
        except Exception:
            pass

    return data


@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock(symbol: str) -> StockQuote:
    """Fetch single stock quote with fundamentals (cached 5 min)."""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="1mo")
    if hist.empty:
        return StockQuote(symbol=symbol)

    price = float(hist["Close"].iloc[-1])
    prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
    change_pct = round(((price - prev) / prev) * 100, 2) if prev else 0
    volume = int(hist["Volume"].iloc[-1])
    rsi_14 = _calc_rsi(hist["Close"], 14)

    weekly_hist = ticker.history(period="6mo", interval="1wk")
    weekly_rsi = _calc_rsi(weekly_hist["Close"], 14) if len(weekly_hist) > 14 else None

    info = ticker.info or {}

    return StockQuote(
        symbol=symbol,
        price=price,
        change_pct=change_pct,
        volume=volume,
        rsi_14=rsi_14,
        weekly_rsi=weekly_rsi,
        forward_pe=info.get("forwardPE"),
        peg_ratio=info.get("pegRatio"),
        free_cash_flow=info.get("freeCashflow"),
        debt_to_equity=info.get("debtToEquity"),
        market_cap=info.get("marketCap"),
        name=info.get("shortName", symbol),
    )


@st.cache_data(ttl=300, show_spinner=False)
def fetch_stocks_batch(symbols: list[str]) -> list[StockQuote]:
    """Fetch multiple stocks."""
    results = []
    for sym in symbols:
        try:
            results.append(fetch_stock(sym))
        except Exception:
            results.append(StockQuote(symbol=sym))
    return results


@st.cache_data(ttl=300, show_spinner=False)
def fetch_usdt_premium(usd_krw: float) -> CryptoQuote:
    """Fetch USDT/KRW from Bithumb public API and calculate kimchi premium."""
    try:
        resp = requests.get(
            "https://api.bithumb.com/public/ticker/USDT_KRW",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "0000":
            price_krw = float(data["data"]["closing_price"])
            fair_krw = usd_krw  # USDT ≈ $1
            premium = round(((price_krw / fair_krw) - 1) * 100, 2) if fair_krw > 0 else 0.0
            return CryptoQuote(price_krw=price_krw, kimchi_premium_pct=premium)
    except Exception:
        pass
    return CryptoQuote()


# ── Dollar Index (DXY) ────────────────────────────────────────

@dataclass
class DXYData:
    price: float = 0.0
    change_pct: float = 0.0
    rsi_14: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    high_52w: float = 0.0
    low_52w: float = 0.0
    drawdown_pct: float = 0.0      # from 52-week high
    bounce_score: int = 50          # 0-100 (higher = more likely bounce)
    bounce_label: str = "중립"


@st.cache_data(ttl=300, show_spinner=False)
def fetch_dxy() -> DXYData:
    """Fetch Dollar Index with technical indicators and bounce assessment."""
    d = DXYData()
    try:
        ticker = yf.Ticker("DX-Y.NYB")
        hist = ticker.history(period="6mo")
        if hist.empty:
            return d
        close = hist["Close"]
        d.price = float(close.iloc[-1])
        if len(close) >= 2:
            prev = float(close.iloc[-2])
            d.change_pct = round(((d.price - prev) / prev) * 100, 2) if prev else 0
        d.rsi_14 = _calc_rsi(close, 14)
        if len(close) >= 20:
            d.sma_20 = round(float(close.rolling(20).mean().iloc[-1]), 2)
        if len(close) >= 50:
            d.sma_50 = round(float(close.rolling(50).mean().iloc[-1]), 2)
        d.high_52w = float(close.max())
        d.low_52w = float(close.min())
        if d.high_52w > 0:
            d.drawdown_pct = round(((d.price - d.high_52w) / d.high_52w) * 100, 2)

        # Bounce assessment (rule-based)
        score = 50
        if d.rsi_14 is not None:
            if d.rsi_14 < 30:
                score += 25    # very oversold → high bounce chance
            elif d.rsi_14 < 40:
                score += 15
            elif d.rsi_14 > 70:
                score -= 20    # overbought → low bounce chance
        if d.sma_20 and d.price < d.sma_20:
            score += 10  # below 20-day MA → mean-reversion potential
        if d.sma_50 and d.price < d.sma_50:
            score += 5
        if d.drawdown_pct < -5:
            score += 10  # significant drop → bounce potential
        d.bounce_score = max(0, min(100, score))

        if d.bounce_score >= 70:
            d.bounce_label = "반등 가능성 높음 🟢"
        elif d.bounce_score >= 55:
            d.bounce_label = "반등 가능성 있음 🟡"
        elif d.bounce_score <= 30:
            d.bounce_label = "추가 하락 가능 🔴"
        else:
            d.bounce_label = "중립 ⚪"
    except Exception:
        pass
    return d


# ── Japanese Yen (JPY/KRW) ────────────────────────────────────

@dataclass
class JPYData:
    price: float = 0.0           # 1 JPY = X KRW
    price_100: float = 0.0       # 100 JPY = X KRW
    change_pct: float = 0.0
    rsi_14: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    high_52w: float = 0.0
    low_52w: float = 0.0
    drawdown_pct: float = 0.0


@st.cache_data(ttl=300, show_spinner=False)
def fetch_jpy() -> JPYData:
    """Fetch JPY/KRW with technicals for yen trading signals."""
    d = JPYData()
    try:
        ticker = yf.Ticker("JPYKRW=X")
        hist = ticker.history(period="6mo")
        if hist.empty:
            return d
        close = hist["Close"]
        d.price = float(close.iloc[-1])
        d.price_100 = round(d.price * 100, 2)
        if len(close) >= 2:
            prev = float(close.iloc[-2])
            d.change_pct = round(((d.price - prev) / prev) * 100, 2) if prev else 0
        d.rsi_14 = _calc_rsi(close, 14)
        if len(close) >= 20:
            d.sma_20 = round(float(close.rolling(20).mean().iloc[-1]) * 100, 2)
        if len(close) >= 50:
            d.sma_50 = round(float(close.rolling(50).mean().iloc[-1]) * 100, 2)
        d.high_52w = round(float(close.max()) * 100, 2)
        d.low_52w = round(float(close.min()) * 100, 2)
        if d.high_52w > 0:
            d.drawdown_pct = round(((d.price_100 - d.high_52w) / d.high_52w) * 100, 2)
    except Exception:
        pass
    return d


# ── FX Intraday (5-min bars for split buy/sell) ───────────────

@dataclass
class FXIntraday:
    symbol: str = ""           # "USD" or "JPY"
    current: float = 0.0      # current price (KRW per unit)
    rsi_5m: Optional[float] = None   # RSI on 5-min bars
    sma_20: Optional[float] = None   # 20-bar SMA (5min)
    sma_50: Optional[float] = None   # 50-bar SMA (5min)
    support: float = 0.0      # short-term support
    resistance: float = 0.0   # short-term resistance
    high_today: float = 0.0
    low_today: float = 0.0
    market_open: bool = True


@st.cache_data(ttl=120, show_spinner=False)
def fetch_fx_intraday(yf_symbol: str, label: str = "USD", multiplier: float = 1.0) -> FXIntraday:
    """Fetch 5-min intraday FX data for split buy/sell signals.

    yf_symbol: e.g. "KRW=X" (USD/KRW) or "JPYKRW=X" (JPY/KRW)
    multiplier: 1.0 for USD, 100.0 for JPY (100엔 기준)
    """
    d = FXIntraday(symbol=label)
    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="5d", interval="5m")
        if hist.empty:
            d.market_open = False
            return d
        close = hist["Close"].dropna() * multiplier
        if close.empty:
            d.market_open = False
            return d

        d.current = round(float(close.iloc[-1]), 2)
        d.rsi_5m = _calc_rsi(close, 14)

        if len(close) >= 20:
            d.sma_20 = round(float(close.rolling(20).mean().iloc[-1]), 2)
        if len(close) >= 50:
            d.sma_50 = round(float(close.rolling(50).mean().iloc[-1]), 2)

        d.support, d.resistance = _find_support_resistance(close, window=40)

        # Today's high/low
        today = close.index[-1].date() if hasattr(close.index[-1], 'date') else None
        if today:
            today_data = close[close.index.date == today]
            if not today_data.empty:
                d.high_today = round(float(today_data.max()), 2)
                d.low_today = round(float(today_data.min()), 2)
        if d.high_today == 0:
            d.high_today = d.resistance
            d.low_today = d.support

        # Check if data is stale (>30 min gap → market likely closed)
        last_ts = close.index[-1]
        if hasattr(last_ts, 'tz_localize'):
            pass
        now_utc = datetime.now(timezone.utc)
        try:
            last_aware = last_ts.to_pydatetime()
            if last_aware.tzinfo is None:
                import pytz
                last_aware = pytz.utc.localize(last_aware)
            gap_minutes = (now_utc - last_aware).total_seconds() / 60
            d.market_open = gap_minutes < 30
        except Exception:
            d.market_open = True

    except Exception:
        d.market_open = False
    return d
