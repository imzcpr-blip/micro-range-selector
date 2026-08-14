"""
Score MES / MNQ / MYM for Cooper Precision Reversion Protocol (CPRP) session suitability.

Scoring maps to Official Rulebook v1.6:
  §2 Instruments & chart setup — micros only; multi-TF hierarchy; two pairs; static 60m bias
  §3 Structure definition      — confirmed S/R range OR channel (≥2 touches each side)
  §4 Order flow                — Bid/Ask power on platform (not scored from Yahoo OHLC)
  §5 Entry rules               — S/R → PA → volume → order flow → RSI (v1.6)
  §6 Risk & exits              — geometry vs −$50 to −$100 hard stop; 30-min structure-break pause
  §7 Pre-trade checklist       — 9 items; full confluence required
  §8 Operational discipline    — prefer MES; quality over frequency; not scalping
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
    STRUCTURE_BARS,
    STRUCTURE_INTERVAL,
    STRUCTURE_PERIOD,
    MIN_SCORE_TO_TRADE,
    PROTOCOL_SHORT,
    RULEBOOK_VERSION,
    SCALPING_MIN_SCORE,
    SCALPING_STYLE,
    SCALPING_VERSION,
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
    path_efficiency: float = 0.5  # low = sideways / choppy; high = directional
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    as_of: str = ""


# Scalping uses **1-minute** charts only (not 1H). Sideways path efficiency → Conclusive.
SCALPING_SIDEWAYS_MAX_ER = 0.42  # efficiency at/below this = sideways movement
SCALPING_DIRECTIONAL_MIN_ER = 0.55  # clearly one-way → inconclusive


@dataclass
class ScalpingMicroScore:
    """Per-micro CPRP Scalping environment score for comparison cards."""

    short: str
    name: str
    priority: int
    score: float
    status: str  # "Option Conclusive" | "Option Inconclusive"
    available: bool
    movement: str  # "Sideways" | "Mixed" | "Directional"
    path_efficiency: float
    volume_score: float
    volatility_score: float
    structure_score: float
    chart: str = "1-minute only"
    notes: list[str] = field(default_factory=list)


@dataclass
class ScalpingOption:
    """Secondary CPRP Scalping offer when environment clears (1m chart · sideways tape)."""

    eligible: bool
    micro: Optional[str]
    score: float
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    label: str = SCALPING_STYLE
    # Always filled for Session Selector comparison cards
    micro_scores: list[ScalpingMicroScore] = field(default_factory=list)
    status_label: str = "Option Inconclusive"  # overall: Conclusive vs Inconclusive


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
    # Strategy options for the desk (primary CPRP and/or secondary scalping)
    primary_active: bool = False
    scalping: Optional[ScalpingOption] = None
    strategy_options: list[str] = field(default_factory=list)


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
    """Rulebook v1.7 chart hierarchy: higher-TF structure + adaptive 1m/5m execution.

    PRIMARY / DEFAULT:  15m structure + adaptive 1m/5m execution (RSI-respect)
    LARGER / SLOWER:    30m structure + adaptive 1m/5m execution
    Execution TF: choose 1m or 5m based on which respects RSI OB/OS bounces.
    """
    # Larger / slower / lighter volume → secondary structure pair
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

    # --- RSI filter (§5 / v1.6): secondary confirmation; prefer divergence at S/R ---
    # Elevated RSI that *stays* high often = strong buying power — do not auto-fade
    # solely because the reading is overbought. Absolute 70/30 is not a hard gate.
    # Full entry still needs S/R + PA + volume + order flow (platform) + RSI.
    rsi = _rsi(look["Close"]).iloc[-1]
    rsi_val = float(rsi) if not np.isnan(rsi) else 50.0
    rsi_score = 50.0
    # Mid-range: RSI extreme is preparation / alert only — never force mid-structure entry
    if 0.30 < pos < 0.70:
        if rsi_val >= 70 or rsi_val <= 30:
            rsi_score = 30.0
            warnings.append(
                f"RSI extreme ({rsi_val:.0f}) while mid-range — wait for boundary + PA + volume + order flow (v1.6)"
            )
        else:
            rsi_score = 40.0
    # Long at support: prefer oversold / recovery; warn if strongly opposing (not hard fail)
    elif pos <= 0.25:
        if rsi_val >= 70:
            rsi_score = 40.0  # v1.6: elevated RSI can still be strength — softer penalty
            warnings.append(
                f"RSI elevated ({rsi_val:.0f}) at support — confirm bid defense / OF; not auto-fade (v1.6)"
            )
        elif rsi_val <= 35:
            rsi_score = 90.0
            reasons.append(f"RSI favorable at support ({rsi_val:.0f}) — oversold / recovery zone")
        elif rsi_val < 55:
            rsi_score = 70.0
            reasons.append(f"RSI not opposing long at support ({rsi_val:.0f})")
        else:
            rsi_score = 50.0
    # Short at resistance: do NOT treat high RSI alone as a short green light (v1.6 strength)
    elif pos >= 0.75:
        if rsi_val <= 30:
            rsi_score = 35.0
            warnings.append(
                f"RSI oversold ({rsi_val:.0f}) at resistance — low-quality short confluence (v1.6)"
            )
        elif rsi_val >= 70:
            # Elevated + still at highs often = buying power still in control
            rsi_score = 45.0
            warnings.append(
                f"RSI elevated ({rsi_val:.0f}) at resistance — may still be strength; "
                "need OF shift + structure crack before fade (v1.6)"
            )
            reasons.append(
                f"RSI high at resistance ({rsi_val:.0f}) — treat as alert, not standalone short signal"
            )
        elif rsi_val >= 55:
            rsi_score = 65.0
            reasons.append(
                f"RSI elevated at resistance ({rsi_val:.0f}) — prefer divergence + ask aggression"
            )
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
        path_efficiency=round(float(er), 3),
        reasons=reasons,
        warnings=warnings,
        as_of=now.strftime("%Y-%m-%d %H:%M:%S %Z"),
    )


@dataclass
class StructureDirectionScenario:
    """One potential path on the structure chart (15m default)."""

    direction: str  # "LONG" | "SHORT" | "RANGE" | "BREAK_UP" | "BREAK_DOWN" | "STAND_ASIDE"
    label: str
    confidence: str  # "High" | "Medium" | "Low"
    probability_hint: float  # 0-100 relative weight among listed scenarios
    triggers: list[str] = field(default_factory=list)
    invalidation: str = ""


@dataclass
class StructureDirectionAnalysis:
    """Technical read of the same structure bars shown on Session Selector (15m)."""

    short: str
    primary: str  # dominant lean: LONG | SHORT | TWO-WAY | STAND_ASIDE
    primary_label: str
    confidence: str
    last: float
    session_high: float
    session_low: float
    position_in_range: float
    path_efficiency: float
    rsi: float
    ema_fast: float
    ema_slow: float
    timeframe: str = "15m"
    break_resistance_state: str = "held"  # held | testing | broken
    break_support_state: str = "held"  # held | testing | broken
    scenarios: list[StructureDirectionScenario] = field(default_factory=list)
    tech_notes: list[str] = field(default_factory=list)
    chart_levels: dict[str, float] = field(default_factory=dict)


def fetch_structure_bars(
    symbol: str,
    *,
    period: str = STRUCTURE_PERIOD,
    interval: str = STRUCTURE_INTERVAL,
    bars: int = STRUCTURE_BARS,
) -> pd.DataFrame:
    """Fetch structure-map bars (default 15m) for Session Selector chart + break TA."""
    df = fetch_bars(symbol, period=period, interval=interval)
    if bars and len(df) > bars:
        return df.tail(bars)
    return df


def analyze_structure_directions(
    bars: pd.DataFrame,
    *,
    short: str = "",
    htf_bias: str = "unknown",
    htf_label: str = "",
    timeframe: str = STRUCTURE_INTERVAL,
) -> StructureDirectionAnalysis:
    """
    Potential directions from technical analysis of the **structure chart** (default **15m**).

    Uses the same OHLC window the Session Selector plots (window high/low = proxy S/R,
    wicks, RSI, EMAs, path efficiency, swing structure, break state). CPRP framing:
      • Prefer boundary reactions (support long / resistance short)
      • Mid-structure → two-way or stand-aside, not forced direction
      • Break resistance / break support assessed on structure TF closes
      • Static 1H bias soft-filters which side is higher quality
    Educational desk context — not an order signal.
    """
    tf = (timeframe or STRUCTURE_INTERVAL or "15m").strip()
    if bars is None or bars.empty or len(bars) < 8:
        return StructureDirectionAnalysis(
            short=short or "—",
            primary="STAND_ASIDE",
            primary_label=f"Insufficient {tf} bars for structure TA",
            confidence="Low",
            last=0.0,
            session_high=0.0,
            session_low=0.0,
            position_in_range=0.5,
            path_efficiency=0.0,
            rsi=50.0,
            ema_fast=0.0,
            ema_slow=0.0,
            timeframe=tf,
            tech_notes=[f"Need more {tf} history before reading direction."],
        )

    look = bars.copy()
    last = float(look["Close"].iloc[-1])
    # Structure S/R: prefer today's structure window if enough bars, else full display window
    now = datetime.now(ET)
    day_df = look[look.index.date == now.date()]
    struct = day_df if len(day_df) >= 8 else look
    session_high = float(struct["High"].max())
    session_low = float(struct["Low"].min())
    # If today's range is degenerate, fall back to full lookback window
    if session_high - session_low < 1e-6:
        session_high = float(look["High"].max())
        session_low = float(look["Low"].min())
        struct = look

    range_pts = max(session_high - session_low, 1e-9)
    pos = float(np.clip((last - session_low) / range_pts, 0, 1))
    er = _efficiency_ratio(look["Close"], window=min(24, len(look) - 1))

    rsi_series = _rsi(look["Close"], period=14)
    rsi_val = float(rsi_series.iloc[-1]) if not np.isnan(rsi_series.iloc[-1]) else 50.0

    ema_fast = float(look["Close"].ewm(span=9, adjust=False).mean().iloc[-1])
    ema_slow = float(look["Close"].ewm(span=21, adjust=False).mean().iloc[-1])

    # Recent swing structure (last ~20 bars on structure TF)
    tail = look.tail(min(24, len(look)))
    swing_high = float(tail["High"].max())
    swing_low = float(tail["Low"].min())
    mid = (session_high + session_low) / 2.0

    # Last bar rejection
    lb = look.iloc[-1]
    bar_range = max(float(lb["High"] - lb["Low"]), 1e-9)
    upper_wick = float(lb["High"] - max(lb["Open"], lb["Close"]))
    lower_wick = float(min(lb["Open"], lb["Close"]) - lb["Low"])
    body = abs(float(lb["Close"] - lb["Open"]))
    bullish_bar = float(lb["Close"]) >= float(lb["Open"])
    close_last = float(lb["Close"])

    # Volume context for break confirmation
    vol = look["Volume"].astype(float)
    vol_ma = float(vol.tail(20).mean()) if len(vol) >= 5 else float(vol.mean() or 1.0)
    vol_last = float(vol.iloc[-1]) if len(vol) else 0.0
    vol_ratio = (vol_last / vol_ma) if vol_ma > 0 else 1.0

    # ── Break resistance / break support state (structure TF closes) ─────
    # Prior structure: high/low of window excluding last 1–2 bars (so we can detect a fresh break)
    prior = look.iloc[:-1] if len(look) > 12 else look
    prior_high = float(prior["High"].max())
    prior_low = float(prior["Low"].min())
    # Use full structure high/low as the map; detect break vs those levels
    res_level = session_high
    sup_level = session_low
    # If last close is still the extreme printer, use prior interior for break status
    if abs(close_last - res_level) < 1e-9 and len(prior) >= 4:
        res_level = float(prior["High"].max())
    if abs(close_last - sup_level) < 1e-9 and len(prior) >= 4:
        sup_level = float(prior["Low"].min())

    # Recompute map levels as window extremes (display lines); break uses close vs those
    res_level = session_high
    sup_level = session_low

    # Testing band = within 8% of structure range from boundary
    test_band = max(range_pts * 0.08, 1e-9)
    # Decisive break: close beyond level by at least a small buffer (tick-ish 0.1% of price or 15% of band)
    break_buf = max(range_pts * 0.02, abs(last) * 0.00015, 0.25)

    if close_last > res_level + break_buf:
        break_res_state = "broken"
    elif last >= res_level - test_band or float(lb["High"]) >= res_level - test_band * 0.5:
        break_res_state = "testing"
    else:
        break_res_state = "held"

    if close_last < sup_level - break_buf:
        break_sup_state = "broken"
    elif last <= sup_level + test_band or float(lb["Low"]) <= sup_level + test_band * 0.5:
        break_sup_state = "testing"
    else:
        break_sup_state = "held"

    # Momentum: close vs EMAs + short slope
    above_fast = last >= ema_fast
    above_slow = last >= ema_slow
    ema_bull = ema_fast >= ema_slow
    slope = float(look["Close"].iloc[-1] - look["Close"].iloc[-min(6, len(look))])

    notes: list[str] = []
    notes.append(
        f"**{tf}** structure high/low (proxy S/R): **{session_high:,.2f}** / **{session_low:,.2f}** · "
        f"last **{last:,.2f}** ({pos:.0%} of structure)"
    )
    notes.append(
        f"Path efficiency **{er:.2f}** "
        f"({'sideways / rotational' if er <= 0.42 else 'moderately directional' if er < 0.60 else 'strongly directional'})"
    )
    notes.append(
        f"RSI(14) **{rsi_val:.1f}** · EMA9 **{ema_fast:,.2f}** · EMA21 **{ema_slow:,.2f}** "
        f"({'bullish stack' if ema_bull and above_fast else 'bearish stack' if (not ema_bull) and (not above_fast) else 'mixed EMAs'})"
    )
    notes.append(
        f"**Break resistance:** `{break_res_state}` at **{session_high:,.2f}** · "
        f"**Break support:** `{break_sup_state}` at **{session_low:,.2f}** "
        f"(decisive = {tf} close beyond level + buffer)"
    )
    if htf_label:
        notes.append(f"Static 1H context: {htf_label} (`{htf_bias}`)")

    scenarios: list[StructureDirectionScenario] = []
    long_weight = 0.0
    short_weight = 0.0
    range_weight = 0.0

    # --- Boundary LONG (support reaction) ---
    if pos <= 0.28 and break_sup_state != "broken":
        w = 38.0
        trig = [
            f"Price in lower **{tf}** structure zone ({pos:.0%}) — CPRP long zone at support proxy",
            f"Defend **{session_low:,.2f}** with rejection / higher low on {tf}",
        ]
        if lower_wick / bar_range >= 0.35:
            w += 12
            trig.append(f"Lower wick rejection on latest {tf} bar")
        if rsi_val <= 40:
            w += 8
            trig.append(f"RSI {rsi_val:.0f} supports mean-reversion bounce from support")
        if break_sup_state == "testing":
            w += 6
            trig.append(f"Support **testing** on {tf} — need hold + bounce, not close through")
        if htf_bias == "down":
            w -= 10
            trig.append("1H bias is down — longs need sharper rejection + order flow (selective)")
        elif htf_bias == "up":
            w += 8
            trig.append("1H bias up — support longs better aligned with HTF")
        if er > 0.62 and slope < 0:
            w -= 8
            trig.append("Strong downside efficiency — wait for structure hold, do not catch a knife")
        scenarios.append(
            StructureDirectionScenario(
                direction="LONG",
                label="Long from support (reversion)",
                confidence="High" if w >= 48 else "Medium" if w >= 32 else "Low",
                probability_hint=max(w, 5.0),
                triggers=trig,
                invalidation=(
                    f"Decisive **{tf} close below {session_low:,.2f}** "
                    f"(structure **break support** → pause reversion)"
                ),
            )
        )
        long_weight += max(w, 0)

    # --- Boundary SHORT (resistance reaction) ---
    if pos >= 0.72 and break_res_state != "broken":
        w = 38.0
        trig = [
            f"Price in upper **{tf}** structure zone ({pos:.0%}) — CPRP short zone at resistance proxy",
            f"Reject **{session_high:,.2f}** with lower high / upper wick on {tf}",
        ]
        if upper_wick / bar_range >= 0.35:
            w += 12
            trig.append(f"Upper wick rejection on latest {tf} bar")
        if rsi_val >= 60:
            w += 8
            trig.append(f"RSI {rsi_val:.0f} supports fade from resistance (prefer divergence live)")
        if break_res_state == "testing":
            w += 6
            trig.append(f"Resistance **testing** on {tf} — need reject, not close through")
        if htf_bias == "up":
            w -= 10
            trig.append("1H bias is up — shorts need clear rejection + OF shift (selective)")
        elif htf_bias == "down":
            w += 8
            trig.append("1H bias down — resistance shorts better aligned with HTF")
        if er > 0.62 and slope > 0:
            w -= 8
            trig.append("Strong upside efficiency — do not auto-fade strength without structure fail")
        scenarios.append(
            StructureDirectionScenario(
                direction="SHORT",
                label="Short from resistance (reversion)",
                confidence="High" if w >= 48 else "Medium" if w >= 32 else "Low",
                probability_hint=max(w, 5.0),
                triggers=trig,
                invalidation=(
                    f"Decisive **{tf} close above {session_high:,.2f}** "
                    f"(structure **break resistance** → pause reversion)"
                ),
            )
        )
        short_weight += max(w, 0)

    # --- Mid-structure / range two-way ---
    if 0.28 < pos < 0.72 and break_res_state != "broken" and break_sup_state != "broken":
        w = 42.0 if er <= 0.45 else 28.0
        trig = [
            f"Price mid-structure ({pos:.0%}) on {tf} — CPRP: no edge for forced one-way entries",
            f"Two-way between **{session_low:,.2f}** and **{session_high:,.2f}** until a boundary is tested",
        ]
        if er <= 0.42:
            w += 10
            trig.append("Low path efficiency — rotational tape favors fade extremes, not mid-range chase")
        scenarios.append(
            StructureDirectionScenario(
                direction="RANGE",
                label="Two-way / wait for boundary",
                confidence="High" if er <= 0.45 else "Medium",
                probability_hint=w,
                triggers=trig,
                invalidation=f"Acceptable only while price remains inside {tf} high/low band",
            )
        )
        range_weight += w
        if er >= 0.55 and above_fast and above_slow and ema_bull:
            scenarios.append(
                StructureDirectionScenario(
                    direction="LONG",
                    label="Bullish continuation (only after pullback to structure)",
                    confidence="Low",
                    probability_hint=18.0,
                    triggers=[
                        f"{tf} EMAs stacked bullish while mid-range",
                        "CPRP still prefers wait for pullback to support / rising channel base — not chasing",
                    ],
                    invalidation=f"Loss of EMA9 **{ema_fast:,.2f}** or break of recent swing low **{swing_low:,.2f}**",
                )
            )
            long_weight += 12
        elif er >= 0.55 and (not above_fast) and (not above_slow) and (not ema_bull):
            scenarios.append(
                StructureDirectionScenario(
                    direction="SHORT",
                    label="Bearish continuation (only after pullback to structure)",
                    confidence="Low",
                    probability_hint=18.0,
                    triggers=[
                        f"{tf} EMAs stacked bearish while mid-range",
                        "CPRP still prefers wait for pullback to resistance / falling channel top — not chasing",
                    ],
                    invalidation=f"Reclaim of EMA9 **{ema_fast:,.2f}** or break of recent swing high **{swing_high:,.2f}**",
                )
            )
            short_weight += 12

    # --- Break resistance (BREAK_UP) — updated structure-TF logic ---
    break_up_w = 10.0
    break_up_trig = [
        f"**Break resistance** level: **{session_high:,.2f}** on {tf}",
        f"State now: **{break_res_state}**",
    ]
    if break_res_state == "broken":
        break_up_w += 28.0
        break_up_trig.append(
            f"Decisive **{tf} close above resistance** (last close {close_last:,.2f} > {session_high:,.2f})"
        )
        if vol_ratio >= 1.15:
            break_up_w += 10.0
            break_up_trig.append(f"Volume elevated on break bar ({vol_ratio:.2f}× avg) — stronger break")
        elif vol_ratio < 0.75:
            break_up_w -= 6.0
            break_up_trig.append("Light volume on break — treat as suspect until follow-through")
        if bullish_bar and body / bar_range >= 0.45:
            break_up_w += 6.0
            break_up_trig.append(f"Strong bullish {tf} body through resistance")
        if htf_bias == "up":
            break_up_w += 8.0
            break_up_trig.append("1H bias up — break-resistance continuation more plausible")
        elif htf_bias == "down":
            break_up_w -= 6.0
            break_up_trig.append("1H bias down — upside break may fail (bull trap risk)")
        break_up_trig.append(
            "CPRP: **pause reversion fades** — re-map new structure after break (structure-break pause)"
        )
    elif break_res_state == "testing":
        break_up_w += 14.0
        break_up_trig.append(f"Price **testing** resistance on {tf} — watch for reject vs close-through")
        break_up_trig.append(
            f"Confirm break only on **{tf} close above {session_high:,.2f}** with follow-through"
        )
        if upper_wick / bar_range >= 0.4:
            break_up_w -= 8.0
            break_up_trig.append("Upper wick at resistance — favors **reject** over break for now")
    else:
        break_up_w += 6.0 + (5.0 if er > 0.55 and slope > 0 else 0.0)
        break_up_trig.append(
            f"Resistance **held** so far — break path only if {tf} closes above **{session_high:,.2f}**"
        )

    scenarios.append(
        StructureDirectionScenario(
            direction="BREAK_UP",
            label=f"Break resistance ({break_res_state})",
            confidence=(
                "High" if break_res_state == "broken" and break_up_w >= 40
                else "Medium" if break_up_w >= 22
                else "Low"
            ),
            probability_hint=max(break_up_w, 5.0),
            triggers=break_up_trig,
            invalidation=(
                f"Failed break / bull trap: {tf} closes back **below {session_high:,.2f}** "
                f"and loses breakout structure"
            ),
        )
    )

    # --- Break support (BREAK_DOWN) ---
    break_dn_w = 10.0
    break_dn_trig = [
        f"**Break support** level: **{session_low:,.2f}** on {tf}",
        f"State now: **{break_sup_state}**",
    ]
    if break_sup_state == "broken":
        break_dn_w += 28.0
        break_dn_trig.append(
            f"Decisive **{tf} close below support** (last close {close_last:,.2f} < {session_low:,.2f})"
        )
        if vol_ratio >= 1.15:
            break_dn_w += 10.0
            break_dn_trig.append(f"Volume elevated on break bar ({vol_ratio:.2f}× avg) — stronger break")
        elif vol_ratio < 0.75:
            break_dn_w -= 6.0
            break_dn_trig.append("Light volume on break — treat as suspect until follow-through")
        if (not bullish_bar) and body / bar_range >= 0.45:
            break_dn_w += 6.0
            break_dn_trig.append(f"Strong bearish {tf} body through support")
        if htf_bias == "down":
            break_dn_w += 8.0
            break_dn_trig.append("1H bias down — break-support continuation more plausible")
        elif htf_bias == "up":
            break_dn_w -= 6.0
            break_dn_trig.append("1H bias up — downside break may fail (bear trap risk)")
        break_dn_trig.append(
            "CPRP: **pause reversion fades** — re-map new structure after break (structure-break pause)"
        )
    elif break_sup_state == "testing":
        break_dn_w += 14.0
        break_dn_trig.append(f"Price **testing** support on {tf} — watch for bounce vs close-through")
        break_dn_trig.append(
            f"Confirm break only on **{tf} close below {session_low:,.2f}** with follow-through"
        )
        if lower_wick / bar_range >= 0.4:
            break_dn_w -= 8.0
            break_dn_trig.append("Lower wick at support — favors **hold/bounce** over break for now")
    else:
        break_dn_w += 6.0 + (5.0 if er > 0.55 and slope < 0 else 0.0)
        break_dn_trig.append(
            f"Support **held** so far — break path only if {tf} closes below **{session_low:,.2f}**"
        )

    scenarios.append(
        StructureDirectionScenario(
            direction="BREAK_DOWN",
            label=f"Break support ({break_sup_state})",
            confidence=(
                "High" if break_sup_state == "broken" and break_dn_w >= 40
                else "Medium" if break_dn_w >= 22
                else "Low"
            ),
            probability_hint=max(break_dn_w, 5.0),
            triggers=break_dn_trig,
            invalidation=(
                f"Failed break / bear trap: {tf} closes back **above {session_low:,.2f}** "
                f"and reclaims support structure"
            ),
        )
    )

    # If structure already broken, elevate primary lean toward break path
    if break_res_state == "broken":
        short_weight *= 0.35  # reversion shorts invalidated
        range_weight *= 0.4
    if break_sup_state == "broken":
        long_weight *= 0.35
        range_weight *= 0.4

    # Micro PA note
    if bullish_bar and body / bar_range >= 0.55:
        notes.append(f"Latest {tf} bar is a strong bullish body")
    elif (not bullish_bar) and body / bar_range >= 0.55:
        notes.append(f"Latest {tf} bar is a strong bearish body")

    # Primary lean — prefer confirmed structure breaks, then boundary reversion, then range
    if break_res_state == "broken" and break_up_w >= 35:
        primary = "LONG"
        primary_label = (
            f"Primary lean: **BREAK RESISTANCE** on {tf} "
            f"(close through **{session_high:,.2f}**) — pause reversion shorts; re-map structure"
        )
        conf = "High" if break_up_w >= 45 else "Medium"
    elif break_sup_state == "broken" and break_dn_w >= 35:
        primary = "SHORT"
        primary_label = (
            f"Primary lean: **BREAK SUPPORT** on {tf} "
            f"(close through **{session_low:,.2f}**) — pause reversion longs; re-map structure"
        )
        conf = "High" if break_dn_w >= 45 else "Medium"
    elif pos <= 0.28 and long_weight >= short_weight and long_weight >= 28:
        primary = "LONG"
        primary_label = f"Primary lean: **LONG** reaction from {tf} support zone"
        conf = "High" if long_weight >= 48 else "Medium"
    elif pos >= 0.72 and short_weight >= long_weight and short_weight >= 28:
        primary = "SHORT"
        primary_label = f"Primary lean: **SHORT** reaction from {tf} resistance zone"
        conf = "High" if short_weight >= 48 else "Medium"
    elif range_weight >= max(long_weight, short_weight) and 0.28 < pos < 0.72:
        primary = "TWO-WAY"
        primary_label = f"Primary lean: **TWO-WAY** — wait for {tf} boundary (mid-structure)"
        conf = "High" if er <= 0.45 else "Medium"
    elif long_weight > short_weight * 1.25 and long_weight >= 22:
        primary = "LONG"
        primary_label = f"Primary lean: **LONG-biased** {tf} structure (confirm at support)"
        conf = "Medium" if long_weight >= 30 else "Low"
    elif short_weight > long_weight * 1.25 and short_weight >= 22:
        primary = "SHORT"
        primary_label = f"Primary lean: **SHORT-biased** {tf} structure (confirm at resistance)"
        conf = "Medium" if short_weight >= 30 else "Low"
    else:
        primary = "STAND_ASIDE"
        primary_label = f"Primary lean: **STAND ASIDE** — {tf} structure TA not conclusive"
        conf = "Low"
        scenarios.insert(
            0,
            StructureDirectionScenario(
                direction="STAND_ASIDE",
                label=f"Stand aside until cleaner {tf} map",
                confidence="Medium",
                probability_hint=30.0,
                triggers=[
                    "No clear boundary edge or conflicting momentum vs location",
                    f"Wait for retest of {tf} high/low with rejection + volume + order flow",
                ],
                invalidation="New confirmed structure with ≥2 touches each side",
            ),
        )

    # Normalize probability hints to ~100
    ssum = sum(max(s.probability_hint, 0) for s in scenarios) or 1.0
    for s in scenarios:
        s.probability_hint = round(100.0 * max(s.probability_hint, 0) / ssum, 1)
    scenarios.sort(key=lambda s: -s.probability_hint)

    return StructureDirectionAnalysis(
        short=short or "—",
        primary=primary,
        primary_label=primary_label,
        confidence=conf,
        last=round(last, 2),
        session_high=round(session_high, 2),
        session_low=round(session_low, 2),
        position_in_range=round(pos, 3),
        path_efficiency=round(float(er), 3),
        rsi=round(rsi_val, 1),
        ema_fast=round(ema_fast, 2),
        ema_slow=round(ema_slow, 2),
        timeframe=tf,
        break_resistance_state=break_res_state,
        break_support_state=break_sup_state,
        scenarios=scenarios[:6],
        tech_notes=notes,
        chart_levels={
            "last": round(last, 2),
            "session_high": round(session_high, 2),
            "session_low": round(session_low, 2),
            "resistance": round(session_high, 2),
            "support": round(session_low, 2),
            "ema9": round(ema_fast, 2),
            "ema21": round(ema_slow, 2),
            "mid": round(mid, 2),
            "swing_high": round(swing_high, 2),
            "swing_low": round(swing_low, 2),
            "break_buffer": round(break_buf, 4),
        },
    )


def analyze_5m_structure_directions(
    bars: pd.DataFrame,
    *,
    short: str = "",
    htf_bias: str = "unknown",
    htf_label: str = "",
) -> StructureDirectionAnalysis:
    """Backward-compatible alias — structure map is **15m** (use analyze_structure_directions)."""
    return analyze_structure_directions(
        bars,
        short=short,
        htf_bias=htf_bias,
        htf_label=htf_label,
        timeframe=STRUCTURE_INTERVAL,
    )


def score_scalping_environment(
    scores: list[InstrumentScore],
    *,
    phase: str,
    primary_active: bool,
    primary_best: InstrumentScore,
) -> ScalpingOption:
    """
    CPRP Scalping v1.1 — secondary tool only.

    Chart for scalping: **1-minute only** (Keltner + SMA 14 + RSI). No 1H chart for scalping entries.
    Movement rule: **sideways** path efficiency → **Option Conclusive**; directional → **Option Inconclusive**.

    Always scores every micro for Session Selector comparison cards.
    """
    reasons: list[str] = []
    warnings: list[str] = []

    hard_block = (
        primary_active
        and primary_best.structure_score >= 72
        and primary_best.score >= 70
    )
    if hard_block:
        warnings.append(
            f"High-quality primary CPRP on {primary_best.short} "
            f"(score {primary_best.score:.1f}, structure {primary_best.structure_score:.0f}) — "
            "prefer reversion; scalping stands aside until structure goes quiet."
        )

    primary_quiet = not primary_active or primary_best.structure_score < 58
    if not primary_active:
        quiet_score = 90.0
        reasons.append(
            f"Primary CPRP is quiet (best {primary_best.short} {primary_best.score:.1f}) — "
            "if **sideways 1m movement**, scalping can be **Option Conclusive**."
        )
    elif primary_quiet:
        quiet_score = 78.0
        reasons.append(
            f"Primary structure soft ({primary_best.short}) — "
            "sideways 1m tape can make scalping **Option Conclusive** by preference."
        )
    else:
        quiet_score = 62.0
        reasons.append(
            f"Primary CPRP also tradeable on {primary_best.short} — "
            "if movement is **sideways**, both protocols may be offered; pick by preference."
        )

    reasons.append(
        "CPRP Scalping chart: **1-minute only** (Keltner · SMA 14 · RSI 80/20). "
        "No 1-Hour chart for scalping entries."
    )

    micro_scores: list[ScalpingMicroScore] = []
    best_short: Optional[str] = None
    best_env = -1.0
    env_notes: list[str] = []

    for s in scores:
        notes: list[str] = [
            "Chart for this protocol: **1-minute only** (not 1H / 60m for entries)",
        ]
        er = float(getattr(s, "path_efficiency", 0.5) or 0.5)

        # Sideways movement = core conclusive signal for scalping
        if er <= SCALPING_SIDEWAYS_MAX_ER:
            movement = "Sideways"
            move_pts = 95.0
            notes.append(
                f"Movement **sideways** (efficiency {er:.2f}) → favors **Option Conclusive**"
            )
        elif er >= SCALPING_DIRECTIONAL_MIN_ER:
            movement = "Directional"
            move_pts = 20.0
            notes.append(
                f"Movement **directional** (efficiency {er:.2f}) → **Option Inconclusive** for scalping"
            )
        else:
            movement = "Mixed"
            move_pts = 50.0
            notes.append(f"Movement mixed (efficiency {er:.2f}) — need clearer sideways tape")

        vol = s.volume_score
        if 40 <= vol <= 72:
            vol_pts = 85.0
        elif 30 <= vol < 40 or 72 < vol <= 85:
            vol_pts = 60.0
        elif vol < 30:
            vol_pts = 35.0
            notes.append("Volume light / dead — weak scalp tape")
        else:
            vol_pts = 40.0
            notes.append("Volume elevated — less ideal for quiet scalp")

        vlt = s.volatility_score
        if 45 <= vlt <= 75:
            vlt_pts = 85.0
        elif 35 <= vlt < 45 or 75 < vlt <= 85:
            vlt_pts = 60.0
        else:
            vlt_pts = 40.0

        if s.structure_score < 50:
            struct_pts = 80.0
            notes.append("Primary map weak — room for 1m Keltner")
        elif s.structure_score < 62:
            struct_pts = 65.0
        else:
            struct_pts = 35.0
            notes.append("Strong primary map — reversion often preferred")

        phase_pts = {
            "midday": 90.0,
            "afternoon": 75.0,
            "morning_open": 50.0,
            "overnight_globex": 70.0,
            "after_hours": 55.0,
        }.get(phase, 55.0)

        # Weight sideways movement heaviest — user rule: sideways → conclusive
        env = (
            0.38 * move_pts
            + 0.20 * quiet_score
            + 0.14 * vol_pts
            + 0.12 * vlt_pts
            + 0.10 * struct_pts
            + 0.06 * phase_pts
            + {1: 3.0, 2: 1.0, 3: 0.0}.get(s.priority, 0.0)
        )
        env = float(np.clip(env, 0, 100))

        # User / rulebook: **sideways movement → Option Conclusive** on 1m protocol
        # Directional movement → Option Inconclusive (scalping not appropriate)
        sideways = movement == "Sideways"
        if sideways:
            env = max(env, SCALPING_MIN_SCORE + 8.0)
            micro_available = True
            if hard_block:
                notes.append(
                    "Primary CPRP structure is also strong — both may show; "
                    "prefer reversion unless you choose quiet 1m scalps by preference"
                )
        else:
            micro_available = False

        status = "Option Conclusive" if micro_available else "Option Inconclusive"
        micro_scores.append(
            ScalpingMicroScore(
                short=s.short,
                name=s.name,
                priority=s.priority,
                score=round(env, 1),
                status=status,
                available=micro_available,
                movement=movement,
                path_efficiency=round(er, 3),
                volume_score=s.volume_score,
                volatility_score=s.volatility_score,
                structure_score=s.structure_score,
                chart="1-minute only",
                notes=notes,
            )
        )

        if env > best_env:
            best_env = env
            best_short = s.short
            env_notes = list(notes)

    if not micro_scores:
        return ScalpingOption(
            eligible=False,
            micro=None,
            score=0.0,
            warnings=["No micro data for scalping environment."],
            micro_scores=[],
            status_label="Option Inconclusive",
        )

    micro_scores.sort(key=lambda m: (-m.score, m.priority))
    reasons.extend(env_notes)

    # Prefer best conclusive (sideways) micro; else best env score
    conclusive_cards = [m for m in micro_scores if m.available]
    if conclusive_cards:
        conclusive_cards.sort(key=lambda m: (-m.score, m.priority))
        best_short = conclusive_cards[0].short
        best_env = conclusive_cards[0].score

    any_conclusive = bool(conclusive_cards)
    eligible = any_conclusive
    status_label = "Option Conclusive" if eligible else "Option Inconclusive"

    if eligible and best_short:
        best_card = next((m for m in micro_scores if m.short == best_short), micro_scores[0])
        reasons.append(
            f"CPRP Scalping v{SCALPING_VERSION}: **Option Conclusive** · focus **{best_short}** · "
            f"movement **{best_card.movement}** · chart **1-minute only** · "
            "Keltner · SMA(14) · RSI 80/20 · risk $30–$50."
        )
        reasons.append(
            "Confirm on the **1-minute** chart only (not 1H): "
            "price accepted one side of SMA · repeated Keltner touches · RSI stretch."
        )
        if primary_active:
            reasons.append(
                "**Both strategies available** — CPRP Reversion and CPRP Scalping. "
                "One rulebook per trade; preference is yours."
            )
        if hard_block:
            warnings.append(
                "Primary CPRP structure is also high quality — "
                "reversion remains preferred, but sideways 1m still marks scalping **Option Conclusive**."
            )
    else:
        warnings.append(
            f"CPRP Scalping: **Option Inconclusive** — need **sideways** chart movement "
            f"(path efficiency ≤ {SCALPING_SIDEWAYS_MAX_ER:.2f}) on the **1-minute** protocol. "
            f"Best env {best_env:.1f}."
        )

    return ScalpingOption(
        eligible=eligible,
        micro=best_short if eligible else None,
        score=round(best_env, 1),
        reasons=reasons,
        warnings=warnings,
        label=SCALPING_STYLE,
        micro_scores=micro_scores,
        status_label=status_label,
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
            primary_active=False,
            scalping=ScalpingOption(
                False, None, 0.0, status_label="Option Inconclusive", micro_scores=[]
            ),
            strategy_options=["SIT OUT — data error"],
        )

    # Sort by score desc, then priority asc (MES wins ties) — §8
    scores.sort(key=lambda s: (-s.score, s.priority))
    best = scores[0]
    second = scores[1] if len(scores) > 1 else None

    # Tie-break: if within margin, pick higher rulebook priority (MES → MNQ → MYM)
    if second and abs(best.score - second.score) <= TIE_BREAK_MARGIN:
        near = [s for s in scores if best.score - s.score <= TIE_BREAK_MARGIN]
        near.sort(key=lambda s: (s.priority, -s.score))
        best = near[0]

    phase = _session_phase()
    primary_active = bool(best.recommend_trade)
    sit_out = not primary_active

    scalping = score_scalping_environment(
        scores,
        phase=phase,
        primary_active=primary_active,
        primary_best=best,
    )

    strategy_options: list[str] = []

    if primary_active:
        strategy_options.append(
            f"PRIMARY · CPRP Reversion · {best.short} (score {best.score:.1f})"
        )
        summary = (
            f"Primary: **{best.short}** range/channel reversion — score {best.score:.1f}. "
            f"{best.grade}. Pair: {best.chart_pair}. HTF: {best.static_htf}."
        )
        alert = (
            f"TRADE {best.short} — CPRP Reversion · score {best.score:.1f} | "
            f"Structure ${best.range_width_usd:.0f} | "
            f"{'AT BOUNDARY' if best.at_extreme else 'WAIT FOR BOUNDARY'} | "
            f"{best.htf_label} | {best.chart_pair}"
        )
        recommended = best.short
        sit_out = False
    else:
        summary = (
            f"Primary CPRP quiet — no micro clears {MIN_SCORE_TO_TRADE:.0f}+ "
            f"(best {best.short} at {best.score:.1f})."
        )
        recommended = None
        sit_out = True
        alert = (
            f"PRIMARY QUIET — best {best.short} ({best.score:.1f}) below reversion threshold."
        )

    if scalping.eligible and scalping.micro:
        strategy_options.append(
            f"OPTION · CPRP Scalping v{SCALPING_VERSION} · {scalping.micro} "
            f"(env {scalping.score:.1f}) · 1m Keltner · $30–$50 risk"
        )
        summary += (
            f" **Scalping option available:** {scalping.micro} "
            f"(environment {scalping.score:.1f}/100) — secondary 1m Keltner mean-reversion "
            "when primary is quiet / sideways."
        )
        if sit_out:
            alert = (
                f"OPTION: CPRP SCALPING · {scalping.micro} (env {scalping.score:.1f}) | "
                f"Primary quiet | 1m Keltner | risk $30–$50 | confirm SMA side + bands"
            )
            # Not a full sit-out when scalping is offered — desk has an option
            sit_out = False
            # Keep recommended None for primary; scalping is separate option
        else:
            alert += f" | ALSO: Scalping option {scalping.micro} (env {scalping.score:.1f})"
    else:
        if sit_out:
            strategy_options.append("SIT OUT — wait for confirmed CPRP structure or quieter scalp tape")
            summary += " No scalping environment either — capital preservation."
            alert = (
                f"SIT OUT — best reversion {best.short} ({best.score:.1f}); "
                f"scalping env {scalping.score:.1f} (need {SCALPING_MIN_SCORE:.0f}+)."
            )

    if not strategy_options:
        strategy_options.append("SIT OUT")

    if errors:
        summary += " | Partial data issues: " + "; ".join(errors)

    return SessionRecommendation(
        recommended=recommended,
        sit_out=sit_out and not (scalping.eligible),
        scores=scores,
        summary=summary,
        chart_pair_global=best.chart_pair,
        static_htf_global=best.static_htf,
        session_phase=phase,
        as_of=best.as_of,
        alert_message=alert,
        primary_active=primary_active,
        scalping=scalping,
        strategy_options=strategy_options,
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
