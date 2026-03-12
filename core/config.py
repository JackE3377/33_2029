# ============================================================
# GEM Protocol v2 — Core Settings
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

    # -- Data APIs --
    fred_api_key: str = ""
    alpha_vantage_api_key: str = ""

    # -- Engine 1: Tether Thresholds --
    kimchi_premium_sell_pct: float = 3.0
    kimchi_premium_buy_pct: float = -1.0
    usdkrw_block_threshold: float = 1400.0

    # -- Engine 2: Magic Split Screening --
    forward_pe_max: float = 15.0
    peg_max: float = 1.5
    rsi_entry: float = 30.0
    watchlist: list[str] = Field(
        default_factory=lambda: [
            "PINS", "NVO", "PYPL", "GOOGL", "AMZN", "MSFT",
            "NVDA", "TSLA", "AMD", "PLTR", "MU", "UBER",
            "NFLX", "ADBE", "AVGO", "IBM", "V", "NU",
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

    # -- Auto-refresh (seconds) --
    refresh_interval_sec: int = 300


@lru_cache()
def get_settings() -> Settings:
    return Settings()
