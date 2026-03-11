# ============================================================
# GEM Protocol — Core Settings (Pydantic Settings)
# ============================================================
from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class Settings(BaseSettings):
    """Single source of truth for all configurable parameters."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(cls, settings_cls, **kwargs):
        """Load Streamlit Cloud secrets into env vars before Pydantic reads them."""
        try:
            import streamlit as st
            if hasattr(st, "secrets") and len(st.secrets) > 0:
                for key, val in st.secrets.items():
                    if isinstance(val, str):
                        os.environ.setdefault(key.upper(), val)
        except Exception:
            pass
        return super().settings_customise_sources(settings_cls, **kwargs)

    # -- App Mode --
    trading_mode: TradingMode = TradingMode.PAPER

    # -- Database --
    database_url: str = "sqlite:///./data/gem_protocol.db"

    # -- LLM --
    gemini_api_key: str = ""
    openai_api_key: str = ""
    llm_monthly_budget_usd: float = 50.0

    # -- Exchange --
    bithumb_api_key: str = ""
    bithumb_secret_key: str = ""

    # -- Brokerage --
    kis_app_key: str = ""
    kis_app_secret: str = ""
    kis_account_no: str = ""

    # -- Data --
    fred_api_key: str = ""
    alpha_vantage_api_key: str = ""

    # -- Telegram --
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # -- Dashboard --
    dashboard_password: str = "changeme"

    # -- Magic Split --
    magic_split_csv_path: str = "C:/MagicSplit/portfolio.csv"
    magic_split_csv_encoding: str = "utf-8"

    # -- Scheduler Intervals (seconds) --
    engine1_interval_sec: int = 300
    engine2_interval_sec: int = 60
    engine3_interval_sec: int = 3600

    # -- Risk Management --
    daily_max_loss_pct: float = 2.0
    single_position_max_pct: float = 10.0
    circuit_breaker_vix: float = 50.0
    black_swan_sp500_drop_pct: float = 7.0

    # -- Macro Filters --
    usdkrw_block_threshold: float = 1400.0
    vix_leverage_block: float = 30.0

    # -- Engine 1 Thresholds --
    kimchi_premium_sell_pct: float = 3.0
    kimchi_premium_buy_pct: float = -1.0

    # -- Engine 2 Thresholds --
    forward_pe_max: float = 15.0
    peg_max: float = 1.5
    rsi_entry: float = 30.0
    split_buy_drop_pcts: list[float] = Field(default_factory=lambda: [-5.0, -10.0])
    take_profit_pct: float = 5.0
    stop_loss_pct: float = -20.0
    max_split_count: int = 3
    initial_position_pct: float = 3.0

    # -- Engine 3 Thresholds --
    rebalance_deviation_pct: float = 5.0
    weekly_rsi_overbought: float = 70.0
    weekly_rsi_oversold: float = 30.0
    nasdaq_crash_pct: float = -3.0

    # -- Engine 3 Target Allocation --
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

    @property
    def is_paper(self) -> bool:
        return self.trading_mode == TradingMode.PAPER

    @property
    def data_dir(self) -> Path:
        p = Path("data")
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def logs_dir(self) -> Path:
        p = Path("logs")
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton settings instance."""
    return Settings()
