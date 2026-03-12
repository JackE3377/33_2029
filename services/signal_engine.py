# ============================================================
# GEM Protocol v2 — Signal Engine (Rule-Based)
# ============================================================
"""
Pure rule-based signal generators for the 3 engines:
  Engine 1 — Tether Arbitrage signals
  Engine 2 — Magic Split entry signals
  Engine 3 — Warehouse rebalance signals
"""
from __future__ import annotations

from dataclasses import dataclass

from core.config import get_settings
from services.data_fetcher import MacroData, StockQuote, CryptoQuote


# ── Engine 1: Tether ──────────────────────────────────────────

@dataclass
class TetherSignal:
    premium_pct: float = 0.0
    usd_krw: float = 0.0
    action: str = "HOLD"       # SELL_USDT / BUY_USDT / HOLD
    alerts: list[str] = None

    def __post_init__(self):
        if self.alerts is None:
            self.alerts = []


def calc_tether_signal(macro: MacroData, crypto: CryptoQuote) -> TetherSignal:
    cfg = get_settings()
    sig = TetherSignal(
        premium_pct=crypto.kimchi_premium_pct,
        usd_krw=macro.usd_krw,
    )
    if crypto.kimchi_premium_pct >= cfg.kimchi_premium_sell_pct:
        sig.action = "SELL_USDT"
        sig.alerts.append(f"🔴 테더 매도 (김프 {crypto.kimchi_premium_pct:+.2f}%) — 원화 확보 타이밍")
    elif crypto.kimchi_premium_pct <= cfg.kimchi_premium_buy_pct:
        sig.action = "BUY_USDT"
        sig.alerts.append(f"🟢 테더 매수 (역프 {crypto.kimchi_premium_pct:+.2f}%) — 달러 전환 기회")
    if macro.usd_krw >= cfg.usdkrw_block_threshold:
        sig.alerts.append(f"⚠️ 환전 금지 구간 (USD/KRW {macro.usd_krw:,.0f}원 ≥ {cfg.usdkrw_block_threshold:,.0f}원)")
    return sig


# ── Engine 2: Magic Split Screening ──────────────────────────

@dataclass
class MagicSignal:
    symbol: str = ""
    reason: str = ""
    action: str = "WATCH"      # SCOUT / WATCH


def calc_magic_signals(quotes: list[StockQuote]) -> list[MagicSignal]:
    cfg = get_settings()
    signals: list[MagicSignal] = []
    for q in quotes:
        if q.price <= 0:
            continue
        meets_valuation = (
            (q.peg_ratio is not None and q.peg_ratio < cfg.peg_max)
            and (q.forward_pe is not None and q.forward_pe < cfg.forward_pe_max)
        )
        meets_rsi = q.rsi_14 is not None and q.rsi_14 < cfg.rsi_entry
        if meets_valuation and meets_rsi:
            signals.append(MagicSignal(
                symbol=q.symbol,
                reason=f"RSI {q.rsi_14:.1f} + PE {q.forward_pe:.1f} + PEG {q.peg_ratio:.2f}",
                action="SCOUT",
            ))
        elif meets_rsi:
            signals.append(MagicSignal(
                symbol=q.symbol,
                reason=f"RSI {q.rsi_14:.1f} (밸류에이션 미충족)",
                action="WATCH",
            ))
    return signals


# ── Engine 3: Warehouse Rebalance ─────────────────────────────

@dataclass
class WarehouseSignal:
    symbol: str = ""
    status: str = "normal"     # hot / cold / panic / normal
    rsi: float | None = None
    label: str = ""


def calc_warehouse_signals(
    quotes: list[StockQuote],
    macro: MacroData,
) -> list[WarehouseSignal]:
    cfg = get_settings()
    signals: list[WarehouseSignal] = []

    # Per-asset RSI signals
    for q in quotes:
        rsi = q.weekly_rsi if q.weekly_rsi is not None else q.rsi_14
        sig = WarehouseSignal(symbol=q.symbol, rsi=rsi)
        if rsi is not None:
            if rsi > cfg.weekly_rsi_overbought:
                sig.status = "hot"
                sig.label = f"🔥 과열 — 비중 축소 권고 (RSI {rsi:.0f})"
            elif rsi < cfg.weekly_rsi_oversold:
                sig.status = "cold"
                sig.label = f"❄️ 침체 — 비중 확대 권고 (RSI {rsi:.0f})"
            else:
                sig.status = "normal"
                sig.label = f"✅ 정상 (RSI {rsi:.0f})"
        else:
            sig.label = "— RSI 데이터 없음"
        signals.append(sig)

    # NASDAQ crash detection
    if macro.nasdaq_daily_chg_pct <= cfg.nasdaq_crash_pct:
        signals.insert(0, WarehouseSignal(
            symbol="NASDAQ",
            status="panic",
            rsi=None,
            label=f"🚨 패닉 셀링 — 나스닥 {macro.nasdaq_daily_chg_pct:+.2f}% 급락! 동적 리밸런싱 즉각 실행",
        ))

    return signals
