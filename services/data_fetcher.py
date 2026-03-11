# ============================================================
# GEM Protocol — Market Data Fetcher (Fallback Chain)
# ============================================================
"""
Data fetching layer with fallback chain:
  Primary   → Yahoo Finance (yfinance)
  Secondary → Alpha Vantage
  Tertiary  → FRED (macro only)

Includes anomaly detection for corrupt data.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf
import requests

from core.config import get_settings
from core.logger import get_logger

logger = get_logger("data_fetcher")


# ---------- Data Classes ----------

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
    symbol: str
    price: float
    change_pct: float
    volume: int
    rsi_14: Optional[float] = None
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    free_cash_flow: Optional[float] = None
    debt_to_equity: Optional[float] = None
    weekly_rsi: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CryptoQuote:
    symbol: str
    price_usd: float
    price_krw: float
    kimchi_premium_pct: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------- Validators ----------

def _validate_positive(value: float, name: str) -> bool:
    if value <= 0:
        logger.warning(f"Anomaly detected: {name} = {value} (expected positive)")
        return False
    return True


def _validate_range(value: float, name: str, low: float, high: float) -> bool:
    if not (low <= value <= high):
        logger.warning(f"Anomaly detected: {name} = {value} (expected {low}~{high})")
        return False
    return True


# ---------- Yahoo Finance (Primary) ----------

class YahooFetcher:
    """Primary data source via yfinance."""

    @staticmethod
    def get_macro() -> MacroData:
        logger.info("Fetching macro data from Yahoo Finance")
        data = MacroData()

        try:
            # USD/KRW
            fx = yf.Ticker("KRW=X")
            hist = fx.history(period="2d")
            if not hist.empty:
                data.usd_krw = float(hist["Close"].iloc[-1])

            # VIX
            vix = yf.Ticker("^VIX")
            vix_hist = vix.history(period="2d")
            if not vix_hist.empty:
                data.vix = float(vix_hist["Close"].iloc[-1])

            # S&P 500
            sp = yf.Ticker("^GSPC")
            sp_hist = sp.history(period="5d")
            if len(sp_hist) >= 2:
                prev = float(sp_hist["Close"].iloc[-2])
                curr = float(sp_hist["Close"].iloc[-1])
                data.sp500_daily_chg_pct = ((curr - prev) / prev) * 100 if prev else 0

            # NASDAQ
            nq = yf.Ticker("^IXIC")
            nq_hist = nq.history(period="5d")
            if len(nq_hist) >= 2:
                prev = float(nq_hist["Close"].iloc[-2])
                curr = float(nq_hist["Close"].iloc[-1])
                data.nasdaq_daily_chg_pct = ((curr - prev) / prev) * 100 if prev else 0

        except Exception as e:
            logger.error(f"Yahoo macro fetch error: {e}")

        # Validation
        _validate_range(data.usd_krw, "USD/KRW", 800, 2000)
        _validate_range(data.vix, "VIX", 0, 100)

        return data

    @staticmethod
    def get_stock(symbol: str) -> StockQuote:
        logger.info(f"Fetching stock data for {symbol} from Yahoo Finance")
        ticker = yf.Ticker(symbol)

        hist = ticker.history(period="1mo")
        if hist.empty:
            raise ValueError(f"No data for {symbol}")

        price = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
        change_pct = ((price - prev) / prev) * 100 if prev else 0
        volume = int(hist["Volume"].iloc[-1])

        # RSI(14) calculation
        rsi_14 = _calc_rsi(hist["Close"], period=14)

        # Weekly RSI from weekly data
        weekly_hist = ticker.history(period="6mo", interval="1wk")
        weekly_rsi = _calc_rsi(weekly_hist["Close"], period=14) if len(weekly_hist) > 14 else None

        # Fundamentals
        info = ticker.info or {}
        quote = StockQuote(
            symbol=symbol,
            price=price,
            change_pct=change_pct,
            volume=volume,
            rsi_14=rsi_14,
            forward_pe=info.get("forwardPE"),
            peg_ratio=info.get("pegRatio"),
            free_cash_flow=info.get("freeCashflow"),
            debt_to_equity=info.get("debtToEquity"),
            weekly_rsi=weekly_rsi,
        )

        _validate_positive(quote.price, f"{symbol}.price")
        return quote


# ---------- Alpha Vantage (Secondary) ----------

class AlphaVantageFetcher:
    """Fallback data source via Alpha Vantage API."""

    BASE_URL = "https://www.alphavantage.co/query"

    @staticmethod
    def get_stock(symbol: str) -> StockQuote:
        settings = get_settings()
        if not settings.alpha_vantage_api_key:
            raise ValueError("Alpha Vantage API key not set")

        logger.info(f"Fetching {symbol} from Alpha Vantage (fallback)")
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": settings.alpha_vantage_api_key,
        }
        resp = requests.get(AlphaVantageFetcher.BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        gq = resp.json().get("Global Quote", {})

        price = float(gq.get("05. price", 0))
        change_pct = float(gq.get("10. change percent", "0").replace("%", ""))
        volume = int(gq.get("06. volume", 0))

        return StockQuote(
            symbol=symbol,
            price=price,
            change_pct=change_pct,
            volume=volume,
        )


# ---------- FRED (Macro Fallback) ----------

class FREDFetcher:
    """Macro data fallback from Federal Reserve Economic Data."""

    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    @staticmethod
    def get_fed_funds_rate() -> Optional[float]:
        settings = get_settings()
        if not settings.fred_api_key:
            return None

        logger.info("Fetching Fed Funds Rate from FRED")
        params = {
            "series_id": "FEDFUNDS",
            "api_key": settings.fred_api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1,
        }
        try:
            resp = requests.get(FREDFetcher.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            obs = resp.json().get("observations", [])
            if obs:
                return float(obs[0]["value"])
        except Exception as e:
            logger.error(f"FRED fetch error: {e}")
        return None

    @staticmethod
    def get_vix() -> Optional[float]:
        settings = get_settings()
        if not settings.fred_api_key:
            return None

        logger.info("Fetching VIX from FRED (fallback)")
        params = {
            "series_id": "VIXCLS",
            "api_key": settings.fred_api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1,
        }
        try:
            resp = requests.get(FREDFetcher.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            obs = resp.json().get("observations", [])
            if obs and obs[0]["value"] != ".":
                return float(obs[0]["value"])
        except Exception as e:
            logger.error(f"FRED VIX fetch error: {e}")
        return None


# ---------- Crypto Data ----------

class CryptoFetcher:
    """USDT price from Bithumb (KRW) public API for kimchi premium."""

    # 빗썸 공개 시세 API (인증 불필요)
    BITHUMB_TICKER_URL = "https://api.bithumb.com/public/ticker/USDT_KRW"

    @staticmethod
    def get_usdt_premium(usd_krw_rate: float) -> CryptoQuote:
        logger.info("Fetching USDT kimchi premium from Bithumb")

        # Bithumb: USDT/KRW 시세 (공개 API)
        try:
            resp = requests.get(CryptoFetcher.BITHUMB_TICKER_URL, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "0000":
                ticker = data["data"]
                price_krw = float(ticker["closing_price"])
            else:
                logger.error(f"Bithumb API error: {data.get('message')}")
                price_krw = 0.0
        except Exception as e:
            logger.error(f"Bithumb USDT fetch error: {e}")
            price_krw = 0.0

        # USDT ≈ $1 (스테이블코인)
        price_usd = 1.0

        # 김치 프리미엄 = (빗썸 KRW가 / (USD 공정가 × 환율) - 1) × 100
        fair_krw = price_usd * usd_krw_rate
        premium = ((price_krw / fair_krw) - 1) * 100 if fair_krw > 0 else 0.0

        return CryptoQuote(
            symbol="USDT",
            price_usd=price_usd,
            price_krw=price_krw,
            kimchi_premium_pct=round(premium, 2),
        )


# ---------- Aggregated Fetcher with Fallback ----------

class DataFetcher:
    """Unified data interface with automatic fallback chain."""

    @staticmethod
    def get_macro() -> MacroData:
        """Fetch macro data: Yahoo → FRED fallback for individual fields."""
        data = YahooFetcher.get_macro()

        # Fallback: if VIX failed, try FRED
        if data.vix <= 0:
            fred_vix = FREDFetcher.get_vix()
            if fred_vix is not None:
                data.vix = fred_vix

        # Always try to enrich with Fed Funds Rate from FRED
        data.fed_funds_rate = FREDFetcher.get_fed_funds_rate()

        return data

    @staticmethod
    def get_stock(symbol: str) -> StockQuote:
        """Fetch stock: Yahoo → Alpha Vantage fallback."""
        try:
            return YahooFetcher.get_stock(symbol)
        except Exception as e:
            logger.warning(f"Yahoo failed for {symbol}: {e}. Trying Alpha Vantage...")
            try:
                return AlphaVantageFetcher.get_stock(symbol)
            except Exception as e2:
                logger.error(f"All data sources failed for {symbol}: {e2}")
                raise

    @staticmethod
    def get_usdt_premium(usd_krw_rate: float) -> CryptoQuote:
        return CryptoFetcher.get_usdt_premium(usd_krw_rate)


# ---------- Helpers ----------

def _calc_rsi(prices, period: int = 14) -> Optional[float]:
    """Calculate RSI from a pandas Series of closing prices."""
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
