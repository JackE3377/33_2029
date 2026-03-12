# ============================================================
# GEM Protocol v3 — LAA Portfolio Store (JSON-based)
# ============================================================
"""
Stores LAA portfolio configuration in data/laa_portfolio.json.
Designed to be git-committed so Streamlit Cloud can read it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PORTFOLIO_FILE = _DATA_DIR / "laa_portfolio.json"


@dataclass
class LAAPortfolio:
    total_investment: float = 0.0   # 총 투자금 (원화)
    allocations: dict[str, float] = field(default_factory=dict)  # symbol → target %


def load_portfolio() -> LAAPortfolio:
    """Load LAA portfolio from JSON file."""
    if _PORTFOLIO_FILE.exists():
        try:
            raw = json.loads(_PORTFOLIO_FILE.read_text(encoding="utf-8"))
            return LAAPortfolio(
                total_investment=float(raw.get("total_investment", 0)),
                allocations=raw.get("allocations", {}),
            )
        except (json.JSONDecodeError, ValueError):
            pass
    return LAAPortfolio()


def save_portfolio(portfolio: LAAPortfolio) -> None:
    """Save LAA portfolio to JSON file."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "total_investment": portfolio.total_investment,
        "allocations": portfolio.allocations,
    }
    _PORTFOLIO_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
