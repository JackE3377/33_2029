# ============================================================
# GEM Protocol v2 — Section: Macro / Tether / Dollar / Bank Rates
# ============================================================
from __future__ import annotations

import streamlit as st

from services.data_fetcher import MacroData, CryptoQuote, DXYData, BankRate
from services.signal_engine import TetherSignal
from ui.components import (
    section_title, big_metric, metric_grid, data_table,
    alert_critical, alert_warning, alert_info, metric_card,
)


def render_macro(
    macro: MacroData,
    crypto: CryptoQuote,
    tether: TetherSignal,
    dxy: DXYData | None = None,
    bank_rates: list[BankRate] | None = None,
):
    section_title("📡 매크로 & 테더", "글로벌 시장 체크포인트")

    # ── Tether alerts first ───────────────────────────────────
    for msg in tether.alerts:
        if "🔴" in msg:
            alert_critical(msg)
        elif "🟢" in msg:
            alert_info(msg)
        else:
            alert_warning(msg)

    # ── Giant metrics row ─────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        prem_css = "down" if crypto.kimchi_premium_pct < 0 else ("up" if crypto.kimchi_premium_pct >= 3 else "")
        big_metric(
            "USDT 김치프리미엄",
            f"{crypto.kimchi_premium_pct:+.2f}%",
            f"USDT {crypto.price_krw:,.0f}원",
            css=prem_css,
        )
    with c2:
        krw_css = "up" if macro.usd_krw >= 1400 else ""
        big_metric(
            "USD/KRW",
            f"₩{macro.usd_krw:,.1f}",
            css=krw_css,
        )

    # ── Secondary metrics grid ────────────────────────────────
    vix_css = "up" if macro.vix >= 25 else ("down" if macro.vix < 15 else "")
    sp_css = "up" if macro.sp500_daily_chg_pct > 0 else ("down" if macro.sp500_daily_chg_pct < 0 else "")
    nq_css = "up" if macro.nasdaq_daily_chg_pct > 0 else ("down" if macro.nasdaq_daily_chg_pct < 0 else "")

    metrics = [
        {"label": "VIX", "value": f"{macro.vix:.1f}", "css": vix_css},
        {"label": "S&P 500", "value": f"{macro.sp500_daily_chg_pct:+.2f}%", "css": sp_css},
        {"label": "NASDAQ", "value": f"{macro.nasdaq_daily_chg_pct:+.2f}%", "css": nq_css},
    ]
    if macro.fed_funds_rate is not None:
        metrics.append({"label": "기준금리", "value": f"{macro.fed_funds_rate:.2f}%"})
    metric_grid(metrics)

    # ── Tether action ─────────────────────────────────────────
    action_map = {
        "SELL_USDT": ("🔴 테더 매도 타이밍", "김프 고점 — USDT → KRW 전환 고려"),
        "BUY_USDT": ("🟢 테더 매수 기회", "역프 발생 — KRW → USDT 전환 고려"),
        "HOLD": ("⚪ 중립 구간", "김치 프리미엄 정상 범위 — 관망"),
    }
    title, desc = action_map.get(tether.action, ("⚪ 중립", ""))
    st.markdown(f"**{title}** — {desc}")

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════
    # 달러 인덱스 (DXY) 분석
    # ═══════════════════════════════════════════════════════════
    if dxy and dxy.price > 0:
        section_title("💵 달러 인덱스 (DXY)", "차트 기반 반등 가능성 평가")

        c1, c2, c3 = st.columns(3)
        with c1:
            dxy_css = "up" if dxy.change_pct > 0 else ("down" if dxy.change_pct < 0 else "")
            big_metric("DXY", f"{dxy.price:.2f}", f"{dxy.change_pct:+.2f}%", css=dxy_css)
        with c2:
            bounce_css = "up" if dxy.bounce_score >= 60 else ("down" if dxy.bounce_score <= 35 else "")
            big_metric("반등 확률", f"{dxy.bounce_score}/100", dxy.bounce_label, css=bounce_css)
        with c3:
            rsi_str = f"{dxy.rsi_14:.0f}" if dxy.rsi_14 is not None else "—"
            rsi_css = "down" if dxy.rsi_14 and dxy.rsi_14 < 30 else ("up" if dxy.rsi_14 and dxy.rsi_14 > 70 else "")
            big_metric("DXY RSI(14)", rsi_str, css=rsi_css)

        dxy_details = [
            {"label": "SMA 20", "value": f"{dxy.sma_20:.2f}" if dxy.sma_20 else "—"},
            {"label": "SMA 50", "value": f"{dxy.sma_50:.2f}" if dxy.sma_50 else "—"},
            {"label": "52주 고점", "value": f"{dxy.high_52w:.2f}"},
            {"label": "52주 저점", "value": f"{dxy.low_52w:.2f}"},
            {"label": "고점대비", "value": f"{dxy.drawdown_pct:+.1f}%"},
        ]
        metric_grid(dxy_details)

        # Interpretation
        notes = []
        if dxy.rsi_14 and dxy.rsi_14 < 30:
            notes.append("⚡ DXY 과매도 구간 — 단기 반등 가능성 높음")
        elif dxy.rsi_14 and dxy.rsi_14 > 70:
            notes.append("📈 DXY 과매수 구간 — 추가 상승 제한적")
        if dxy.sma_20 and dxy.price < dxy.sma_20:
            notes.append(f"📉 DXY가 20일 이평선({dxy.sma_20:.2f}) 하회 — 약세 흐름")
        if dxy.sma_50 and dxy.price > dxy.sma_50:
            notes.append(f"📊 DXY가 50일 이평선({dxy.sma_50:.2f}) 상회 — 중기 강세")
        for note in notes:
            st.markdown(f"- {note}")

        st.markdown("---")

    # ═══════════════════════════════════════════════════════════
    # 은행별 환율 비교
    # ═══════════════════════════════════════════════════════════
    if bank_rates:
        section_title("🏦 은행별 환율 비교", "모바일/온라인 기준 추정치 (기준환율 ± 스프레드)")

        headers = ["기관", "살 때 (원→달러)", "팔 때 (달러→원)", "스프레드", "추천"]
        rows = []
        for br in sorted(bank_rates, key=lambda r: r.buy_rate):
            rec_html = f'<span style="color:#34c759;font-weight:700;">{br.recommendation}</span>' if br.recommendation else ""
            rows.append([
                f"<b>{br.name}</b>",
                f"₩{br.buy_rate:,.2f}",
                f"₩{br.sell_rate:,.2f}",
                f"{br.spread_pct:.2f}%",
                rec_html,
            ])
        data_table(headers, rows)

        best_buy = min(bank_rates, key=lambda r: r.buy_rate)
        best_sell = max(bank_rates, key=lambda r: r.sell_rate)
        spread_diff = best_sell.sell_rate - best_buy.buy_rate
        st.markdown(
            f"💡 **달러 매수** → **{best_buy.name}** (₩{best_buy.buy_rate:,.2f}) | "
            f"**달러 매도** → **{best_sell.name}** (₩{best_sell.sell_rate:,.2f})"
        )
        st.caption("※ 실제 우대율은 거래금액·고객등급에 따라 다를 수 있습니다.")
