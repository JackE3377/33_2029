# ============================================================
# GEM Protocol v3 — Signal Engine (Rule-Based)
# ============================================================
"""
Signal generators:
  1  — Tether Arbitrage (kimchi premium)
  1b — Dollar split buy/sell (5-min intraday FX)
  1c — Yen split buy/sell (5-min intraday FX)
  2  — Dollar Index (DXY) technical analysis
  3  — Warehouse LAA dynamic rebalancing
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from core.config import get_settings
from services.data_fetcher import (
    MacroData, StockQuote, CryptoQuote, DXYData, JPYData, FXIntraday,
)


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
        sig.alerts.append(f"🔴 테더 매도 → 달러 전환 (김프 {crypto.kimchi_premium_pct:+.2f}%)")
    elif crypto.kimchi_premium_pct <= cfg.kimchi_premium_buy_pct:
        sig.action = "BUY_USDT"
        sig.alerts.append(f"🟢 달러 → 테더 전환 (역프 {crypto.kimchi_premium_pct:+.2f}%)")
    return sig


# ── Engine 1b: FX Split Buy/Sell ──────────────────────────────

@dataclass
class FXSplitSignal:
    currency: str = "USD"       # USD / JPY
    current: float = 0.0
    action: str = "HOLD"        # BUY / SELL / HOLD
    urgency: int = 0
    label: str = "관망"
    detail: str = ""
    buy_levels: list[float] = field(default_factory=list)
    sell_levels: list[float] = field(default_factory=list)
    rsi_5m: Optional[float] = None
    support: float = 0.0
    resistance: float = 0.0
    market_open: bool = True
    entry_score: int = 0        # 0-100: 진입 적합도 (higher = better entry)
    entry_rationale: str = ""   # 진입 근거 요약


def calc_fx_split_signal(
    intraday: FXIntraday,
    buy_interval: float,
    sell_interval: float,
    dxy: 'DXYData | None' = None,
) -> FXSplitSignal:
    """FX split buy/sell with DXY-backed entry evaluation.

    Mechanical intervals are replaced by support/resistance-based levels.
    Entry decision uses: DXY bounce_score, DXY RSI, FX 5m RSI, support proximity.
    """
    sig = FXSplitSignal(
        currency=intraday.symbol,
        current=intraday.current,
        rsi_5m=intraday.rsi_5m,
        support=intraday.support,
        resistance=intraday.resistance,
        market_open=intraday.market_open,
    )

    if not intraday.market_open or intraday.current <= 0:
        sig.label = "시장 휴장"
        sig.detail = "데이터 갱신 대기 중"
        return sig

    price = intraday.current
    rsi = intraday.rsi_5m
    sup = intraday.support
    res = intraday.resistance

    # ── Entry Score: 0-100 (종합 진입 적합도) ─────────────────
    score = 50
    rationale_parts = []

    # Factor 1: DXY bounce probability (30 pts max)
    if dxy and dxy.bounce_score is not None:
        # DXY 반등 가능성 높으면 → 원화 약세(환율↑) → 달러 매수 유리
        if intraday.symbol == "USD":
            dxy_contrib = int((dxy.bounce_score - 50) * 0.6)  # -30 ~ +30
        else:
            # 엔화: DXY 약세(반등↓)면 엔화 강세 → 엔화 매수 유리
            dxy_contrib = int((50 - dxy.bounce_score) * 0.4)  # -20 ~ +20
        score += dxy_contrib
        if dxy.bounce_score >= 65:
            rationale_parts.append(f"DXY 반등↑{dxy.bounce_score}")
        elif dxy.bounce_score <= 35:
            rationale_parts.append(f"DXY 추가하락↓{dxy.bounce_score}")

    # Factor 2: DXY RSI (15 pts max)
    if dxy and dxy.rsi_14 is not None:
        dxy_rsi = dxy.rsi_14
        if intraday.symbol == "USD":
            if dxy_rsi < 30:
                score += 15
                rationale_parts.append(f"DXY RSI {dxy_rsi:.0f} 과매도")
            elif dxy_rsi < 40:
                score += 8
            elif dxy_rsi > 70:
                score -= 15
                rationale_parts.append(f"DXY RSI {dxy_rsi:.0f} 과매수")
            elif dxy_rsi > 60:
                score -= 8
        else:  # JPY: inverse relationship
            if dxy_rsi > 70:
                score += 10
            elif dxy_rsi < 30:
                score -= 10

    # Factor 3: FX 5-min RSI (20 pts max)
    if rsi is not None:
        if rsi < 30:
            score += 20
            rationale_parts.append(f"FX RSI {rsi:.0f} 과매도")
        elif rsi < 40:
            score += 10
            rationale_parts.append(f"FX RSI {rsi:.0f} 저점")
        elif rsi > 70:
            score -= 20
            rationale_parts.append(f"FX RSI {rsi:.0f} 과매수")
        elif rsi > 60:
            score -= 10

    # Factor 4: Support proximity (15 pts max)
    if sup > 0:
        sup_dist = price - sup
        pct_from_sup = (sup_dist / price) * 100 if price > 0 else 99
        if pct_from_sup < 0.2:
            score += 15
            rationale_parts.append("지지선 도달")
        elif pct_from_sup < 0.5:
            score += 8
            rationale_parts.append("지지선 접근")

    # Factor 5: SMA position (10 pts max)
    if intraday.sma_20 and price < intraday.sma_20:
        score += 5  # below 20-bar SMA → mean-reversion buy
    if intraday.sma_50 and price < intraday.sma_50:
        score += 5

    sig.entry_score = max(0, min(100, score))
    sig.entry_rationale = " · ".join(rationale_parts) if rationale_parts else "특이사항 없음"

    # ── Buy/Sell Levels: support/resistance-based ─────────────
    # Buy levels: support 기준으로 분산 (support 근처에 밀집)
    if sup > 0:
        gap_to_sup = price - sup
        if gap_to_sup > 0:
            sig.buy_levels = [
                round(price - gap_to_sup * 0.25, 1),  # 25% toward support
                round(price - gap_to_sup * 0.50, 1),  # 50% (halfway)
                round(sup + buy_interval, 1),          # just above support
                round(sup, 1),                         # support itself
            ]
        else:
            # Already at/below support: use intervals below
            for i in range(1, 5):
                sig.buy_levels.append(round(price - buy_interval * i, 1))
    else:
        for i in range(1, 5):
            sig.buy_levels.append(round(price - buy_interval * i, 1))

    # Sell levels: resistance 기준으로 분산
    if res > 0 and res > price:
        gap_to_res = res - price
        sig.sell_levels = [
            round(price + gap_to_res * 0.25, 1),
            round(price + gap_to_res * 0.50, 1),
            round(res - sell_interval, 1),
            round(res, 1),
        ]
    else:
        for i in range(1, 5):
            sig.sell_levels.append(round(price + sell_interval * i, 1))

    # ── Action decision based on entry_score ──────────────────
    if sig.entry_score >= 75:
        sig.action = "BUY"
        sig.urgency = 3
        sig.label = "분할 매수 적기"
        sig.detail = (
            f"₩{price:,.1f} · 진입점수 {sig.entry_score}/100 · "
            f"{sig.entry_rationale}"
        )
    elif sig.entry_score >= 60:
        sig.action = "BUY"
        sig.urgency = 2
        sig.label = "매수 검토"
        sig.detail = (
            f"₩{price:,.1f} · 진입점수 {sig.entry_score}/100 · "
            f"{sig.entry_rationale}"
        )
    elif sig.entry_score <= 25:
        sig.action = "SELL"
        sig.urgency = 3
        sig.label = "분할 매도 구간"
        sig.detail = (
            f"₩{price:,.1f} · 진입점수 {sig.entry_score}/100 · "
            f"{sig.entry_rationale}"
        )
    elif sig.entry_score <= 40:
        sig.action = "SELL"
        sig.urgency = 2
        sig.label = "매도 검토"
        sig.detail = (
            f"₩{price:,.1f} · 진입점수 {sig.entry_score}/100 · "
            f"{sig.entry_rationale}"
        )
    else:
        rsi_str = f"RSI {rsi:.0f}" if rsi is not None else "RSI —"
        sig.label = "관망"
        sig.detail = (
            f"₩{price:,.1f} · 진입점수 {sig.entry_score}/100 · "
            f"{rsi_str}"
        )

    return sig


# ── Engine 1c: Dollar Index (DXY) ─────────────────────────────

@dataclass
class DollarSignal:
    dxy_price: float = 0.0
    dxy_rsi: float | None = None
    usd_krw: float = 0.0
    action: str = "HOLD"
    urgency: int = 0
    label: str = "관망"
    detail: str = ""


def calc_dollar_signal(dxy: DXYData, macro: MacroData) -> DollarSignal:
    sig = DollarSignal(
        dxy_price=dxy.price,
        dxy_rsi=dxy.rsi_14,
        usd_krw=macro.usd_krw,
    )
    rsi = dxy.rsi_14
    if rsi is None:
        return sig

    if rsi < 30:
        sig.action = "BUY_USD"
        sig.urgency = 3
        sig.label = "달러 강세 반등 가능"
        sig.detail = f"DXY RSI {rsi:.0f} 과매도 · 반등 확률 {dxy.bounce_score}/100"
    elif rsi < 40:
        sig.action = "BUY_USD"
        sig.urgency = 2
        sig.label = "달러 저점 접근"
        sig.detail = f"DXY RSI {rsi:.0f} · {dxy.bounce_label}"
    elif rsi > 70:
        sig.action = "SELL_USD"
        sig.urgency = 3
        sig.label = "달러 약세 전환 가능"
        sig.detail = f"DXY RSI {rsi:.0f} 과매수 · 추가 상승 제한적"
    elif rsi > 60:
        sig.action = "SELL_USD"
        sig.urgency = 1
        sig.label = "달러 고점 관심"
        sig.detail = f"DXY RSI {rsi:.0f} 고점 접근"
    else:
        sig.label = "관망"
        sig.detail = f"DXY {dxy.price:.1f} · RSI {rsi:.0f} 중립"

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


# ── Engine 3: Warehouse LAA Dynamic Rebalance ─────────────────

@dataclass
class WarehouseSignal:
    symbol: str = ""
    status: str = "normal"       # hot / cold / panic / normal / momentum_off
    rsi: float | None = None
    label: str = ""
    target_pct: float = 0.0      # target allocation %
    current_value: float = 0.0   # current $ value per unit
    momentum_12m: float | None = None   # 12-month return %
    above_200dma: bool | None = None    # price > 200-day MA?
    invest_amount: float = 0.0   # 추가 투입 금액 (원)


def calc_warehouse_signals(
    quotes: list[StockQuote],
    macro: MacroData,
    total_investment: float = 0.0,
) -> list[WarehouseSignal]:
    """Dynamic rebalancing with Dual Momentum + RSI + NASDAQ panic.

    total_investment: 총 투자금 (원화). 0이면 금액 안내 생략.
    """
    import yfinance as yf

    cfg = get_settings()
    signals: list[WarehouseSignal] = []
    allocations = cfg.warehouse_allocations

    # Calculate total target value per asset
    total_target = {}
    for sym, pct in allocations.items():
        total_target[sym] = total_investment * pct if total_investment > 0 else 0

    for q in quotes:
        if q.symbol not in allocations:
            continue

        target_pct = allocations.get(q.symbol, 0)
        sig = WarehouseSignal(
            symbol=q.symbol,
            rsi=q.weekly_rsi if q.weekly_rsi is not None else q.rsi_14,
            target_pct=target_pct,
            current_value=q.price,
        )

        # 12-month momentum: fetch 1-year history
        try:
            hist_1y = yf.Ticker(q.symbol).history(period="1y")
            if len(hist_1y) >= 200:
                first_price = float(hist_1y["Close"].iloc[0])
                last_price = float(hist_1y["Close"].iloc[-1])
                sig.momentum_12m = round(((last_price / first_price) - 1) * 100, 2) if first_price > 0 else None

                # 200-day moving average
                sma_200 = float(hist_1y["Close"].rolling(200).mean().iloc[-1])
                sig.above_200dma = last_price > sma_200
        except Exception:
            pass

        # RSI-based status
        rsi = sig.rsi
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

        # Dual Momentum override: negative 12m return → momentum_off
        if sig.momentum_12m is not None and sig.momentum_12m < 0:
            sig.status = "momentum_off"
            sig.label = (
                f"⚠️ 절대모멘텀 음수 ({sig.momentum_12m:+.1f}%) — "
                f"SHY(단기채) 대체 검토"
            )

        # Calculate investment amount needed
        if total_investment > 0:
            target_value = total_target.get(q.symbol, 0)
            sig.invest_amount = round(target_value, 0)

        signals.append(sig)

    # NASDAQ crash detection
    if macro.nasdaq_daily_chg_pct <= cfg.nasdaq_crash_pct:
        signals.insert(0, WarehouseSignal(
            symbol="NASDAQ",
            status="panic",
            rsi=None,
            label=f"🚨 패닉 — 나스닥 {macro.nasdaq_daily_chg_pct:+.2f}% 급락! 리밸런싱 검토",
        ))

    # NASDAQ 200-day MA warning
    try:
        nq_hist = yf.Ticker("^IXIC").history(period="1y")
        if len(nq_hist) >= 200:
            nq_price = float(nq_hist["Close"].iloc[-1])
            nq_200 = float(nq_hist["Close"].rolling(200).mean().iloc[-1])
            if nq_price < nq_200:
                signals.insert(0, WarehouseSignal(
                    symbol="NASDAQ-200MA",
                    status="cold",
                    rsi=None,
                    label=f"📉 나스닥 200일 이평선 하회 — 방어적 배분 강화 권고",
                ))
    except Exception:
        pass

    return signals
