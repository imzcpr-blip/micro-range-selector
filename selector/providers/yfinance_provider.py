"""Yahoo Finance provider — free delayed futures, ETFs, and VIX.

Price structure prefers the E-mini continuous (ES=F / NQ=F / YM=F) when the
micro ticker is thin, because Yahoo's MES=F/MNQ=F/MYM=F history often gaps.
Index points are 1:1. Volume on the E-mini is a liquidity *proxy*, not micro volume.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

from selector.config import (
    DAILY_PERIOD,
    ET_TZ,
    HTF_INTERVAL,
    HTF_PERIOD,
    INSTRUMENTS,
    INTRADAY_INTERVAL,
    INTRADAY_PERIOD,
    ORDERED_BOOKS,
    STRUCTURE_INTERVAL,
    STRUCTURE_PERIOD,
    VIX_SYMBOL,
)
from selector.models import (
    DataGap,
    HtfContext,
    InstrumentMetrics,
    InternalsSnapshot,
    MarketBundle,
    OvernightStats,
)
from selector.providers.base import SessionClock, overnight_window, rth_window, slice_index
from selector.volume_profile import volume_at_price

ET = ZoneInfo(ET_TZ)


def fetch_live_bundle(clock: SessionClock) -> MarketBundle:
    symbols = _symbol_list()
    frames = _download_many(symbols)

    gaps: list[DataGap] = []
    price_notes: list[str] = []
    sources: list[dict] = [
        {
            "name": "Yahoo Finance (yfinance)",
            "used_for": "OHLC, volume, VIX, SPY/QQQ/DIA",
            "status": "live",
            "limitation": "Delayed, not CME. Micros often thin — E-mini continuous used for structure.",
        }
    ]

    vix_last, vix_chg, vix_regime = _vix(frames.get(VIX_SYMBOL), gaps)
    internals = _internals(frames, vix_last, vix_chg, vix_regime, gaps)
    _try_tick(frames, internals, gaps)

    metrics: dict[str, InstrumentMetrics] = {}
    for short in ORDERED_BOOKS:
        metrics[short] = _instrument_metrics(
            short, frames, clock, gaps, price_notes, internals
        )

    sources.append(
        {
            "name": "Volume-at-price proxy",
            "used_for": "POC / VA / HVN-LVN clarity",
            "status": "proxy",
            "limitation": "Built from Yahoo 5m/15m volume, not session profile or delta. Paste NT/CME nodes to upgrade.",
        }
    )
    return MarketBundle(
        as_of=clock.now.strftime("%Y-%m-%d %H:%M ET"),
        session_date=clock.target_rth.isoformat(),
        session_phase=clock.phase,
        overnight_ready=clock.overnight_ready,
        using_mock=False,
        mock_scenario=None,
        price_notes=price_notes,
        gaps=gaps,
        metrics=metrics,
        internals=internals,
        calendar=[],
        calendar_source="pending",
        mega_cap_earnings=[],
        sources_used=sources,
    )


def _symbol_list() -> list[str]:
    out = [VIX_SYMBOL, "SPY", "QQQ", "DIA"]
    for inst in INSTRUMENTS.values():
        out.extend([inst.yahoo_micro, inst.yahoo_emini, inst.etf])
    # ^TICK / ^ADD / ^VOLD are typically delisted on Yahoo — skip the round-trip.
    # unique, stable order
    seen = set()
    uniq = []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


def _download_many(symbols: list[str]) -> dict[str, dict[str, pd.DataFrame]]:
    """symbol -> {intraday, structure, htf, daily}"""
    specs = [
        ("intraday", INTRADAY_PERIOD, INTRADAY_INTERVAL),
        ("structure", STRUCTURE_PERIOD, STRUCTURE_INTERVAL),
        ("htf", HTF_PERIOD, HTF_INTERVAL),
        ("daily", DAILY_PERIOD, "1d"),
    ]
    with ThreadPoolExecutor(max_workers=10) as pool:
        fut_map = {}
        for sym in symbols:
            for key, period, interval in specs:
                if sym in {VIX_SYMBOL, "SPY", "QQQ", "DIA"} and key in {"structure", "htf"}:
                    continue
                fut = pool.submit(_history, sym, period, interval)
                fut_map[fut] = (sym, key)
        frames: dict[str, dict[str, pd.DataFrame]] = {s: {} for s in symbols}
        for fut in as_completed(fut_map):
            sym, key = fut_map[fut]
            try:
                df = fut.result()
            except Exception:
                df = pd.DataFrame()
            frames[sym][key] = df
    return frames


def _history(symbol: str, period: str, interval: str) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=True)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df.columns = [str(c).title() for c in df.columns]
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert(ET)
    else:
        df.index = df.index.tz_convert(ET)
    cols = [c for c in ("Open", "High", "Low", "Close", "Volume") if c in df.columns]
    return df[cols].dropna(how="all")


def _pick_price_frame(
    frames: dict, micro: str, emini: str, kind: str
) -> tuple[pd.DataFrame, str]:
    micro_df = (frames.get(micro) or {}).get(kind, pd.DataFrame())
    emini_df = (frames.get(emini) or {}).get(kind, pd.DataFrame())
    if micro_df is not None and len(micro_df) >= 20:
        return micro_df, micro
    if emini_df is not None and len(emini_df) >= 8:
        return emini_df, emini
    if micro_df is not None and not micro_df.empty:
        return micro_df, micro
    if emini_df is not None and not emini_df.empty:
        return emini_df, emini
    return pd.DataFrame(), "none"


def _instrument_metrics(
    short: str,
    frames: dict,
    clock: SessionClock,
    gaps: list[DataGap],
    price_notes: list[str],
    internals: InternalsSnapshot,
) -> InstrumentMetrics:
    inst = INSTRUMENTS[short]
    intra, src_i = _pick_price_frame(frames, inst.yahoo_micro, inst.yahoo_emini, "intraday")
    struct, src_s = _pick_price_frame(frames, inst.yahoo_micro, inst.yahoo_emini, "structure")
    htf_df, src_h = _pick_price_frame(frames, inst.yahoo_micro, inst.yahoo_emini, "htf")
    daily, src_d = _pick_price_frame(frames, inst.yahoo_micro, inst.yahoo_emini, "daily")

    src = src_i or src_s or src_d or "none"
    if src == inst.yahoo_emini:
        price_notes.append(
            f"{short}: structure from {inst.yahoo_emini} (same index points). "
            f"{inst.yahoo_micro} was thin or empty on Yahoo."
        )
    if src == "none":
        gaps.append(
            DataGap(
                key=f"price_{short}",
                detail=f"No Yahoo bars for {inst.yahoo_micro} or {inst.yahoo_emini}.",
                score_effect="Instrument falls back toward liquidity base; cleanliness capped.",
            )
        )

    last = _last_close(intra, struct, daily)
    htf = _htf_context(htf_df if htf_df is not None and not htf_df.empty else daily, last)
    on = _overnight_stats(intra, struct, clock, inst.point_value, last)
    if on.source in {"prior_session", "daily_proxy"}:
        gaps.append(
            DataGap(
                key=f"overnight_{short}",
                detail=on.note,
                score_effect="Overnight cleanliness uses a proxy; refresh when Globex is live.",
            )
        )

    look = intra if intra is not None and len(intra) >= 12 else struct
    if look is None or look.empty:
        look = daily
    profile = volume_at_price(look.tail(80) if look is not None else pd.DataFrame(), inst.tick_size)
    if profile.source == "unavailable":
        gaps.append(
            DataGap(
                key=f"vp_{short}",
                detail=profile.notes,
                score_effect="Cleanliness × 0.88 and confidence −8 until a real profile is pasted.",
            )
        )
    else:
        gaps.append(
            DataGap(
                key=f"vp_{short}",
                detail="Volume profile is a Yahoo VAP proxy, not CME session profile / delta.",
                score_effect="Cleanliness × 0.88 and confidence −8 unless you paste POC/HVN from the platform.",
            )
        )

    atr_pts = _atr(daily, 14)
    rth_pts = _recent_rth_median(intra, clock, fallback_daily=daily)
    expected_pts = _expected_range(atr_pts, rth_pts, on.range_pts)
    vol, vol_ratio, oi = _volume_oi(daily, frames, inst)
    tests_hi, tests_lo, er, rsi = _structure_stats(look, on)

    etf_df = (frames.get(inst.etf) or {}).get("intraday", pd.DataFrame())
    etf_pct = _etf_premarket_pct(etf_df)

    warnings: list[str] = []
    if on.efficiency > 0.65:
        warnings.append("Overnight path is one-way — poor mean-reversion until value rebuilds.")
    if profile.balance_label == "unbalanced":
        warnings.append("Profile proxy looks unbalanced / trending.")
    if atr_pts * inst.point_value > 8 * 75:
        warnings.append("ATR in dollars is very wide versus a $75 stop — noise risk.")

    pos_htf = 0.5
    if htf.high > htf.low:
        pos_htf = float(np.clip((last - htf.low) / (htf.high - htf.low), 0, 1))

    return InstrumentMetrics(
        short=short,
        name=inst.name,
        last_price=round(float(last), 2),
        price_source=src,
        overnight=on,
        htf=htf,
        profile=profile,
        atr14_pts=round(float(atr_pts), 2),
        atr14_usd=round(float(atr_pts) * inst.point_value, 2),
        recent_rth_range_pts=round(float(rth_pts), 2),
        recent_rth_range_usd=round(float(rth_pts) * inst.point_value, 2),
        expected_rth_pts=round(float(expected_pts), 2),
        expected_rth_usd=round(float(expected_pts) * inst.point_value, 2),
        prior_day_volume=float(vol),
        volume_vs_20d=round(float(vol_ratio), 2),
        open_interest=oi,
        etf_overnight_pct=etf_pct,
        dual_side_high_tests=tests_hi,
        dual_side_low_tests=tests_lo,
        path_efficiency=round(float(er), 3),
        rsi14=round(float(rsi), 1),
        position_in_htf_range=round(float(pos_htf), 3),
        typical_rth_pts=inst.typical_rth_pts,
        tick_value=inst.tick_value,
        point_value=inst.point_value,
        tick_size=inst.tick_size,
        warnings=warnings,
    )


def _last_close(*frames: pd.DataFrame) -> float:
    for df in frames:
        if df is not None and not df.empty and "Close" in df.columns:
            val = float(df["Close"].dropna().iloc[-1])
            if np.isfinite(val):
                return val
    return 0.0


def _htf_context(df: pd.DataFrame, last: float) -> HtfContext:
    if df is None or df.empty:
        return HtfContext("unknown", "1H unavailable", last, last, last, 0.0, "No 1H bars.")
    look = df.tail(48)
    hi = float(look["High"].max())
    lo = float(look["Low"].min())
    close = float(look["Close"].iloc[-1])
    er = _efficiency(look["Close"], min(20, len(look) - 1))
    n = min(12, len(look))
    slope = float(look["Close"].iloc[-1] - look["Close"].iloc[-n]) / max(hi - lo, 1e-9)
    pos = (close - lo) / max(hi - lo, 1e-9)
    if er < 0.40:
        bias, label, note = "ranging", "1H ranging / choppy", "Higher-TF is rotating — standard CPRP fades."
    elif slope > 0.12 and pos > 0.45:
        bias, label, note = "up", "1H uptrend", "Be selective shorting resistance against 1H power."
    elif slope < -0.12 and pos < 0.55:
        bias, label, note = "down", "1H downtrend", "Be selective buying support against 1H power."
    else:
        bias, label, note = "ranging", "1H mixed / mild drift", "No strong HTF filter."
    return HtfContext(bias, label, round(close, 2), round(hi, 2), round(lo, 2), round(er, 3), note)


def _overnight_stats(
    intra: pd.DataFrame,
    struct: pd.DataFrame,
    clock: SessionClock,
    point_value: float,
    last: float,
) -> OvernightStats:
    rth = clock.target_rth if clock.overnight_ready else clock.last_completed_rth
    start, end = overnight_window(rth)
    source = "live" if clock.overnight_ready else "prior_session"
    df = intra if intra is not None and not intra.empty else struct
    sl = slice_index(df, start, end) if df is not None else None
    if sl is None or sl.empty:
        # Fallback: last 14 hours of 5m/15m
        if df is not None and not df.empty:
            sl = df.tail(80)
            source = "prior_session"
        else:
            return OvernightStats(
                high=last, low=last, last=last, range_pts=0, range_usd=0,
                position=0.5, efficiency=0.5, bar_count=0, source="daily_proxy",
                note="No overnight bars — using last as a stub.",
            )
    hi = float(sl["High"].max())
    lo = float(sl["Low"].min())
    cls = float(sl["Close"].iloc[-1])
    rng = max(hi - lo, 0.0)
    pos = (cls - lo) / rng if rng else 0.5
    er = _efficiency(sl["Close"], min(24, max(len(sl) - 1, 1)))
    note = f"{len(sl)} bars {start.strftime('%a %H:%M')}–{end.strftime('%H:%M')} ET ({source})."
    if source == "prior_session":
        note = "Using last completed overnight / recent Globex because the next window is not live. " + note
    return OvernightStats(
        high=round(hi, 2),
        low=round(lo, 2),
        last=round(cls, 2),
        range_pts=round(rng, 2),
        range_usd=round(rng * point_value, 2),
        position=round(float(np.clip(pos, 0, 1)), 3),
        efficiency=round(float(er), 3),
        bar_count=int(len(sl)),
        source=source,
        note=note,
    )


def _recent_rth_median(intra: pd.DataFrame, clock: SessionClock, fallback_daily: pd.DataFrame) -> float:
    if intra is None or intra.empty:
        if fallback_daily is not None and not fallback_daily.empty:
            rng = (fallback_daily["High"] - fallback_daily["Low"]).tail(10)
            return float(rng.median())
        return 0.0
    ranges = []
    dates = sorted(set(intra.index.date))[-8:]
    for d in dates:
        sl = slice_index(intra, *rth_window(d))
        if sl is not None and len(sl) >= 6:
            ranges.append(float(sl["High"].max() - sl["Low"].min()))
    if ranges:
        return float(np.median(ranges))
    return float((intra["High"] - intra["Low"]).tail(40).sum())  # weak fallback


def _expected_range(atr_pts: float, rth_pts: float, on_pts: float) -> float:
    parts = [p for p in (atr_pts, rth_pts) if p and p > 0]
    if not parts:
        return on_pts * 1.15 if on_pts else 0.0
    base = 0.6 * atr_pts + 0.4 * (rth_pts or atr_pts)
    # Overnight already consumed some of the day's range.
    if on_pts and atr_pts:
        remain = max(atr_pts - 0.35 * on_pts, 0.45 * atr_pts)
        return 0.5 * base + 0.5 * remain
    return base


def _atr(daily: pd.DataFrame, n: int = 14) -> float:
    if daily is None or len(daily) < n + 1:
        if daily is not None and not daily.empty:
            return float((daily["High"] - daily["Low"]).tail(5).mean())
        return 0.0
    h, l, c = daily["High"], daily["Low"], daily["Close"]
    prev = c.shift(1)
    tr = pd.concat([(h - l), (h - prev).abs(), (l - prev).abs()], axis=1).max(axis=1)
    val = float(tr.rolling(n).mean().iloc[-1])
    return val if np.isfinite(val) else float(tr.iloc[-1])


def _volume_oi(daily: pd.DataFrame, frames: dict, inst) -> tuple[float, float, Optional[float]]:
    vol = 0.0
    ratio = 1.0
    if daily is not None and not daily.empty and "Volume" in daily.columns:
        v = daily["Volume"].astype(float)
        vol = float(v.iloc[-1])
        mean = float(v.tail(20).mean())
        ratio = vol / mean if mean > 0 else 1.0
    # Yahoo rarely populates micro open interest; leave None for a paid CME/Databento hook.
    oi = None
    return vol, ratio, oi


def _structure_stats(look: pd.DataFrame, on: OvernightStats) -> tuple[int, int, float, float]:
    if look is None or look.empty:
        return 0, 0, on.efficiency, 50.0
    window = look.tail(48)
    hi, lo = on.high, on.low
    if hi <= lo:
        hi = float(window["High"].max())
        lo = float(window["Low"].min())
    band = max((hi - lo) * 0.08, 1e-9)
    tests_hi = int((window["High"] >= hi - band).sum())
    tests_lo = int((window["Low"] <= lo + band).sum())
    er = _efficiency(window["Close"], min(24, len(window) - 1))
    rsi = _rsi(window["Close"])
    return min(tests_hi, 8), min(tests_lo, 8), er, rsi


def _efficiency(close: pd.Series, window: int) -> float:
    if close is None or len(close) < 3:
        return 0.5
    window = max(min(window, len(close) - 1), 1)
    net = abs(float(close.iloc[-1] - close.iloc[-window]))
    path = float(close.diff().abs().iloc[-window:].sum())
    if path <= 0:
        return 0.0
    return net / path


def _rsi(close: pd.Series, period: int = 14) -> float:
    if close is None or len(close) < period + 2:
        return 50.0
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    val = float((100 - (100 / (1 + rs))).iloc[-1])
    return val if np.isfinite(val) else 50.0


def _vix(daily_map: Optional[dict], gaps: list[DataGap]) -> tuple[Optional[float], Optional[float], str]:
    df = (daily_map or {}).get("daily", pd.DataFrame())
    if df is None or df.empty:
        df = (daily_map or {}).get("intraday", pd.DataFrame())
    if df is None or df.empty:
        gaps.append(
            DataGap("vix", "VIX (^VIX) unavailable from Yahoo.", "CPRP alignment uses a neutral VIX; confidence −3.")
        )
        return None, None, "unknown"
    last = float(df["Close"].iloc[-1])
    prev = float(df["Close"].iloc[-2]) if len(df) >= 2 else last
    chg = last - prev
    if last < 13:
        regime = "grind"
    elif last <= 22:
        regime = "fadeable"
    elif last <= 28:
        regime = "elevated"
    else:
        regime = "event"
    return round(last, 2), round(chg, 2), regime


def _etf_premarket_pct(df: pd.DataFrame) -> Optional[float]:
    if df is None or df.empty:
        return None
    day = df.index[-1].date()
    sl = df[df.index.date == day]
    if sl.empty:
        sl = df.tail(20)
    try:
        return round(100.0 * (float(sl["Close"].iloc[-1]) / float(sl["Open"].iloc[0]) - 1.0), 3)
    except Exception:
        return None


def _internals(
    frames: dict,
    vix_last: Optional[float],
    vix_chg: Optional[float],
    vix_regime: str,
    gaps: list[DataGap],
) -> InternalsSnapshot:
    pcts = {}
    notes = []
    for etf in ("SPY", "QQQ", "DIA"):
        daily = (frames.get(etf) or {}).get("daily", pd.DataFrame())
        intra = (frames.get(etf) or {}).get("intraday", pd.DataFrame())
        pct = None
        if intra is not None and len(intra) >= 4:
            pct = _etf_premarket_pct(intra)
        if pct is None and daily is not None and len(daily) >= 2:
            pct = round(100.0 * (float(daily["Close"].iloc[-1]) / float(daily["Close"].iloc[-2]) - 1.0), 3)
        pcts[etf] = pct
        if pct is None:
            gaps.append(DataGap(f"etf_{etf}", f"{etf} return unavailable.", "Leadership for that index is neutralized."))
    valid = {k: v for k, v in pcts.items() if v is not None}
    if valid:
        leader = max(valid, key=valid.get)
        laggard = min(valid, key=valid.get)
        spread = None
        if pcts.get("QQQ") is not None and pcts.get("SPY") is not None:
            spread = round(pcts["QQQ"] - pcts["SPY"], 3)
            notes.append(f"QQQ vs SPY {spread:+.2f} pts (percentage points).")
        if abs(valid[leader] - valid[laggard]) < 0.12:
            leader, laggard = "mixed", "mixed"
            notes.append("ETFs are moving together — no clear leadership.")
        else:
            notes.append(f"Leader {leader} ({valid[leader]:+.2f}%) · laggard {laggard} ({valid[laggard]:+.2f}%).")
    else:
        leader = laggard = "unknown"
        spread = None
        notes.append("No ETF relative-strength print.")
    return InternalsSnapshot(
        spy_pct=pcts.get("SPY"),
        qqq_pct=pcts.get("QQQ"),
        dia_pct=pcts.get("DIA"),
        leader=leader,
        laggard=laggard,
        spread_qqq_spy=spread,
        vix_last=vix_last,
        vix_change=vix_chg,
        vix_regime=vix_regime,
        notes=notes,
    )


def _try_tick(frames: dict, internals: InternalsSnapshot, gaps: list[DataGap]) -> None:
    gaps.append(
        DataGap(
            "internals_tick",
            "NYSE TICK / ADD / VOLD are not on Yahoo (symbols delisted). Using SPY/QQQ/DIA relative performance.",
            score_effect="Leadership uses ETF proxies only. Plug a paid internals feed into providers/ later.",
        )
    )
    internals.notes.append("TICK/ADD/VOLD unavailable — ETF relative performance is the internals proxy.")
