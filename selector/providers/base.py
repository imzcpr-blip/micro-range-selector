"""Session clock, disk cache, and overlay application."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from selector.config import CACHE_DIR, DISK_CACHE_MAX_AGE_HOURS, ET_TZ, GLOBEX_OPEN, RTH_CLOSE, RTH_OPEN
from selector.models import DataGap, MarketBundle, OvernightStats, UserOverlays, VolumeProfileProxy, _to_jsonable
from selector.volume_profile import apply_user_profile

ET = ZoneInfo(ET_TZ)


@dataclass
class SessionClock:
    now: datetime
    target_rth: date
    last_completed_rth: date
    phase: str
    overnight_ready: bool
    overnight_label: str
    note: str


def session_clock(now: Optional[datetime] = None) -> SessionClock:
    now = now or datetime.now(ET)
    if now.tzinfo is None:
        now = now.replace(tzinfo=ET)
    else:
        now = now.astimezone(ET)

    t = now.time()
    wd = now.weekday()  # Mon=0
    open_t = time(*RTH_OPEN)
    close_t = time(*RTH_CLOSE)
    globex_t = time(*GLOBEX_OPEN)

    last_completed = _last_weekday(now.date() if t >= close_t else now.date() - timedelta(days=1))
    if t < close_t and wd < 5 and t >= open_t:
        last_completed = _last_weekday(now.date() - timedelta(days=1)) if wd > 0 else _last_weekday(now.date() - timedelta(days=1))

    if wd >= 5:
        target = _next_weekday(now.date())
        # Sunday after 18:00 ET: overnight for Monday is live.
        if wd == 6 and t >= globex_t:
            phase = "overnight_globex"
            overnight_ready = True
            label = "Sunday Globex → Monday RTH"
            note = "Monday overnight is open. Score from live Globex + Monday calendar."
        else:
            phase = "weekend"
            overnight_ready = False
            label = "Weekend — next RTH Monday"
            note = (
                "Overnight for Monday is not open yet (CME Globex Sunday 18:00 ET). "
                "Scores use Friday's structure + Monday's calendar. Refresh after Sunday 18:00."
            )
        return SessionClock(now, target, last_completed, phase, overnight_ready, label, note)

    if t < open_t:
        # Overnight for today. Globex opened previous calendar evening (or Sunday).
        overnight_ready = True
        if t < time(6, 0):
            phase = "overnight_globex"
        else:
            phase = "pre_market"
        return SessionClock(
            now,
            now.date(),
            last_completed,
            phase,
            True,
            f"Overnight → {now.strftime('%A')} RTH",
            "Pre-RTH. Use overnight range, VP proxy, and the 08:30 calendar. Open the book 30–60 minutes before 09:30.",
        )

    if t < close_t:
        return SessionClock(
            now,
            now.date(),
            last_completed,
            "rth_live",
            True,
            f"RTH live {now.strftime('%A')}",
            "Regular trading hours are live. Selector is a focus tool — entries still come from platform order flow at HVN/LVN edges.",
        )

    # After 16:00 ET weekdays. Next RTH is tomorrow (or Monday).
    nxt = _next_weekday(now.date() + timedelta(days=1)) if t < globex_t else _next_weekday(now.date() + timedelta(days=1))
    if t >= globex_t:
        nxt = _next_weekday(now.date() + timedelta(days=1))
        return SessionClock(
            now,
            nxt,
            now.date() if wd < 5 else last_completed,
            "overnight_globex",
            True,
            f"Overnight → {nxt.strftime('%A')} RTH",
            "Next-session Globex is open. Score the upcoming RTH book.",
        )
    return SessionClock(
        now,
        nxt,
        now.date(),
        "after_hours",
        False,
        f"Post-close — next RTH {nxt.strftime('%A')}",
        "RTH is closed. Globex reopens 18:00 ET. Scores use today's completed session until overnight prints.",
    )


def overnight_window(rth_date: date) -> tuple[datetime, datetime]:
    """Globex overnight for an RTH date: prior 18:00 ET → 09:30 ET."""
    end = datetime.combine(rth_date, time(*RTH_OPEN), tzinfo=ET)
    if rth_date.weekday() == 0:
        start = datetime.combine(rth_date - timedelta(days=1), time(*GLOBEX_OPEN), tzinfo=ET)
    else:
        start = datetime.combine(rth_date - timedelta(days=1), time(*GLOBEX_OPEN), tzinfo=ET)
    return start, end


def rth_window(rth_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(rth_date, time(*RTH_OPEN), tzinfo=ET)
    end = datetime.combine(rth_date, time(*RTH_CLOSE), tzinfo=ET)
    return start, end


def slice_index(df, start: datetime, end: datetime):
    if df is None or df.empty:
        return df
    return df[(df.index >= start) & (df.index < end)]


def _next_weekday(d: date) -> date:
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _last_weekday(d: date) -> date:
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def disk_cache_load(key: str) -> Optional[MarketBundle]:
    path = CACHE_DIR / f"{key}.json"
    if not path.is_file():
        return None
    age_h = (datetime.now(ET) - datetime.fromtimestamp(path.stat().st_mtime, tz=ET)).total_seconds() / 3600
    if age_h > DISK_CACHE_MAX_AGE_HOURS:
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return _bundle_from_dict(raw)
    except Exception:
        return None


def disk_cache_save(key: str, bundle: MarketBundle) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{key}.json"
    payload = _to_jsonable(asdict(bundle))
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def apply_overlays(bundle: MarketBundle, overlays: UserOverlays) -> None:
    """Mutate bundle metrics with trader-supplied overnight / VP numbers."""
    for short, m in bundle.metrics.items():
        hi = overlays.on_high.get(short)
        lo = overlays.on_low.get(short)
        if hi is not None and lo is not None and hi > lo:
            last = m.overnight.last if m.overnight.last else (hi + lo) / 2
            rng = hi - lo
            pos = (last - lo) / rng if rng else 0.5
            m.overnight = OvernightStats(
                high=float(hi),
                low=float(lo),
                last=float(last),
                range_pts=float(rng),
                range_usd=float(rng) * m.point_value,
                position=float(max(0.0, min(1.0, pos))),
                efficiency=m.overnight.efficiency,
                bar_count=m.overnight.bar_count,
                source="user",
                note="Overnight high/low supplied by trader.",
            )
        shape = overlays.profile_shape.get(short, "auto")
        note = overlays.notes.get(short, "")
        m.profile = apply_user_profile(
            m.profile,
            overlays.poc.get(short),
            overlays.vah.get(short),
            overlays.val.get(short),
            shape,
            note,
        )
        lean = overlays.delta_lean.get(short, "")
        if lean and lean not in {"unknown", "auto", ""}:
            m.warnings = [w for w in m.warnings if "delta" not in w.lower()]
            m.profile.notes = f"Delta lean: {lean}. " + (m.profile.notes or "")
        if m.profile.source.startswith("user"):
            bundle.gaps = [g for g in bundle.gaps if g.key != f"vp_{short}"]
    if overlays.high_impact_override is True:
        bundle.gaps.append(
            DataGap(
                key="calendar_override",
                detail="Trader marked this as a high-impact event day.",
                score_effect="CPRP alignment haircut on all books; extra MNQ penalty.",
            )
        )


def _bundle_from_dict(raw: dict) -> MarketBundle:
    """Best-effort rebuild. If the cache shape drifts, callers fall back to live/mock."""
    from models import (
        CalendarEvent,
        HtfContext,
        InstrumentMetrics,
        InternalsSnapshot,
        OvernightStats,
        VolumeProfileProxy,
    )

    def _dc(cls, d, **extra):
        if not isinstance(d, dict):
            raise TypeError
        fields = {k: d[k] for k in d if k in cls.__dataclass_fields__}
        fields.update(extra)
        return cls(**fields)

    metrics = {}
    for short, md in (raw.get("metrics") or {}).items():
        metrics[short] = _dc(
            InstrumentMetrics,
            md,
            overnight=_dc(OvernightStats, md["overnight"]),
            htf=_dc(HtfContext, md["htf"]),
            profile=_dc(VolumeProfileProxy, md["profile"]),
            typical_rth_pts=tuple(md.get("typical_rth_pts") or (0, 0)),
        )
    internals = _dc(InternalsSnapshot, raw["internals"])
    gaps = [_dc(DataGap, g) for g in raw.get("gaps") or []]
    calendar = [_dc(CalendarEvent, e) for e in raw.get("calendar") or []]
    return MarketBundle(
        as_of=raw["as_of"],
        session_date=raw["session_date"],
        session_phase=raw["session_phase"],
        overnight_ready=bool(raw.get("overnight_ready")),
        using_mock=bool(raw.get("using_mock")),
        mock_scenario=raw.get("mock_scenario"),
        price_notes=list(raw.get("price_notes") or []),
        gaps=gaps,
        metrics=metrics,
        internals=internals,
        calendar=calendar,
        calendar_source=raw.get("calendar_source", "cache"),
        mega_cap_earnings=list(raw.get("mega_cap_earnings") or []),
        sources_used=list(raw.get("sources_used") or []),
    )
