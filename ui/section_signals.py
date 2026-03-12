# ============================================================
# GEM Protocol v2 — Section 1: 신호등 대시보드 (6-Card Grid)
# ============================================================
from __future__ import annotations

import streamlit as st

from services.signal_engine import (
    TetherSignal, MagicSignal, WarehouseSignal, DollarSignal, YenSignal,
)
from services.stock_analyst import AnalysisResult
from services.index_scanner import ScreenedStock
from services.data_fetcher import CryptoQuote, DXYData, BankRate, JPYData
from ui.components import signal_card_html, data_table, section_title


def _html(s: str):
    st.markdown(s.strip(), unsafe_allow_html=True)


# ── Card builders (return dict with urgency for sorting) ─────

def _card_tether(
    tether: TetherSignal,
    crypto: CryptoQuote | None,
    bank_rates: list[BankRate] | None,
) -> dict:
    icon, title, theme = "💰", "테더 김프/역프", "sc-tether"
    if crypto is None:
        return dict(icon=icon, title=title, label="데이터 없음", detail="", urgency=0, theme=theme)

    prem = crypto.kimchi_premium_pct
    best_buy = min(bank_rates, key=lambda r: r.buy_rate) if bank_rates else None
    best_sell = max(bank_rates, key=lambda r: r.sell_rate) if bank_rates else None

    if prem >= 3.0:
        bank_hint = f" → {best_buy.name}에서 달러 매수" if best_buy else ""
        return dict(
            icon=icon, title=title, theme=theme, urgency=3,
            label=f"테더 매도 → 달러 매수 (김프 {prem:+.2f}%)",
            detail=f"김프 과열 구간{bank_hint}",
        )
    elif prem >= 2.0:
        bank_hint = f" → {best_buy.name}에서 달러 매수" if best_buy else ""
        return dict(
            icon=icon, title=title, theme=theme, urgency=2,
            label=f"테더 매도 검토 (김프 {prem:+.2f}%)",
            detail=f"매도 기준 도달{bank_hint}",
        )
    elif prem <= -2.0:
        return dict(
            icon=icon, title=title, theme=theme, urgency=3,
            label=f"테더 저가 매수 적기 (역프 {prem:+.2f}%)",
            detail="깊은 역프 — 테더 매수 후 김프 정상화 시 매도",
        )
    elif prem <= -0.5:
        bank_hint = f" → {best_sell.name}에서 달러 매도" if best_sell else ""
        return dict(
            icon=icon, title=title, theme=theme, urgency=2,
            label=f"달러 매도 → 테더 매수 (역프 {prem:+.2f}%)",
            detail=f"역프 구간{bank_hint}",
        )
    else:
        return dict(
            icon=icon, title=title, theme=theme, urgency=0,
            label=f"관망 (김프 {prem:+.2f}%)",
            detail=f"USDT ₩{crypto.price_krw:,.0f}",
        )


def _card_dollar(dollar: DollarSignal | None) -> dict:
    icon, title, theme = "💵", "달러 매매", "sc-dollar"
    if dollar is None:
        return dict(icon=icon, title=title, label="데이터 없음", detail="", urgency=0, theme=theme)
    return dict(
        icon=icon, title=title, theme=theme,
        urgency=dollar.urgency,
        label=dollar.label,
        detail=dollar.detail,
    )


def _card_yen(yen: YenSignal | None) -> dict:
    icon, title, theme = "💴", "엔화 매매", "sc-yen"
    if yen is None:
        return dict(icon=icon, title=title, label="데이터 없음", detail="", urgency=0, theme=theme)
    return dict(
        icon=icon, title=title, theme=theme,
        urgency=yen.urgency,
        label=yen.label,
        detail=yen.detail,
    )


def _card_bank(
    bank_rates: list[BankRate] | None,
    bank_rates_jpy: list[BankRate] | None = None,
) -> dict:
    icon, title, theme = "🏦", "환율 차익", "sc-bank"
    if not bank_rates:
        return dict(icon=icon, title=title, label="데이터 없음", detail="", urgency=0, theme=theme)

    best_buy_usd = min(bank_rates, key=lambda r: r.buy_rate)
    best_sell_usd = max(bank_rates, key=lambda r: r.sell_rate)

    lines = []
    gap_usd = best_sell_usd.sell_rate - best_buy_usd.buy_rate
    gap_str = f" ₩{gap_usd:,.0f}" if gap_usd > 0 else ""
    lines.append(
        f"💵 {best_buy_usd.name} ₩{best_buy_usd.buy_rate:,.0f} → "
        f"{best_sell_usd.name} ₩{best_sell_usd.sell_rate:,.0f}{gap_str}"
    )

    if bank_rates_jpy:
        best_buy_jpy = min(bank_rates_jpy, key=lambda r: r.buy_rate)
        best_sell_jpy = max(bank_rates_jpy, key=lambda r: r.sell_rate)
        gap_jpy = best_sell_jpy.sell_rate - best_buy_jpy.buy_rate
        gap_str_j = f" ₩{gap_jpy:,.0f}" if gap_jpy > 0 else ""
        lines.append(
            f"💴 {best_buy_jpy.name} ₩{best_buy_jpy.buy_rate:,.0f} → "
            f"{best_sell_jpy.name} ₩{best_sell_jpy.sell_rate:,.0f}{gap_str_j}"
        )

    return dict(
        icon=icon, title=title, theme=theme, urgency=1,
        label="매수 최저 · 매도 최고 비교",
        detail="<br>".join(lines),
    )


def _card_stock(
    ai_top: list[AnalysisResult] | None,
    screened: list[ScreenedStock] | None,
) -> dict:
    icon, title, theme = "🚀", "미국 주식 진입", "sc-stock"
    buy_picks = [r for r in (ai_top or []) if r.verdict == "BUY"]

    if buy_picks:
        names = ", ".join(r.symbol for r in buy_picks[:3])
        extra = f" 외 {len(buy_picks)-3}종목" if len(buy_picks) > 3 else ""
        best = buy_picks[0]
        return dict(
            icon=icon, title=title, theme=theme, urgency=2,
            label=f"BUY: {names}{extra}",
            detail=f"Top: {best.symbol} {best.score}점 — "
                   f"{best.synthesis[:80] if best.synthesis else best.bull_summary[:80]}",
        )
    n_screened = len(screened) if screened else 0
    if n_screened > 0:
        return dict(
            icon=icon, title=title, theme=theme, urgency=1,
            label=f"BUY 종목 없음 · 후보 {n_screened}종목 관찰 중",
            detail="스크리닝 대기 — AI 분석 기준 미달",
        )
    return dict(
        icon=icon, title=title, theme=theme, urgency=0,
        label="관망 구간",
        detail="BUY 의견 종목 없음",
    )


def _card_rebalance(warehouse: list[WarehouseSignal]) -> dict:
    icon, title, theme = "🏛️", "자산배분 리밸런싱", "sc-rebal"
    panic = [s for s in warehouse if s.status == "panic"]
    hot = [s for s in warehouse if s.status == "hot"]
    cold = [s for s in warehouse if s.status == "cold"]

    if panic:
        return dict(
            icon=icon, title=title, theme=theme, urgency=3,
            label="패닉 리밸런싱 즉시 실행",
            detail=panic[0].label,
        )
    parts = []
    if hot:
        parts.append(f"🔥 과열 축소: {', '.join(s.symbol for s in hot)}")
    if cold:
        parts.append(f"❄️ 침체 확대: {', '.join(s.symbol for s in cold)}")
    if parts:
        return dict(
            icon=icon, title=title, theme=theme, urgency=2,
            label="리밸런싱 필요",
            detail=" · ".join(parts),
        )
    return dict(
        icon=icon, title=title, theme=theme, urgency=0,
        label="정상 — 리밸런싱 불필요",
        detail="모든 자산 RSI 정상 범위",
    )


# ── Main Render ──────────────────────────────────────────────

def render_signals(
    tether: TetherSignal,
    crypto: CryptoQuote | None = None,
    bank_rates: list[BankRate] | None = None,
    dxy: DXYData | None = None,
    dollar: DollarSignal | None = None,
    yen: YenSignal | None = None,
    bank_rates_jpy: list[BankRate] | None = None,
):
    section_title("신호등 대시보드", "GO / WAIT 상태를 즉시 확인하세요")

    # Fast cards (from signal data only)
    cards = [
        _card_tether(tether, crypto, bank_rates),
        _card_dollar(dollar),
        _card_yen(yen),
        _card_bank(bank_rates, bank_rates_jpy),
    ]

    # Stock + rebalance cards: show placeholder (heavy data in tabs 3/4)
    cards.append(dict(icon="🚀", title="미국 주식 진입", label="Magic Split 탭에서 확인", detail="", urgency=0, theme="sc-stock"))
    cards.append(dict(icon="🏛️", title="자산배분 리밸런싱", label="Warehouse 탭에서 확인", detail="", urgency=0, theme="sc-rebal"))
    ai_top = None
    screened = None

    # Sort by urgency descending (urgent first)
    cards.sort(key=lambda c: c["urgency"], reverse=True)

    # Render as 2-per-row grid
    grid_html = '<div class="sc-grid">'
    for c in cards:
        grid_html += signal_card_html(**c)
    grid_html += '</div>'
    _html(grid_html)

    # ── Expanded details ─────────────────────────────────────

    # BUY picks detail
    buy_picks = [r for r in (ai_top or []) if r.verdict == "BUY"]
    if buy_picks:
        with st.expander(f"🚀 BUY 종목 상세 ({len(buy_picks)}종목)", expanded=False):
            for r in buy_picks:
                _html(
                    f'<div class="ac">'
                    f'<div class="ac-title"><b>{r.symbol}</b> ({r.name}) '
                    f'<span class="badge buy">{r.score}점 BUY</span></div>'
                    f'<div class="ac-body">{r.synthesis or r.bull_summary[:200]}'
                    f'{"<br><i>📊 규칙 기반</i>" if r.source == "rule" else ""}'
                    f'</div></div>'
                )

    # Screened candidates
    if screened:
        with st.expander(f"📋 스크리닝 후보 {len(screened)}종목", expanded=False):
            headers = ["종목", "가격", "RSI", "고점대비", "점수"]
            rows = []
            for s in screened[:15]:
                rsi_str = f"{s.rsi_14:.0f}" if s.rsi_14 is not None else "—"
                rows.append([
                    f"<b>{s.symbol}</b>",
                    f"${s.price:,.2f}",
                    rsi_str,
                    f"{s.drawdown_pct:+.1f}%",
                    f"{s.rule_score}",
                ])
            data_table(headers, rows)

    # Bank rates detail (USD + JPY)
    if bank_rates:
        with st.expander("🏦 은행별 환율 비교", expanded=False):
            _html('<div class="st" style="font-size:18px;margin:0 0 10px;">💵 달러 (USD)</div>')
            headers = ["기관", "매수(₩)", "매도(₩)", "스프레드", "비고"]
            rows = []
            for r in sorted(bank_rates, key=lambda x: x.buy_rate):
                rows.append([
                    f"<b>{r.name}</b>",
                    f"₩{r.buy_rate:,.0f}",
                    f"₩{r.sell_rate:,.0f}",
                    f"{r.spread_pct:.2f}%",
                    r.recommendation,
                ])
            data_table(headers, rows)

            if bank_rates_jpy:
                _html('<div class="st" style="font-size:18px;margin:16px 0 10px;">💴 엔화 (100 JPY)</div>')
                rows_jpy = []
                for r in sorted(bank_rates_jpy, key=lambda x: x.buy_rate):
                    rows_jpy.append([
                        f"<b>{r.name}</b>",
                        f"₩{r.buy_rate:,.0f}",
                        f"₩{r.sell_rate:,.0f}",
                        f"{r.spread_pct:.2f}%",
                        r.recommendation,
                    ])
                data_table(headers, rows_jpy)
