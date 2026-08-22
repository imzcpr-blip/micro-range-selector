"""Hard-stop position sizing for CPRP (−$50 to −$100)."""

from __future__ import annotations

from dataclasses import dataclass

from selector.config import HARD_STOP_DEFAULT_USD, HARD_STOP_MAX_USD, HARD_STOP_MIN_USD, INSTRUMENTS


@dataclass
class SizePlan:
    short: str
    risk_usd: float
    stop_pts: float
    stop_ticks: float
    usd_per_contract: float
    contracts: int
    actual_risk_usd: float
    note: str


def stop_pts_for_usd(short: str, risk_usd: float) -> float:
    inst = INSTRUMENTS[short]
    return risk_usd / inst.point_value


def usd_for_stop_pts(short: str, stop_pts: float) -> float:
    inst = INSTRUMENTS[short]
    return stop_pts * inst.point_value


def suggested_stop_pts(
    short: str,
    overnight_range_pts: float,
    atr14_pts: float,
    hard_stop_usd: float = HARD_STOP_DEFAULT_USD,
) -> float:
    """Distance from an HVN/LVN edge that still fits the hard stop.

    Uses the tighter of: 25% of overnight range, 15% of ATR, and the dollar cap.
    """
    inst = INSTRUMENTS[short]
    cap = hard_stop_usd / inst.point_value
    node = overnight_range_pts * 0.30 if overnight_range_pts > 0 else cap
    atr_frac = atr14_pts * 0.20 if atr14_pts > 0 else cap
    raw = min(p for p in (node, atr_frac, cap) if p > 0)
    # At least a few ticks so the number is executable.
    return max(raw, inst.tick_size * 4)


def max_contracts(short: str, stop_pts: float, risk_usd: float) -> int:
    inst = INSTRUMENTS[short]
    usd = stop_pts * inst.point_value
    if usd <= 0:
        return 1
    n = int(risk_usd // usd)
    return max(n, 0)


def plan(
    short: str,
    stop_pts: float,
    risk_usd: float,
) -> SizePlan:
    inst = INSTRUMENTS[short]
    risk_usd = float(np_clip(risk_usd, HARD_STOP_MIN_USD, HARD_STOP_MAX_USD * 4))
    stop_pts = max(float(stop_pts), inst.tick_size)
    usd = stop_pts * inst.point_value
    ticks = stop_pts / inst.tick_size
    n = max_contracts(short, stop_pts, risk_usd)
    if n < 1:
        note = (
            f"Even 1 {short} at {stop_pts:.2f} pts (${usd:.0f}) exceeds a ${risk_usd:.0f} risk cap. "
            "Wait for a tighter node or sit out."
        )
        actual = usd
        n = 0
    else:
        actual = n * usd
        note = (
            f"{n} {short} × {stop_pts:.2f} pts ({ticks:.0f} ticks) = ${actual:.0f} "
            f"(tick ${inst.tick_value:.2f}). Protocol default is 1 micro."
        )
        if n > 2:
            note += " CPRP typically runs 1 contract — size above 2 is outside the spirit of −$50/−$100."
            n = min(n, 2)
            actual = n * usd
    return SizePlan(
        short=short,
        risk_usd=risk_usd,
        stop_pts=round(stop_pts, 4),
        stop_ticks=round(ticks, 2),
        usd_per_contract=round(usd, 2),
        contracts=n,
        actual_risk_usd=round(actual, 2),
        note=note,
    )


def np_clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def sizing_notes(short: str, hard_stop_usd: float, stop_pts: float) -> list[str]:
    inst = INSTRUMENTS[short]
    lo, hi = inst.typical_rth_pts
    return [
        f"Tick {inst.tick_size:g} pts = ${inst.tick_value:.2f}  ·  1.00 pt = ${inst.point_value:.2f}",
        f"Typical RTH range {lo:.0f}–{hi:.0f} pts (${lo * inst.point_value:.0f}–${hi * inst.point_value:.0f})",
        (
            f"${hard_stop_usd:.0f} hard stop = {hard_stop_usd / inst.point_value:.2f} pts "
            f"({hard_stop_usd / inst.tick_value:.0f} ticks)"
        ),
        (
            f"Suggested structure stop {stop_pts:.2f} pts = ${stop_pts * inst.point_value:.0f} "
            f"per contract"
        ),
        "Hard daily risk is −$50 to −$100. No averaging down. Micros only.",
    ]
