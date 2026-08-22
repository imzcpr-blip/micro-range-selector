"""Bundled sample sessions so the app is demonstrable with no live futures feed."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from selector.config import ET_TZ, INSTRUMENTS, ORDERED_BOOKS
from selector.models import (
    CalendarEvent,
    DataGap,
    HtfContext,
    InstrumentMetrics,
    InternalsSnapshot,
    MarketBundle,
    OvernightStats,
    VolumeProfileProxy,
)
from selector.providers.base import SessionClock

ET = ZoneInfo(ET_TZ)

SCENARIOS = {
    "mes_default": "Demo · MES is the cleanest (default bias holds)",
    "mnq_clear": "Demo · MNQ clearly cleaner + higher opportunity",
    "sitout": "Demo · messy / event day — low conviction, stick with MES",
}


def load_mock_bundle(
    scenario: str,
    clock: SessionClock,
    fallback_reason: str | None = None,
) -> MarketBundle:
    scenario = scenario if scenario in SCENARIOS else "mes_default"
    builder = {
        "mes_default": _mes_default,
        "mnq_clear": _mnq_clear,
        "sitout": _sitout,
    }[scenario]
    bundle = builder(clock)
    bundle.using_mock = True
    bundle.mock_scenario = scenario
    if fallback_reason:
        bundle.price_notes.insert(
            0,
            f"LIVE DATA FAILED — using sample scenario '{scenario}'. Reason: {fallback_reason[:240]}",
        )
        bundle.gaps.insert(
            0,
            DataGap(
                key="live_fetch",
                detail=f"Yahoo fetch failed: {fallback_reason[:240]}",
                score_effect="All scores are DEMO. Do not trade off this print.",
            ),
        )
    else:
        bundle.price_notes.insert(0, f"DEMO MODE — bundled sample '{scenario}'. Not a live call.")
    return bundle


def _base_gaps(extra: list[DataGap] | None = None) -> list[DataGap]:
    gaps = [
        DataGap(
            key="vp_proxy",
            detail="Sample profile is illustrative. Live mode still uses a Yahoo VAP proxy unless you paste NT nodes.",
            score_effect="Cleanliness × 0.88 and confidence −8 when VP is proxy-only.",
        ),
        DataGap(
            key="order_flow",
            detail="Delta / bid-ask dominance is not in Yahoo. Confirm on Ironbeam / NinjaTrader.",
            score_effect="Alignment does not include real delta. Paste a lean to upgrade.",
        ),
    ]
    if extra:
        gaps.extend(extra)
    return gaps


def _sources(clock: SessionClock) -> list[dict]:
    return [
        {
            "name": "Bundled sample session",
            "used_for": "All OHLC, ATR, VP, VIX, ETF leadership",
            "status": "mock",
            "limitation": "Deterministic demo. Refresh with Live data when Yahoo is reachable.",
        },
        {
            "name": "Static US high-impact calendar",
            "used_for": "FOMC / CPI / NFP / GDP windows",
            "status": "static",
            "limitation": "Not a full economic calendar. Cross-check Forex Factory / TradingView.",
        },
        {
            "name": f"Session clock {clock.phase}",
            "used_for": "Which RTH date is being scored",
            "status": "live",
            "limitation": clock.note,
        },
    ]


def _mes_default(clock: SessionClock) -> MarketBundle:
    """Two-sided ES overnight, peaked POC, QQQ not vertical, VIX fadeable."""
    metrics = {
        "MES": _m(
            "MES",
            last=5642.25,
            on=(5658.0, 5624.5, 5642.25, 0.41, "live"),
            htf=("ranging", "1H ranging / choppy", 5642.25, 5672.0, 5618.0, 0.32),
            poc=5640.5,
            vah=5652.0,
            val=5631.0,
            clarity=78.0,
            balance="balanced",
            atr=48.0,
            rth=44.0,
            expected=42.0,
            vol_ratio=1.08,
            tests=(3, 3),
            er=0.34,
            rsi=48.0,
            pos=0.46,
        ),
        "MNQ": _m(
            "MNQ",
            last=20485.50,
            on=(20640.0, 20310.0, 20485.50, 0.58, "live"),
            htf=("up", "1H mild uptrend", 20485.5, 20720.0, 20240.0, 0.52),
            poc=20440.0,
            vah=20580.0,
            val=20355.0,
            clarity=58.0,
            balance="unbalanced",
            atr=240.0,
            rth=210.0,
            expected=195.0,
            vol_ratio=1.22,
            tests=(2, 1),
            er=0.57,
            rsi=62.0,
            pos=0.64,
            extra_warn=["Overnight leans one-way into the highs — fade quality is lower than MES."],
        ),
        "MYM": _m(
            "MYM",
            last=44820.0,
            on=(44980.0, 44640.0, 44820.0, 0.53, "live"),
            htf=("ranging", "1H mixed / mild drift", 44820.0, 45110.0, 44590.0, 0.44),
            poc=44790.0,
            vah=44910.0,
            val=44680.0,
            clarity=54.0,
            balance="balanced",
            atr=310.0,
            rth=260.0,
            expected=250.0,
            vol_ratio=0.82,
            tests=(2, 2),
            er=0.42,
            rsi=51.0,
            pos=0.51,
            extra_warn=["Depth is the weakest of the three. Dollar range vs $75 stop is only ~1.7R."],
        ),
    }
    internals = InternalsSnapshot(
        spy_pct=0.12,
        qqq_pct=0.28,
        dia_pct=0.05,
        leader="QQQ",
        laggard="DIA",
        spread_qqq_spy=0.16,
        vix_last=16.8,
        vix_change=-0.4,
        vix_regime="fadeable",
        notes=[
            "Leader QQQ (+0.28%) · laggard DIA (+0.05%).",
            "QQQ vs SPY +0.16 pp — mild tech lead, not a squeeze.",
            "VIX 16.8, down 0.4 — fadeable regime for HVN-edge mean reversion.",
        ],
    )
    return MarketBundle(
        as_of=clock.now.strftime("%Y-%m-%d %H:%M ET"),
        session_date=clock.target_rth.isoformat(),
        session_phase=clock.phase,
        overnight_ready=clock.overnight_ready,
        using_mock=True,
        mock_scenario="mes_default",
        price_notes=["Sample: balanced MES overnight, mild Nasdaq lead, VIX 16.8."],
        gaps=_base_gaps(),
        metrics=metrics,
        internals=internals,
        calendar=_cal(clock),
        calendar_source="static",
        mega_cap_earnings=[],
        sources_used=_sources(clock),
    )


def _mnq_clear(clock: SessionClock) -> MarketBundle:
    """ES drifting mid-value with a messy profile; NQ rotating in a defined range."""
    metrics = {
        "MES": _m(
            "MES",
            last=5618.00,
            on=(5648.0, 5602.0, 5618.0, 0.35, "live"),
            htf=("down", "1H downtrend", 5618.0, 5675.0, 5598.0, 0.61),
            poc=5634.0,
            vah=5646.0,
            val=5610.0,
            clarity=46.0,
            balance="unbalanced",
            atr=62.0,
            rth=58.0,
            expected=52.0,
            vol_ratio=0.91,
            tests=(1, 2),
            er=0.63,
            rsi=38.0,
            pos=0.26,
            extra_warn=["ES is leaving value lower. Profile is not a clean two-sided node."],
        ),
        "MNQ": _m(
            "MNQ",
            last=20110.00,
            on=(20240.0, 19980.0, 20110.0, 0.50, "live"),
            htf=("ranging", "1H ranging / choppy", 20110.0, 20310.0, 19940.0, 0.29),
            poc=20105.0,
            vah=20185.0,
            val=20020.0,
            clarity=84.0,
            balance="balanced",
            atr=220.0,
            rth=205.0,
            expected=200.0,
            vol_ratio=1.18,
            tests=(4, 3),
            er=0.28,
            rsi=51.0,
            pos=0.49,
        ),
        "MYM": _m(
            "MYM",
            last=44410.0,
            on=(44780.0, 44220.0, 44410.0, 0.34, "live"),
            htf=("down", "1H downtrend", 44410.0, 45100.0, 44180.0, 0.66),
            poc=44550.0,
            vah=44700.0,
            val=44300.0,
            clarity=42.0,
            balance="unbalanced",
            atr=380.0,
            rth=340.0,
            expected=310.0,
            vol_ratio=0.74,
            tests=(1, 1),
            er=0.68,
            rsi=34.0,
            pos=0.25,
            extra_warn=["Dow is trending, not rotating. Skip for CPRP limits."],
        ),
    }
    internals = InternalsSnapshot(
        spy_pct=-0.42,
        qqq_pct=0.08,
        dia_pct=-0.61,
        leader="QQQ",
        laggard="DIA",
        spread_qqq_spy=0.50,
        vix_last=18.4,
        vix_change=0.6,
        vix_regime="fadeable",
        notes=[
            "Nasdaq holding while ES/Dow leak — rotation, not a melt-up.",
            "MNQ overnight is two-sided around a peaked POC; ES is walking value lower.",
        ],
    )
    return MarketBundle(
        as_of=clock.now.strftime("%Y-%m-%d %H:%M ET"),
        session_date=clock.target_rth.isoformat(),
        session_phase=clock.phase,
        overnight_ready=clock.overnight_ready,
        using_mock=True,
        mock_scenario="mnq_clear",
        price_notes=["Sample: MNQ is the only clean two-sided book; MES is leaking value."],
        gaps=_base_gaps(),
        metrics=metrics,
        internals=internals,
        calendar=_cal(clock),
        calendar_source="static",
        mega_cap_earnings=[],
        sources_used=_sources(clock),
    )


def _sitout(clock: SessionClock) -> MarketBundle:
    """CPI morning: wide overnight, trending all three, VIX event-ish."""
    metrics = {
        "MES": _m(
            "MES",
            last=5588.50,
            on=(5680.0, 5568.0, 5588.50, 0.18, "live"),
            htf=("down", "1H downtrend", 5588.5, 5695.0, 5560.0, 0.74),
            poc=5620.0,
            vah=5660.0,
            val=5575.0,
            clarity=28.0,
            balance="unbalanced",
            atr=92.0,
            rth=88.0,
            expected=80.0,
            vol_ratio=1.85,
            tests=(1, 1),
            er=0.79,
            rsi=28.0,
            pos=0.21,
            extra_warn=["Event overnight. $75 stop is inside noise versus ATR."],
        ),
        "MNQ": _m(
            "MNQ",
            last=19740.00,
            on=(20480.0, 19620.0, 19740.0, 0.14, "live"),
            htf=("down", "1H downtrend", 19740.0, 20550.0, 19580.0, 0.81),
            poc=20010.0,
            vah=20280.0,
            val=19680.0,
            clarity=22.0,
            balance="unbalanced",
            atr=410.0,
            rth=390.0,
            expected=360.0,
            vol_ratio=2.10,
            tests=(1, 1),
            er=0.84,
            rsi=22.0,
            pos=0.16,
            extra_warn=["MNQ is the event vehicle. Do not mean-revert a CPI dump on a $50–$100 stop."],
        ),
        "MYM": _m(
            "MYM",
            last=43980.0,
            on=(44860.0, 43840.0, 43980.0, 0.14, "live"),
            htf=("down", "1H downtrend", 43980.0, 45020.0, 43790.0, 0.72),
            poc=44300.0,
            vah=44640.0,
            val=43920.0,
            clarity=30.0,
            balance="unbalanced",
            atr=520.0,
            rth=480.0,
            expected=440.0,
            vol_ratio=1.60,
            tests=(1, 1),
            er=0.77,
            rsi=26.0,
            pos=0.16,
        ),
    }
    internals = InternalsSnapshot(
        spy_pct=-1.85,
        qqq_pct=-2.40,
        dia_pct=-1.55,
        leader="DIA",
        laggard="QQQ",
        spread_qqq_spy=-0.55,
        vix_last=27.6,
        vix_change=4.8,
        vix_regime="elevated",
        notes=["Risk-off dump across all three. VIX +4.8 into 27.6. CPRP sit-out until value rebuilds."],
    )
    extra = [
        DataGap(
            key="event_day",
            detail="Sample is an 08:30 CPI-style event overnight.",
            score_effect="Alignment heavily penalized. Sit-out warning fires.",
        )
    ]
    cal = [
        CalendarEvent(
            date=clock.target_rth.isoformat(),
            time="08:30",
            title="CPI (sample event day)",
            impact="high",
            source="mock",
        )
    ]
    return MarketBundle(
        as_of=clock.now.strftime("%Y-%m-%d %H:%M ET"),
        session_date=clock.target_rth.isoformat(),
        session_phase=clock.phase,
        overnight_ready=clock.overnight_ready,
        using_mock=True,
        mock_scenario="sitout",
        price_notes=["Sample: CPI dump. All three books are trending. Selector should warn sit-out."],
        gaps=_base_gaps(extra),
        metrics=metrics,
        internals=internals,
        calendar=cal,
        calendar_source="mock",
        mega_cap_earnings=["NVDA earnings (sample)"],
        sources_used=_sources(clock),
    )


def _cal(clock: SessionClock) -> list[CalendarEvent]:
    # Quiet-ish sample: GDP later in the week, no red folder today unless sitout.
    d = clock.target_rth.isoformat()
    return [
        CalendarEvent(date=d, time="", title="No high-impact US print on the sample session", impact="low", source="mock"),
        CalendarEvent(
            date="2026-08-26",
            time="08:30",
            title="GDP (Second Estimate) Q2",
            impact="high",
            source="static",
        ),
    ]


def _m(
    short: str,
    *,
    last: float,
    on: tuple,
    htf: tuple,
    poc: float,
    vah: float,
    val: float,
    clarity: float,
    balance: str,
    atr: float,
    rth: float,
    expected: float,
    vol_ratio: float,
    tests: tuple[int, int],
    er: float,
    rsi: float,
    pos: float,
    extra_warn: list[str] | None = None,
) -> InstrumentMetrics:
    inst = INSTRUMENTS[short]
    on_hi, on_lo, on_last, on_er, on_src = on
    rng = on_hi - on_lo
    position = (on_last - on_lo) / rng if rng else 0.5
    htf_bias, htf_label, htf_last, htf_hi, htf_lo, htf_er = htf
    return InstrumentMetrics(
        short=short,
        name=inst.name,
        last_price=last,
        price_source="mock",
        overnight=OvernightStats(
            high=on_hi,
            low=on_lo,
            last=on_last,
            range_pts=round(rng, 2),
            range_usd=round(rng * inst.point_value, 2),
            position=round(position, 3),
            efficiency=on_er,
            bar_count=42,
            source=on_src,
            note="Bundled overnight sample.",
        ),
        htf=HtfContext(
            bias=htf_bias,
            label=htf_label,
            last=htf_last,
            high=htf_hi,
            low=htf_lo,
            efficiency=htf_er,
            note="Bundled 1H context.",
        ),
        profile=VolumeProfileProxy(
            poc=poc,
            vah=vah,
            val=val,
            hvn_levels=[poc],
            lvn_levels=[round((poc + val) / 2, 2)],
            peakedness=clarity,
            clarity=clarity,
            balance_label=balance,
            is_proxy=True,
            source="mock",
            notes="Sample HVN/LVN. Replace with NinjaTrader session profile in live use.",
            bin_count=48,
            value_area_width_pts=round(vah - val, 2),
        ),
        atr14_pts=atr,
        atr14_usd=round(atr * inst.point_value, 2),
        recent_rth_range_pts=rth,
        recent_rth_range_usd=round(rth * inst.point_value, 2),
        expected_rth_pts=expected,
        expected_rth_usd=round(expected * inst.point_value, 2),
        prior_day_volume=1_000_000 if short == "MES" else (800_000 if short == "MNQ" else 220_000),
        volume_vs_20d=vol_ratio,
        open_interest=None,
        etf_overnight_pct=None,
        dual_side_high_tests=tests[0],
        dual_side_low_tests=tests[1],
        path_efficiency=er,
        rsi14=rsi,
        position_in_htf_range=pos,
        typical_rth_pts=inst.typical_rth_pts,
        tick_value=inst.tick_value,
        point_value=inst.point_value,
        tick_size=inst.tick_size,
        warnings=list(extra_warn or []),
    )
