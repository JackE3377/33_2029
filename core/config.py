# ============================================================
# GEM Protocol v3 — Core Settings
# ============================================================
from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(cls, settings_cls, **kwargs):
        try:
            import streamlit as st
            if hasattr(st, "secrets") and len(st.secrets) > 0:
                for key, val in st.secrets.items():
                    if isinstance(val, str):
                        os.environ.setdefault(key.upper(), val)
        except Exception:
            pass
        return super().settings_customise_sources(settings_cls, **kwargs)

    # -- LLM --
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"
    gemini_model_lite: str = "gemini-3-flash-preview"
    # Fallback models (separate daily quota pool)
    gemini_model_fallback: str = "gemini-3.1-flash-lite-preview"
    gemini_model_lite_fallback: str = "gemini-3.1-flash-lite-preview"

    # -- Data APIs --
    fred_api_key: str = ""
    alpha_vantage_api_key: str = ""

    # -- 한국수출입은행 API (무료 등록: koexim.go.kr) --
    koexim_api_key: str = ""

    # -- FX Split Buy/Sell Intervals (원) --
    fx_split_buy_interval_usd: float = 4.5
    fx_split_sell_interval_usd: float = 3.0
    fx_split_buy_interval_jpy: float = 3.0
    fx_split_sell_interval_jpy: float = 2.0

    # -- Index Screening --
    index_screen_rsi_max: float = 40.0
    index_screen_top_n_ai: int = 5

    # -- Engine 1: Tether Thresholds --
    kimchi_premium_sell_pct: float = 2.0
    kimchi_premium_buy_pct: float = -0.5

    # -- Engine 2: Magic Split Screening --
    forward_pe_max: float = 15.0
    peg_max: float = 1.5
    rsi_entry: float = 30.0
    debt_to_equity_max_a: float = 60.0    # Track A hard limit
    debt_to_equity_warn_b: float = 200.0  # Track B warning threshold
    market_cap_min: float = 1e10          # $10B minimum
    max_per_sector: int = 2               # sector diversity cap
    strategy_file: str = "STRATEGY.md"    # local strategy doc for AI injection
    watchlist: list[str] = Field(
        default_factory=lambda: [
            "PINS", "NVO", "PYPL", "GOOGL", "AMZN", "MSFT",
            "NVDA", "TSLA", "AMD", "PLTR", "MU", "UBER",
            "NFLX", "ADBE", "AVGO", "IBM", "V", "NU", "META",
        ]
    )
    # Track classification: A=방어형 가치주, B=공격형 성장주
    track_a: list[str] = Field(
        default_factory=lambda: ["V", "PYPL", "IBM", "NU"]
    )
    track_b: list[str] = Field(
        default_factory=lambda: [
            "NVDA", "AMD", "AVGO", "MU", "GOOGL", "AMZN",
            "MSFT", "TSLA", "PLTR", "NFLX", "ADBE", "UBER", "META",
        ]
    )

    # -- Engine 3: Warehouse LAA --
    warehouse_allocations: dict[str, float] = Field(
        default_factory=lambda: {
            "SPY": 0.25,
            "QQQ": 0.10,
            "TLT": 0.30,
            "IEF": 0.10,
            "GLD": 0.15,
            "SHY": 0.10,
        }
    )
    weekly_rsi_overbought: float = 70.0
    weekly_rsi_oversold: float = 30.0
    nasdaq_crash_pct: float = -3.0
    rebalance_deviation_pct: float = 5.0
    momentum_lookback_months: int = 12

    # -- Auto-refresh (seconds) --
    refresh_interval_sec: int = 300


@lru_cache()
def get_settings() -> Settings:
    return Settings()
