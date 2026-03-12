# ============================================================
# GEM Protocol v2 — Market Data Fetcher
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
