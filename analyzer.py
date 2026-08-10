"""
Score MES / MNQ / MYM for Cooper Precision Reversion Protocol (CPRP) session suitability.

Scoring maps to Official Rulebook v1.5 (Final):
  §2 Instruments & chart setup — micros only; two chart pairs only; static 1H context
  §3 Structure definition      — confirmed S/R range OR channel (≥2 touches each side)
  §4 Entry rules               — confirmation hierarchy: S/R → PA → volume → RSI (v1.5)
  §5 Risk & exits              — range/channel geometry vs −$50 to −$100 hard stop;
                               structure-break → flatten + 30-min pause (or new clear range)
  §6 Pre-trade checklist       — full confluence required
  §7 Operational discipline    — prefer MES; quality over frequency (v1.5)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

from config import (
    CHART_PAIR_DEFAULT,
    CHART_PAIR_SLOW,
    HARD_STOP_DEFAULT_USD,
    HARD_STOP_MAX_USD,
    HARD_STOP_MIN_USD,
    INSTRUMENTS,
    INTRADAY_INTERVAL,
    INTRADAY_PERIOD,
    MIN_SCORE_TO_TRADE,
    PROTOCOL_SHORT,
    RULEBOOK_VERSION,
    STATIC_HTF_INTERVAL,
    STATIC_HTF_PERIOD,
    STRUCTURE_BREAK_PAUSE_MINUTES,
    TIE_BREAK_MARGIN,
    Instrument,
)

ET = ZoneInfo("America/New_York")


@dataclass
class TrendContext:
    """Static 1-Hour long-term trend context (Rulebook §2 / v1.3)."""

    bias: str  # "up" | "down" | "ranging" | "unknown"
    label: str
    last_close: float
    htf_high: float
    htf_low: float
    efficiency: float
    note: str


@dataclass
class InstrumentScore:
    short: str
    name: str
    priority: int
    notes: str
    score: float
    grade: str
    recommend_trade: bool
    last_price: float
    session_high: float
    session_low: float
    range_width_pts: float
    range_width_usd: float
    stop_pts_at_default: float
    range_fit_label: str
    position_in_range: float  # 0 = support, 1 = resistance
    at_extreme: bool
    range_quality: float
    volume_score: float
    volatility_score: float
    structure_score: float
    risk_fit_score: float
    trend_context_score: float
    htf_bias: str
    htf_label: str
    chart_pair: str
    static_htf: str
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    as_of: str = ""


@dataclass
class SessionRecommendation:
    recommended: Optional[str]
    sit_out: bool
    scores: list[InstrumentScore]
    summary: str
    chart_pair_global: str
    static_htf_global: str
    session_phase: str
    as_of: str
    alert_message: str


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _session_phase(now: Optional[datetime] = None) -> str:
    now = now or datetime.now(ET)
    t = now.time()
    # RTH-oriented phases for micro equity index futures
    if time(9, 30) <= t < time(11, 0):
        return "morning_open"
    if time(11, 0) <= t < time(13, 30):
        return "midday"
    if time(13, 30) <= t < time(16, 0):
        return "afternoon"
    if time(18, 0) <= t or t < time(9, 30):
        return "overnight_globex"
    return "after_hours"


def suggest_chart_pair(phase: str, range_width_usd: float, volume_ratio: float) -> str:
    """Rulebook §2 + v1.5 chart-pair hierarchy (two pairs only).

    PRIMARY / DEFAULT:  15m structure + 5m execution
    LARGER / SLOWER:    30m structure + 15m execution
    No chart lower than 5-minute for structure or execution.
    """
    # Larger / slower / lighter volume → secondary pair
    if (
        phase in ("overnight_globex", "after_hours")
        or range_width_usd >= HARD_STOP_MAX_USD * 3.5
        or volume_ratio < 0.85
    ):
        return CHART_PAIR_SLOW
    return CHART_PAIR_DEFAULT


def fetch_bars(symbol: str, period: str = INTRADAY_PERIOD, interval: str = INTRADAY_INTERVAL) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=True)
    if df is None or df.empty:
        raise RuntimeError(f"No data returned for {symbol} ({interval})")
    df = df.rename(columns=str.title)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert(ET)
    else:
        df.index = df.index.tz_convert(ET)
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()


def _efficiency_ratio(close: pd.Series, window: int = 24) -> float:
    """Kaufman-style efficiency: low = choppy/range, high = directional."""
    if len(close) < window + 1:
        window = max(len(close) - 1, 1)
    net = abs(close.iloc[-1] - close.iloc[-window])
    path = close.diff().abs().iloc[-window:].sum()
    if path <= 0:
        return 0.0
    return float(net / path)


def analyze_htf_trend(symbol: str) -> TrendContext:
    """Static 1-Hour trend context — filter only, not entries (Rulebook §2 / v1.3)."""
    try:
        df = fetch_bars(symbol, period=STATIC_HTF_PERIOD, interval=STATIC_HTF_INTERVAL)
    except Exception:
        return TrendContext(
            bias="unknown",
            label="1H context unavailable",
            last_close=0.0,
            htf_high=0.0,
            htf_low=0.0,
            efficiency=0.0,
            note="Could not load 1-Hour bars — confirm trend context on NinjaTrader.",
        )

    look = df.tail(48)  # ~2 trading days of 1H bars
    if len(look) < 6:
        look = df

    last = float(look["Close"].iloc[-1])
    htf_high = float(look["High"].max())
    htf_low = float(look["Low"].min())
    er = _efficiency_ratio(look["Close"], window=min(20, len(look) - 1))

    # Slope of recent closes vs mid-range location
    n = min(12, len(look))
    slope = float(look["Close"].iloc[-1] - look["Close"].iloc[-n]) / max(htf_high - htf_low, 1e-9)
    mid = (htf_high + htf_low) / 2
    pos = (last - htf_low) / max(htf_high - htf_low, 1e-9)

    if er < 0.40:
        bias = "ranging"
        label = "1H ranging / choppy"
        note = (
            "1-Hour is ranging or choppy — standard range/channel reversion setups "
            "on the active pair generally have higher quality (§2)."
        )
    elif slope > 0.12 and pos > 0.45:
        bias = "up"
        label = "1H uptrend"
        note = (
            "1-Hour cleanly trending up — be more selective fading against the trend "
            "(shorting resistance) inside the active range/channel (§2)."
        )
    elif slope < -0.12 and pos < 0.55:
        bias = "down"
        label = "1H downtrend"
        note = (
            "1-Hour cleanly trending down — be more selective fading against the trend "
            "(buying support) inside the active range/channel (§2)."
        )
    else:
        bias = "ranging"
        label = "1H mixed / mild drift"
        note = "1-Hour bias is mixed — use standard CPRP confluence; no strong HTF filter."

    return TrendContext(
        bias=bias,
        label=label,
        last_close=round(last, 2),
        htf_high=round(htf_high, 2),
        htf_low=round(htf_low, 2),
        efficiency=round(er, 3),
        note=note,
    )


def _count_extreme_tests(highs: pd.Series, lows: pd.Series, session_high: float, session_low: float) -> tuple[int, int, int]:
    """Count retests of upper/lower boundaries (Rulebook §3: ≥2 touches each side)."""
    band = max((session_high - session_low) * 0.08, 1e-9)
    high_tests = int((highs >= session_high - band).sum())
    low_tests = int((lows <= session_low + band).sum())
    # Cap contribution; we care that levels were revisited, not every wick
    hi = min(high_tests, 6)
    lo = min(low_tests, 6)
    return hi, lo, hi + lo


def score_instrument(
    inst: Instrument,
    df: pd.DataFrame,
    hard_stop_usd: float = HARD_STOP_DEFAULT_USD,
    htf: Optional[TrendContext] = None,
) -> InstrumentScore:
    reasons: list[str] = []
    warnings: list[str] = []
    now = datetime.now(ET)
    phase = _session_phase(now)
    htf = htf or TrendContext("unknown", "1H n/a", 0.0, 0.0, 0.0, 0.0, "")

    # Prefer today's RTH-ish window if available; else last ~78 bars (~6.5h of 5m)
    today = now.date()
    day_df = df[df.index.date == today]
    if len(day_df) < 12:
        day_df = df.tail(78)
    look = day_df if len(day_df) >= 8 else df.tail(48)

    last = float(look["Close"].iloc[-1])
    session_high = float(look["High"].max())
    session_low = float(look["Low"].min())
    range_pts = max(session_high - session_low, 1e-9)
    range_usd = range_pts * inst.point_value
    stop_pts = hard_stop_usd / inst.point_value

    # --- Structure quality (§3): confirmed range OR channel ---
    # Both horizontal ranges and sloping channels are valid.
    # Low path efficiency still preferred (oscillation inside structure);
    # moderate efficiency is OK if boundaries are being retested (channel).
    er = _efficiency_ratio(look["Close"], window=min(24, len(look) - 1))
    structure_from_er = float(np.clip((0.60 - er) / 0.60 * 100, 0, 100))

    hi_tests, lo_tests, tests = _count_extreme_tests(
        look["High"], look["Low"], session_high, session_low
    )
    # Prefer ≥2 tests on both sides
    both_sides = hi_tests >= 2 and lo_tests >= 2
    structure_from_tests = float(np.clip(tests / 8.0 * 100, 0, 100))
    if both_sides:
        structure_from_tests = min(100.0, structure_from_tests + 15.0)

    # Mid-range occupancy (good structures spend time inside, not one-way)
    inside_band = (
        (look["Close"] > session_low + 0.15 * range_pts)
        & (look["Close"] < session_high - 0.15 * range_pts)
    ).mean()
    structure_from_inside = float(np.clip(inside_band * 120, 0, 100))

    structure_score = 0.40 * structure_from_er + 0.40 * structure_from_tests + 0.20 * structure_from_inside
    range_quality = structure_score

    if both_sides and er < 0.45:
        reasons.append(
            f"Confirmed structure: ≥2 touches each boundary "
            f"(H:{hi_tests}/L:{lo_tests}), efficiency {er:.2f} — range/channel OK (§3)"
        )
    elif both_sides:
        reasons.append(
            f"Boundaries retested both sides (H:{hi_tests}/L:{lo_tests}) — "
            f"channel/range candidate (efficiency {er:.2f})"
        )
    elif er < 0.35:
        reasons.append(f"Ranging structure (efficiency {er:.2f}) — good for reversion")
        warnings.append("Fewer than 2 clear touches on both sides — wait for confirmation (§3)")
    elif er > 0.65:
        warnings.append(
            f"Strongly directional (efficiency {er:.2f}) — structure not confirmed; "
            f"do not force trades (§1, §3)"
        )
    else:
        warnings.append("Structure ambiguous — need ≥2 touches at both boundaries (§3)")

    # --- Position at boundaries (§4: only Support / Resistance zones) ---
    pos = float(np.clip((last - session_low) / range_pts, 0, 1))
    at_extreme = pos <= 0.20 or pos >= 0.80
    extreme_score = 100.0 if at_extreme else float(np.clip(100 - abs(pos - 0.5) * 160, 0, 70))
    side = "support" if pos <= 0.5 else "resistance"
    if at_extreme:
        reasons.append(
            f"Price near range/channel {side} ({pos:.0%} of structure) — valid entry zone (§4)"
        )
    else:
        warnings.append("Price mid-structure — entries only at boundaries (§4)")

    # --- Volume confirmation (§4) ---
    vol = look["Volume"].astype(float)
    vol_ma = vol.rolling(20, min_periods=5).mean()
    recent_vol = float(vol.tail(6).mean())
    base_vol = float(vol_ma.iloc[-1]) if not np.isnan(vol_ma.iloc[-1]) else recent_vol
    volume_ratio = recent_vol / base_vol if base_vol > 0 else 1.0
    volume_score = float(np.clip(50 + (volume_ratio - 1.0) * 80, 0, 100))
    if volume_ratio >= 1.15:
        reasons.append(f"Elevated volume ({volume_ratio:.2f}× avg) — supports rejection/absorption")
    elif volume_ratio < 0.7:
        warnings.append("Volume light — weaker confirmation (§4)")

    # --- Price action rejection proxy (§4) ---
    last_bar = look.iloc[-1]
    upper_wick = float(last_bar["High"] - max(last_bar["Open"], last_bar["Close"]))
    lower_wick = float(min(last_bar["Open"], last_bar["Close"]) - last_bar["Low"])
    bar_range = max(float(last_bar["High"] - last_bar["Low"]), 1e-9)
    rejection = 0.0
    if pos >= 0.75 and upper_wick / bar_range >= 0.4:
        rejection = 90.0
        reasons.append("Upper rejection wick at resistance zone (§4)")
    elif pos <= 0.25 and lower_wick / bar_range >= 0.4:
        rejection = 90.0
        reasons.append("Lower rejection wick at support zone (§4)")
    else:
        rejection = float(np.clip((max(upper_wick, lower_wick) / bar_range) * 70, 0, 70))

    # --- RSI filter (§4 / v1.5): secondary confirmation; prefer divergence at S/R ---
    # Absolute 70/30 is not a mandatory hard gate. Full entry still needs S/R + PA + volume.
    # Hierarchy: confirmed S/R → price action → volume → RSI.
    rsi = _rsi(look["Close"]).iloc[-1]
    rsi_val = float(rsi) if not np.isnan(rsi) else 50.0
    rsi_score = 50.0
    # Mid-range: RSI extreme is preparation / alert only — never force mid-structure entry
    if 0.30 < pos < 0.70:
        if rsi_val >= 70 or rsi_val <= 30:
            rsi_score = 30.0
            warnings.append(
                f"RSI extreme ({rsi_val:.0f}) while mid-range — wait for boundary + PA + volume (v1.5)"
            )
        else:
            rsi_score = 40.0
    # Long at support: prefer oversold / recovery; warn if strongly opposing (not hard fail)
    elif pos <= 0.25:
        if rsi_val >= 70:
            rsi_score = 35.0
            warnings.append(
                f"RSI overbought ({rsi_val:.0f}) at support — low-quality long confluence (v1.5)"
            )
        elif rsi_val <= 35:
            rsi_score = 90.0
            reasons.append(f"RSI favorable at support ({rsi_val:.0f}) — oversold / recovery zone")
        elif rsi_val < 55:
            rsi_score = 70.0
            reasons.append(f"RSI not opposing long at support ({rsi_val:.0f})")
        else:
            rsi_score = 50.0
    # Short at resistance: prefer overbought / fade; warn if strongly opposing
    elif pos >= 0.75:
        if rsi_val <= 30:
            rsi_score = 35.0
            warnings.append(
                f"RSI oversold ({rsi_val:.0f}) at resistance — low-quality short confluence (v1.5)"
            )
        elif rsi_val >= 65:
            rsi_score = 90.0
            reasons.append(f"RSI favorable at resistance ({rsi_val:.0f}) — overbought / fade zone")
        elif rsi_val > 45:
            rsi_score = 70.0
            reasons.append(f"RSI not opposing short at resistance ({rsi_val:.0f})")
        else:
            rsi_score = 50.0

    # --- Risk fit: structure width tradeable inside hard stop (§5) ---
    # Primary target = opposite boundary; stop must fit −$50 to −$100
    ratio = range_usd / hard_stop_usd
    if 1.2 <= ratio <= 4.0:
        risk_fit = 100.0
        range_fit_label = "Structure fits hard-stop risk well"
        reasons.append(f"Structure ${range_usd:.0f} vs stop ${hard_stop_usd:.0f} (ratio {ratio:.1f}×) (§5)")
    elif 0.8 <= ratio < 1.2:
        risk_fit = 70.0
        range_fit_label = "Tight structure — scalps / partial targets only"
        warnings.append("Structure narrow vs stop — targets small (§5)")
    elif 4.0 < ratio <= 6.0:
        risk_fit = 65.0
        range_fit_label = "Wide structure — use tighter sub-levels"
        warnings.append("Wide structure — prefer sub-ranges or larger chart pair")
    else:
        risk_fit = 35.0
        range_fit_label = "Poor risk / structure geometry"
        warnings.append(f"Structure ${range_usd:.0f} poorly matches ${hard_stop_usd:.0f} stop (§5)")

    # Volatility: prefer tradable but not chaos for micros
    tr = pd.concat(
        [
            look["High"] - look["Low"],
            (look["High"] - look["Close"].shift()).abs(),
            (look["Low"] - look["Close"].shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = float(tr.tail(14).mean())
    atr_usd = atr * inst.point_value
    if HARD_STOP_MIN_USD * 0.15 <= atr_usd <= HARD_STOP_MAX_USD * 0.45:
        volatility_score = 90.0
    elif atr_usd < HARD_STOP_MIN_USD * 0.1:
        volatility_score = 45.0
        warnings.append("Very quiet — few clean reversion moves")
    else:
        volatility_score = 55.0
        if atr_usd > HARD_STOP_MAX_USD * 0.5:
            warnings.append("Hot volatility — hard stop can hit quickly (§5)")

    # --- Static 1-Hour trend context filter (§2 / v1.3) ---
    # 1H does not generate entries; it filters quality when fading against trend.
    trend_context_score = 70.0
    if htf.bias == "ranging":
        trend_context_score = 95.0
        reasons.append(htf.note)
    elif htf.bias == "up":
        if at_extreme and pos >= 0.80:
            # Shorting resistance against HTF uptrend — more selective
            trend_context_score = 45.0
            warnings.append(htf.note)
        elif at_extreme and pos <= 0.20:
            # Long with HTF trend at support
            trend_context_score = 85.0
            reasons.append("Long at support aligned with 1H uptrend context — higher quality filter")
        else:
            trend_context_score = 60.0
            reasons.append(htf.note)
    elif htf.bias == "down":
        if at_extreme and pos <= 0.20:
            trend_context_score = 45.0
            warnings.append(htf.note)
        elif at_extreme and pos >= 0.80:
            trend_context_score = 85.0
            reasons.append("Short at resistance aligned with 1H downtrend context — higher quality filter")
        else:
            trend_context_score = 60.0
            reasons.append(htf.note)
    else:
        trend_context_score = 55.0
        if htf.note:
            warnings.append(htf.note)

    # Priority slight bias (§7: prefer MES)
    priority_nudge = {1: 3.0, 2: 1.0, 3: 0.0}[inst.priority]

    # Composite — structure + risk + extremes + confluence + 1H context
    score = (
        0.24 * structure_score
        + 0.16 * risk_fit
        + 0.14 * extreme_score
        + 0.12 * trend_context_score
        + 0.10 * volume_score
        + 0.09 * rejection
        + 0.07 * rsi_score
        + 0.08 * volatility_score
        + priority_nudge
    )
    score = float(np.clip(score, 0, 100))

    if score >= 75:
        grade = "A — Strong session candidate"
    elif score >= 65:
        grade = "B — Tradeable with full confluence"
    elif score >= MIN_SCORE_TO_TRADE:
        grade = "C — Marginal — wait for boundary + confirm"
    else:
        grade = "D — Prefer sit-out / other micro"

    chart_pair = suggest_chart_pair(phase, range_usd, volume_ratio)
    static_htf = f"1-Hour static trend ({htf.label})"

    return InstrumentScore(
        short=inst.short,
        name=inst.name,
        priority=inst.priority,
        notes=inst.notes,
        score=round(score, 1),
        grade=grade,
        recommend_trade=score >= MIN_SCORE_TO_TRADE,
        last_price=round(last, 2),
        session_high=round(session_high, 2),
        session_low=round(session_low, 2),
        range_width_pts=round(range_pts, 2),
        range_width_usd=round(range_usd, 2),
        stop_pts_at_default=round(stop_pts, 2),
        range_fit_label=range_fit_label,
        position_in_range=round(pos, 3),
        at_extreme=at_extreme,
        range_quality=round(range_quality, 1),
        volume_score=round(volume_score, 1),
        volatility_score=round(volatility_score, 1),
        structure_score=round(structure_score, 1),
        risk_fit_score=round(risk_fit, 1),
        trend_context_score=round(trend_context_score, 1),
        htf_bias=htf.bias,
        htf_label=htf.label,
        chart_pair=chart_pair,
        static_htf=static_htf,
        reasons=reasons,
        warnings=warnings,
        as_of=now.strftime("%Y-%m-%d %H:%M:%S %Z"),
    )


def analyze_all(hard_stop_usd: float = HARD_STOP_DEFAULT_USD) -> SessionRecommendation:
    scores: list[InstrumentScore] = []
    errors: list[str] = []

    for key, inst in INSTRUMENTS.items():
        try:
            df = fetch_bars(inst.symbol)
            htf = analyze_htf_trend(inst.symbol)
            scores.append(score_instrument(inst, df, hard_stop_usd=hard_stop_usd, htf=htf))
        except Exception as exc:  # noqa: BLE001 — surface per-symbol failures cleanly
            errors.append(f"{key}: {exc}")

    if not scores:
        as_of = datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S %Z")
        return SessionRecommendation(
            recommended=None,
            sit_out=True,
            scores=[],
            summary="Unable to fetch market data for MES / MNQ / MYM.",
            chart_pair_global=CHART_PAIR_DEFAULT,
            static_htf_global="1-Hour static trend (context)",
            session_phase=_session_phase(),
            as_of=as_of,
            alert_message="DATA ERROR — cannot recommend a micro. Check connection.",
        )

    # Sort by score desc, then priority asc (MES wins ties) — §7
    scores.sort(key=lambda s: (-s.score, s.priority))
    best = scores[0]
    second = scores[1] if len(scores) > 1 else None

    # Tie-break: if within margin, pick higher rulebook priority (MES → MNQ → MYM)
    if second and abs(best.score - second.score) <= TIE_BREAK_MARGIN:
        near = [s for s in scores if best.score - s.score <= TIE_BREAK_MARGIN]
        near.sort(key=lambda s: (s.priority, -s.score))
        best = near[0]

    phase = _session_phase()
    sit_out = not best.recommend_trade

    if sit_out:
        summary = (
            f"No micro clears the {MIN_SCORE_TO_TRADE:.0f}+ session threshold. "
            f"Highest: {best.short} at {best.score:.1f}. Sit out or wait for confirmed structure (§1)."
        )
        alert = f"SIT OUT — best candidate {best.short} ({best.score:.1f}) below trade threshold."
        recommended = None
    else:
        summary = (
            f"Recommended session micro: {best.short} ({best.name}) — score {best.score:.1f}. "
            f"{best.grade}. Active pair: {best.chart_pair}. "
            f"Static HTF: {best.static_htf}."
        )
        alert = (
            f"TRADE {best.short} — score {best.score:.1f} | "
            f"Structure ${best.range_width_usd:.0f} | "
            f"{'AT BOUNDARY' if best.at_extreme else 'WAIT FOR BOUNDARY'} | "
            f"{best.htf_label} | {best.chart_pair}"
        )
        recommended = best.short

    if errors:
        summary += " | Partial data issues: " + "; ".join(errors)

    return SessionRecommendation(
        recommended=recommended,
        sit_out=sit_out,
        scores=scores,
        summary=summary,
        chart_pair_global=best.chart_pair,
        static_htf_global=best.static_htf,
        session_phase=phase,
        as_of=best.as_of,
        alert_message=alert,
    )


if __name__ == "__main__":
    print(f"{PROTOCOL_SHORT} Rulebook v{RULEBOOK_VERSION} — session analysis")
    print(f"Structure-break pause: {STRUCTURE_BREAK_PAUSE_MINUTES} minutes (§5)")
    rec = analyze_all()
    print(rec.alert_message)
    print(rec.summary)
    for s in rec.scores:
        print(
            f"  {s.short}: {s.score:.1f} | {s.grade} | "
            f"structure ${s.range_width_usd:.0f} | {s.htf_label}"
        )
