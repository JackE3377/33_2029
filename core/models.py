# ============================================================
# GEM Protocol — Database Models (SQLAlchemy ORM)
# ============================================================
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from core.config import get_settings

import enum


# ---------- Enums ----------

class EngineType(str, enum.Enum):
    ENGINE1_TETHER = "engine1_tether"
    ENGINE2_MAGIC = "engine2_magic"
    ENGINE3_WAREHOUSE = "engine3_warehouse"


class OrderSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class AlertPriority(str, enum.Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class TradeStatus(str, enum.Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    SIMULATED = "simulated"


# ---------- Base ----------

class Base(DeclarativeBase):
    pass


# ---------- Models ----------

class TradeLog(Base):
    """Immutable audit trail for every trade decision."""
    __tablename__ = "trade_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    engine = Column(SAEnum(EngineType), nullable=False, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(SAEnum(OrderSide), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    status = Column(SAEnum(TradeStatus), default=TradeStatus.PENDING)
    reason = Column(Text, default="")
    llm_model_used = Column(String(50), default="")
    is_paper = Column(Boolean, default=True)


class PositionSnapshot(Base):
    """Point-in-time snapshot of portfolio positions."""
    __tablename__ = "position_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    engine = Column(SAEnum(EngineType), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    avg_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    pnl_pct = Column(Float, nullable=False)
    weight_pct = Column(Float, nullable=False)


class AlertHistory(Base):
    """All alerts sent, with acknowledgement tracking."""
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    priority = Column(SAEnum(AlertPriority), nullable=False, index=True)
    engine = Column(SAEnum(EngineType), nullable=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    acknowledged = Column(Boolean, default=False)
    ack_timestamp = Column(DateTime, nullable=True)


class PerformanceDaily(Base):
    """Daily performance tracking for analytics."""
    __tablename__ = "performance_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True, unique=True)
    total_asset_krw = Column(Float, nullable=False)
    daily_return_pct = Column(Float, nullable=False)
    cumulative_return_pct = Column(Float, nullable=False)
    max_drawdown_pct = Column(Float, nullable=False)
    sharpe_ratio = Column(Float, nullable=True)
    engine1_pnl = Column(Float, default=0.0)
    engine2_pnl = Column(Float, default=0.0)
    engine3_pnl = Column(Float, default=0.0)


class LLMUsageLog(Base):
    """Track LLM API usage for budget control."""
    __tablename__ = "llm_usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    model = Column(String(50), nullable=False)
    task_type = Column(String(50), nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)


class MacroSnapshot(Base):
    """Periodic macro indicator snapshots."""
    __tablename__ = "macro_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    usd_krw = Column(Float, nullable=True)
    vix = Column(Float, nullable=True)
    sp500_daily_chg_pct = Column(Float, nullable=True)
    nasdaq_daily_chg_pct = Column(Float, nullable=True)
    fed_funds_rate = Column(Float, nullable=True)


class EngineResult(Base):
    """Latest engine execution result — JSON blob for dashboard lookup."""
    __tablename__ = "engine_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    engine = Column(SAEnum(EngineType), nullable=False, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    result_json = Column(Text, nullable=False)   # JSON-encoded result dict
    status = Column(String(20), default="ok")     # ok / error / blocked


# ---------- Engine & Session Factory ----------

_engine = None
_SessionLocal = None


def get_db_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            echo=False,
            connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
        )
        Base.metadata.create_all(bind=_engine)
    return _engine


def get_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_db_engine())
    return _SessionLocal()
