# ============================================================
# GEM Protocol — Alert & Notification System
# ============================================================
"""
Multi-channel alert system:
  - Streamlit banner (stored in session state)
  - Telegram push notification
  - 3 priority levels: CRITICAL / WARNING / INFO
  - Throttling: same event cannot re-fire within cooldown period
  - ACK tracking for CRITICAL alerts
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests

from core.config import get_settings
from core.logger import get_logger
from core.models import AlertHistory, AlertPriority, EngineType, get_session

logger = get_logger("alerts")

# Cooldown per unique alert key (seconds)
COOLDOWN_SECONDS = {
    AlertPriority.CRITICAL: 60,     # 1 min — repeat until ACK'd
    AlertPriority.WARNING: 300,     # 5 min
    AlertPriority.INFO: 600,        # 10 min
}


@dataclass
class Alert:
    priority: AlertPriority
    title: str
    message: str
    engine: Optional[EngineType] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AlertManager:
    """
    Manages alert lifecycle: creation → throttle check → send → persist → ACK.
    
    Usage:
        alerts = AlertManager()
        alerts.send(Alert(
            priority=AlertPriority.CRITICAL,
            title="Circuit Breaker Activated",
            message="Daily loss exceeded -2%. All engines paused.",
        ))
    """

    def __init__(self):
        self._settings = get_settings()
        self._last_sent: dict[str, float] = {}  # key → unix timestamp
        self._pending_banners: list[Alert] = []

    @property
    def pending_banners(self) -> list[Alert]:
        """Alerts to display as banners on the Streamlit dashboard."""
        return list(self._pending_banners)

    def clear_banners(self):
        self._pending_banners.clear()

    def send(self, alert: Alert) -> bool:
        """
        Send an alert through all channels.
        Returns True if sent (not throttled).
        """
        key = f"{alert.priority.value}:{alert.title}"

        # Throttle check
        if self._is_throttled(key, alert.priority):
            logger.debug(f"Alert throttled: {key}")
            return False

        self._last_sent[key] = time.time()

        # Add to dashboard banners
        self._pending_banners.append(alert)

        # Persist to DB
        self._persist(alert)

        # Send Telegram
        self._send_telegram(alert)

        logger.info(f"Alert sent [{alert.priority.value}]: {alert.title}")
        return True

    def get_unacknowledged(self) -> list[AlertHistory]:
        """Get all unacknowledged CRITICAL alerts."""
        session = get_session()
        try:
            return (
                session.query(AlertHistory)
                .filter(
                    AlertHistory.priority == AlertPriority.CRITICAL,
                    AlertHistory.acknowledged == False,
                )
                .order_by(AlertHistory.timestamp.desc())
                .all()
            )
        finally:
            session.close()

    def acknowledge(self, alert_id: int) -> bool:
        """Mark a CRITICAL alert as acknowledged."""
        session = get_session()
        try:
            alert = session.query(AlertHistory).filter_by(id=alert_id).first()
            if alert:
                alert.acknowledged = True
                alert.ack_timestamp = datetime.now(timezone.utc)
                session.commit()
                logger.info(f"Alert #{alert_id} acknowledged")
                return True
            return False
        finally:
            session.close()

    def _is_throttled(self, key: str, priority: AlertPriority) -> bool:
        if key not in self._last_sent:
            return False
        cooldown = COOLDOWN_SECONDS.get(priority, 300)
        elapsed = time.time() - self._last_sent[key]
        return elapsed < cooldown

    def _persist(self, alert: Alert):
        session = get_session()
        try:
            session.add(AlertHistory(
                priority=alert.priority,
                engine=alert.engine,
                title=alert.title,
                message=alert.message,
            ))
            session.commit()
        except Exception as e:
            logger.error(f"Failed to persist alert: {e}")
            session.rollback()
        finally:
            session.close()

    def _send_telegram(self, alert: Alert):
        """Send alert via Telegram Bot API."""
        token = self._settings.telegram_bot_token
        chat_id = self._settings.telegram_chat_id

        if not token or not chat_id or token.startswith("your_"):
            logger.debug("Telegram not configured — skipping")
            return

        emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(
            alert.priority.value, "⚪"
        )

        text = (
            f"{emoji} *GEM Protocol Alert*\n"
            f"*[{alert.priority.value.upper()}]* {alert.title}\n\n"
            f"{alert.message}"
        )

        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                },
                timeout=10,
            )
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
