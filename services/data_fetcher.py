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


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_koexim_rates(cur_unit: str = "USD") -> Optional[tuple[float, float, float]]:
    """Fetch official rates from 한국수출입은행 API.

    Returns (매매기준율, TTS, TTB) or None if unavailable.
    """
    cfg = get_settings()
    if not cfg.koexim_api_key:
        return None
    try:
        url = "https://www.koexim.go.kr/site/program/financial/exchangeJSON"
        today = datetime.now().strftime("%Y%m%d")
        resp = requests.get(url, params={
            "authkey": cfg.koexim_api_key,
            "searchdate": today,
            "data": "AP01",
        }, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        for item in data:
            if item.get("cur_unit") == cur_unit:
                def _p(v: str) -> float:
                    return float(v.replace(",", ""))
                return (_p(item["deal_bas_r"]), _p(item["tts"]), _p(item["ttb"]))
    except Exception:
        pass
    return None


@st.cache_data(ttl=300, show_spinner=False)
def fetch_bank_rates_jpy(base_jpy_krw: float) -> list['BankRate']:
    """Compute bank JPY rates using 우대율 model (100엔 기준)."""
    cfg = get_settings()
    base_100 = base_jpy_krw * 100
    base_spread = cfg.fx_base_spread_jpy

    # Try KOEXIM for official JPY TTS/TTB
    koexim = _fetch_koexim_rates("JPY(100)")
    if koexim:
        _, tts, ttb = koexim
        tts_gap = tts - base_100
        ttb_gap = base_100 - ttb
    else:
        tts_gap = base_100 * base_spread / 100
        ttb_gap = base_100 * base_spread / 100

    rates: list['BankRate'] = []
    for name, pref in cfg.bank_preferences_jpy.items():
        discount = pref / 100
        buy = round(base_100 + tts_gap * (1 - discount), 2)
        sell = round(base_100 - ttb_gap * (1 - discount), 2)
        actual_spread = round((buy - sell) / base_100 * 100, 4) if base_100 > 0 else 0
        rates.append(BankRate(
            name=name, buy_rate=buy, sell_rate=sell, spread_pct=actual_spread,
        ))
    if rates:
        best_buy = min(rates, key=lambda r: r.buy_rate)
        best_sell = max(rates, key=lambda r: r.sell_rate)
        best_buy.recommendation = "💰 매수 최저가"
        best_sell.recommendation = "💵 매도 최고가"
    return rates


# ── Bank Exchange Rates ───────────────────────────────────────

@dataclass
class BankRate:
    name: str = ""
    buy_rate: float = 0.0      # 달러 살 때 (고객이 원화→달러)
    sell_rate: float = 0.0     # 달러 팔 때 (고객이 달러→원화)
    spread_pct: float = 0.0
    recommendation: str = ""   # "매수 유리" / "매도 유리" / ""


@st.cache_data(ttl=300, show_spinner=False)
def fetch_bank_rates(base_usd_krw: float) -> list[BankRate]:
    """Compute bank exchange rates using 우대율 model.

    Formula per institution:
      buy  = 기준율 + (TTS - 기준율) × (1 - 우대율/100)
      sell = 기준율 - (기준율 - TTB) × (1 - 우대율/100)
    100% 우대 → buy = sell = 기준율 (토스, 카카오뱅크)
    """
    cfg = get_settings()
    base_spread = cfg.fx_base_spread_usd

    # Try KOEXIM for official TTS/TTB
    koexim = _fetch_koexim_rates("USD")
    if koexim:
        _, tts, ttb = koexim
        tts_gap = tts - base_usd_krw
        ttb_gap = base_usd_krw - ttb
    else:
        # Fallback: estimate spread from base rate
        tts_gap = base_usd_krw * base_spread / 100
        ttb_gap = base_usd_krw * base_spread / 100

    rates: list[BankRate] = []
    for name, pref in cfg.bank_preferences.items():
        discount = pref / 100
        buy = round(base_usd_krw + tts_gap * (1 - discount), 2)
        sell = round(base_usd_krw - ttb_gap * (1 - discount), 2)
        actual_spread = round((buy - sell) / base_usd_krw * 100, 4) if base_usd_krw > 0 else 0
        rates.append(BankRate(
            name=name, buy_rate=buy, sell_rate=sell, spread_pct=actual_spread,
        ))

    if rates:
        best_buy = min(rates, key=lambda r: r.buy_rate)
        best_sell = max(rates, key=lambda r: r.sell_rate)
        best_buy.recommendation = "💰 매수 최저가"
        best_sell.recommendation = "💵 매도 최고가"

    return rates
