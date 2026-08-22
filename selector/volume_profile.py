"""Session volume-profile PROXY from OHLC volume-at-price.

This is NOT CME footprint / NinjaTrader Session VP / order-flow delta.
Each bar's volume is spread evenly across the ticks it traded. Good enough to
judge whether value is peaked (clean HVN) or flat (messy), and to estimate POC /
value area. True HVN-edge limit entries still need the platform profile.

When the trader pastes a real POC / VAH / VAL, scoring prefers those numbers.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from selector.config import VP_HVN_FRAC, VP_LVN_FRAC, VP_VALUE_AREA
from selector.models import VolumeProfileProxy


def _empty(reason: str) -> VolumeProfileProxy:
    return VolumeProfileProxy(
        poc=0.0,
        vah=0.0,
        val=0.0,
        hvn_levels=[],
        lvn_levels=[],
        peakedness=0.0,
        clarity=40.0,
        balance_label="unknown",
        is_proxy=True,
        source="unavailable",
        notes=reason,
        bin_count=0,
        value_area_width_pts=0.0,
    )


def volume_at_price(
    df: pd.DataFrame,
    tick_size: float,
    value_area: float = VP_VALUE_AREA,
) -> VolumeProfileProxy:
    """Build a tick-binned volume-at-price histogram from OHLC bars."""
    if df is None or df.empty or tick_size <= 0:
        return _empty("No bars to build a volume-at-price proxy.")

    need = {"High", "Low", "Close", "Volume"}
    if not need.issubset(set(df.columns)):
        return _empty("Bars missing High/Low/Close/Volume.")

    highs = df["High"].astype(float).to_numpy()
    lows = df["Low"].astype(float).to_numpy()
    closes = df["Close"].astype(float).to_numpy()
    vols = df["Volume"].astype(float).to_numpy()
    vols = np.where(np.isfinite(vols) & (vols > 0), vols, 0.0)
    if float(vols.sum()) <= 0:
        return _empty("Volume column is empty — cannot proxy a profile.")

    lo = float(np.nanmin(lows))
    hi = float(np.nanmax(highs))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return _empty("Range is degenerate — cannot bin volume.")

    # Cap bin count so a wide MNQ/MYM range stays tractable.
    raw_bins = int(round((hi - lo) / tick_size)) + 1
    n_bins = int(np.clip(raw_bins, 12, 180))
    edges = np.linspace(lo, hi, n_bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    hist = np.zeros(n_bins, dtype=float)

    for h, l, v in zip(highs, lows, vols):
        if not np.isfinite(h) or not np.isfinite(l) or v <= 0:
            continue
        if h < l:
            h, l = l, h
        # Distribute this bar's volume across overlapping bins.
        i0 = int(np.searchsorted(edges, l, side="right") - 1)
        i1 = int(np.searchsorted(edges, h, side="left") - 1)
        i0 = int(np.clip(i0, 0, n_bins - 1))
        i1 = int(np.clip(i1, 0, n_bins - 1))
        if i1 < i0:
            i0, i1 = i1, i0
        span = i1 - i0 + 1
        hist[i0 : i1 + 1] += v / span

    total = float(hist.sum())
    if total <= 0:
        return _empty("Histogram collapsed to zero.")

    poc_i = int(hist.argmax())
    poc = float(centers[poc_i])
    peak = float(hist[poc_i])

    # Value area: expand from POC until `value_area` of volume is captured.
    lo_i = hi_i = poc_i
    captured = peak
    target = total * value_area
    while captured < target and (lo_i > 0 or hi_i < n_bins - 1):
        left = hist[lo_i - 1] if lo_i > 0 else -1.0
        right = hist[hi_i + 1] if hi_i < n_bins - 1 else -1.0
        if right > left:
            hi_i += 1
            captured += hist[hi_i]
        elif left >= 0:
            lo_i -= 1
            captured += hist[lo_i]
        else:
            break
    val = float(centers[lo_i])
    vah = float(centers[hi_i])

    hvn: list[float] = []
    lvn: list[float] = []
    for i in range(1, n_bins - 1):
        if hist[i] >= peak * VP_HVN_FRAC and hist[i] >= hist[i - 1] and hist[i] >= hist[i + 1]:
            hvn.append(float(centers[i]))
        if hist[i] <= peak * VP_LVN_FRAC and hist[i] <= hist[i - 1] and hist[i] <= hist[i + 1]:
            lvn.append(float(centers[i]))
    if poc not in hvn:
        hvn.insert(0, poc)
    hvn = _unique_round(hvn, tick_size)[:6]
    lvn = _unique_round(lvn, tick_size)[:6]

    # Peakedness: share of volume in the POC bin vs a flat distribution.
    peakedness = float(np.clip((peak / total) * n_bins * 12.0, 0, 100))
    va_width = max(vah - val, tick_size)
    range_w = max(hi - lo, tick_size)
    tightness = float(np.clip(100.0 * (1.0 - va_width / range_w), 0, 100))
    clarity = float(np.clip(0.55 * peakedness + 0.45 * tightness, 0, 100))

    last = float(closes[-1])
    inside_va = val <= last <= vah
    # Unbalanced if last is outside VA and one wing holds almost no volume.
    lower_share = float(hist[:poc_i].sum() / total) if poc_i > 0 else 0.0
    upper_share = float(hist[poc_i + 1 :].sum() / total) if poc_i < n_bins - 1 else 0.0
    if inside_va and 0.28 <= lower_share <= 0.72:
        balance = "balanced"
    elif not inside_va or lower_share < 0.18 or upper_share < 0.18:
        balance = "unbalanced"
    else:
        balance = "balanced" if inside_va else "unbalanced"

    notes = (
        f"Yahoo VAP proxy · {n_bins} bins · POC {poc:.2f} · VA {val:.2f}–{vah:.2f} · "
        f"{balance}. Not CME session profile / delta."
    )
    return VolumeProfileProxy(
        poc=round(poc, 2),
        vah=round(vah, 2),
        val=round(val, 2),
        hvn_levels=[round(x, 2) for x in hvn],
        lvn_levels=[round(x, 2) for x in lvn],
        peakedness=round(peakedness, 1),
        clarity=round(clarity, 1),
        balance_label=balance,
        is_proxy=True,
        source="yahoo_vap_proxy",
        notes=notes,
        bin_count=n_bins,
        value_area_width_pts=round(va_width, 2),
    )


def apply_user_profile(
    base: VolumeProfileProxy,
    poc: Optional[float],
    vah: Optional[float],
    val: Optional[float],
    shape: str,
    note: str,
) -> VolumeProfileProxy:
    """Overlay trader-supplied session-profile numbers on the Yahoo proxy."""
    out = VolumeProfileProxy(**{**base.__dict__})
    used = []
    if poc is not None:
        out.poc = float(poc)
        used.append("POC")
    if vah is not None:
        out.vah = float(vah)
        used.append("VAH")
    if val is not None:
        out.val = float(val)
        used.append("VAL")
    shape = (shape or "auto").lower()
    if shape in {"balanced", "unbalanced", "trend"}:
        out.balance_label = "unbalanced" if shape == "trend" else shape
        used.append(f"shape={shape}")
        if shape == "balanced":
            out.clarity = max(out.clarity, 72.0)
        elif shape == "trend":
            out.clarity = min(out.clarity, 48.0)
            out.balance_label = "unbalanced"
    if used:
        out.is_proxy = False
        out.source = "user+proxy"
        extra = f"Trader overlay: {', '.join(used)}."
        if note:
            extra += " " + note.strip()
        out.notes = extra + " " + (base.notes or "")
        # User-defined nodes are more trustworthy for cleanliness.
        out.clarity = float(np.clip(out.clarity + 12.0, 0, 100))
    elif note:
        out.notes = note.strip() + " | " + (base.notes or "")
    return out


def _unique_round(xs: list[float], tick: float) -> list[float]:
    seen = set()
    out = []
    for x in xs:
        key = round(x / tick) * tick
        if key in seen:
            continue
        seen.add(key)
        out.append(float(key))
    return out
