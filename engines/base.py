# ============================================================
# GEM Protocol — Engine Base Class
# ============================================================
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from core.config import get_settings, TradingMode
from core.logger import get_logger
from core.models import EngineType


@dataclass
class EngineStatus:
    """Runtime status of an engine."""
    engine: EngineType
    is_running: bool = False
    is_paused: bool = False
    last_run: Optional[datetime] = None
    last_error: Optional[str] = None
    cycle_count: int = 0


class BaseEngine(ABC):
    """Abstract base for all trading engines."""

    def __init__(self, engine_type: EngineType):
        self.engine_type = engine_type
        self.settings = get_settings()
        self.logger = get_logger(engine_type.value)
        self.status = EngineStatus(engine=engine_type)

    @abstractmethod
    def run_cycle(self) -> dict:
        """Execute one cycle of the engine logic. Returns summary dict."""
        ...

    def execute(self) -> dict:
        """Wrapper that handles pausing, error capture, and status updates."""
        if self.status.is_paused:
            self.logger.info(f"{self.engine_type.value} is PAUSED — skipping cycle")
            return {"status": "paused"}

        self.status.is_running = True
        try:
            result = self.run_cycle()
            self.status.cycle_count += 1
            self.status.last_run = datetime.now(timezone.utc)
            self.status.last_error = None
            return result
        except Exception as e:
            self.status.last_error = str(e)
            self.logger.error(f"Engine cycle failed: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
        finally:
            self.status.is_running = False

    def pause(self):
        self.status.is_paused = True
        self.logger.info(f"{self.engine_type.value} PAUSED")

    def resume(self):
        self.status.is_paused = False
        self.logger.info(f"{self.engine_type.value} RESUMED")

    @property
    def is_paper(self) -> bool:
        return self.settings.is_paper
