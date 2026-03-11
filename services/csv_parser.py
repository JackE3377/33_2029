# ============================================================
# GEM Protocol — CSV Parser for Magic Split Portfolio
# ============================================================
"""
Reads the local CSV/Excel file exported by the external
'Magic Split' program and returns structured position data.

Handles:
  - File lock detection (copies before reading)
  - Encoding fallback (UTF-8 → EUC-KR)
  - Schema validation
"""
from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from core.config import get_settings
from core.logger import get_logger

logger = get_logger("csv_parser")


@dataclass
class MagicSplitPosition:
    """Single position from Magic Split program."""
    symbol: str
    name: str
    quantity: float
    avg_price: float
    current_price: float
    pnl_pct: float
    split_count: int         # 현재 분할 매수 횟수
    target_buy_price: float  # 다음 분할 매수 목표가
    target_sell_price: float # 목표 매도가
    market: str              # "KR" or "US"


# Expected column mappings (Magic Split 프로그램 실제 컬럼명 → 내부 필드)
COLUMN_MAP = {
    "코드": "symbol",
    "종목명": "name",
    "수량": "quantity",
    "매입가": "avg_price",
    "현재가": "current_price",
    "수익률": "pnl_pct",
    "매입금액": "total_invested",
    "평가금액": "total_value",
    "평가손익": "pnl_amount",
    "등락": "daily_change",
    "인덱스": "index_num",
    # English fallback
    "symbol": "symbol",
    "name": "name",
    "qty": "quantity",
    "avg_price": "avg_price",
    "cur_price": "current_price",
    "pnl_pct": "pnl_pct",
    "split_cnt": "split_count",
    "target_buy": "target_buy_price",
    "target_sell": "target_sell_price",
    "market": "market",
}

# Columns that contain split-buy level prices (1차 ~ 50차)
SPLIT_LEVEL_PREFIX = "차"


def parse_magic_split_file(
    file_path: Optional[str] = None,
) -> list[MagicSplitPosition]:
    """
    Parse the Magic Split CSV/Excel file.

    To avoid file-lock conflicts, copies the file to a temp location first.
    Falls back from UTF-8 to EUC-KR encoding if needed.
    """
    settings = get_settings()
    path = Path(file_path or settings.magic_split_csv_path)

    if not path.exists():
        logger.warning(f"Magic Split file not found: {path}")
        return []

    # Copy to temp to avoid file-lock conflicts
    tmp = Path(tempfile.gettempdir()) / f"gem_ms_{path.name}"
    try:
        shutil.copy2(path, tmp)
    except PermissionError:
        logger.error(f"Cannot copy Magic Split file (locked?): {path}")
        return []

    # Read with encoding fallback
    df = _read_file(tmp, settings.magic_split_csv_encoding)
    if df is None or df.empty:
        logger.warning("Magic Split file is empty or unreadable")
        return []

    # Map columns
    df = _map_columns(df)
    required = {"symbol", "quantity", "avg_price", "current_price"}
    if not required.issubset(set(df.columns)):
        missing = required - set(df.columns)
        logger.error(f"Missing required columns in Magic Split file: {missing}")
        return []

    # Count split levels from 1차~50차 columns
    split_cols = [c for c in df.columns if c.endswith(SPLIT_LEVEL_PREFIX) and c[:-1].isdigit()]

    # Parse rows
    positions: list[MagicSplitPosition] = []
    for _, row in df.iterrows():
        try:
            symbol = str(row.get("symbol", "")).strip()
            if not symbol:
                continue

            # split_count = number of non-NaN split level columns
            split_count = sum(1 for c in split_cols if pd.notna(row.get(c)))

            # Parse numeric values, stripping commas
            qty = _parse_num(row.get("quantity", 0))
            avg_p = _parse_num(row.get("avg_price", 0))
            cur_p = _parse_num(row.get("current_price", 0))
            pnl = _parse_num(row.get("pnl_pct", 0))

            pos = MagicSplitPosition(
                symbol=symbol,
                name=str(row.get("name", "")).strip(),
                quantity=qty,
                avg_price=avg_p,
                current_price=cur_p,
                pnl_pct=pnl,
                split_count=split_count,
                target_buy_price=0.0,   # Calculated by engine
                target_sell_price=0.0,  # Calculated by engine
                market="US",
            )
            positions.append(pos)
        except (ValueError, TypeError) as e:
            logger.warning(f"Skipping invalid row: {e}")

    logger.info(f"Parsed {len(positions)} positions from Magic Split file")
    return positions


def _parse_num(val) -> float:
    """Parse a numeric value that may contain commas or be a string."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    return float(str(val).replace(",", "").strip())


def _read_file(path: Path, encoding: str) -> Optional[pd.DataFrame]:
    """Read CSV or Excel with encoding fallback."""
    suffix = path.suffix.lower()

    if suffix in (".xlsx", ".xls"):
        try:
            return pd.read_excel(path)
        except Exception as e:
            logger.error(f"Excel read error: {e}")
            return None

    # CSV — try primary encoding, then fallback
    for enc in [encoding, "euc-kr", "cp949", "utf-8-sig"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception as e:
            logger.error(f"CSV read error ({enc}): {e}")
            return None

    logger.error("All encoding attempts failed for CSV file")
    return None


def _map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns using known mapping."""
    rename = {}
    for col in df.columns:
        col_stripped = col.strip()
        if col_stripped in COLUMN_MAP:
            rename[col] = COLUMN_MAP[col_stripped]
    return df.rename(columns=rename)
