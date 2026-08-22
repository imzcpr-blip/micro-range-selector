"""Economic calendar — live Forex Factory JSON when it works, static US high-impact fallback."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

import requests

from selector.config import MEGA_CAPS, STATIC_HIGH_IMPACT_2026
from selector.models import CalendarEvent

FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
TIMEOUT = 8


def fetch_calendar(session_date: date) -> tuple[list[CalendarEvent], str]:
    live: list[CalendarEvent] = []
    source = "static"
    try:
        resp = requests.get(FF_URL, timeout=TIMEOUT, headers={"User-Agent": "CPRP-Micro-Selector/1.0"})
        resp.raise_for_status()
        payload = resp.json()
        live = _parse_ff(payload, session_date)
        if live or payload:
            source = "forexfactory_json+static"
    except Exception:
        live = []
        source = "static"

    static = [
        CalendarEvent(
            date=e["date"],
            time=e.get("time", ""),
            title=e["title"],
            impact=e.get("impact", "high"),
            country="US",
            source="static",
        )
        for e in STATIC_HIGH_IMPACT_2026
        if _within(e["date"], session_date, days=7)
    ]
    # Prefer live for the session date; keep static for known FOMC/CPI/NFP if live missed them.
    merged: dict[tuple, CalendarEvent] = {}
    for ev in static + live:
        key = (ev.date, ev.title.lower()[:40])
        merged[key] = ev
    events = sorted(merged.values(), key=lambda e: (e.date, e.time or "99:99"))
    return events, source


def session_impact(events: list[CalendarEvent], session_date: date, override: Optional[bool] = None) -> str:
    """high | medium | none — used by the alignment scorer."""
    if override is True:
        return "high"
    if override is False:
        return "none"
    day = session_date.isoformat()
    todays = [e for e in events if e.date == day]
    if any(e.impact == "high" for e in todays):
        return "high"
    if any(e.impact == "medium" for e in todays):
        return "medium"
    return "none"


def fetch_mega_cap_earnings() -> list[str]:
    """Best-effort next earnings window for mega-caps. Failures are silent."""
    out: list[str] = []
    try:
        import yfinance as yf
    except Exception:
        return out
    today = date.today()
    for sym in MEGA_CAPS:
        try:
            cal = yf.Ticker(sym).calendar
            if cal is None:
                continue
            raw = None
            if isinstance(cal, dict):
                raw = cal.get("Earnings Date") or cal.get("earningsDate")
            elif hasattr(cal, "loc") and "Earnings Date" in getattr(cal, "index", []):
                raw = cal.loc["Earnings Date"]
            dates = _as_dates(raw)
            for d in dates:
                if 0 <= (d - today).days <= 7:
                    out.append(f"{sym} earnings {d.isoformat()}")
        except Exception:
            continue
    return out


def _parse_ff(payload, session_date: date) -> list[CalendarEvent]:
    events = []
    rows = payload if isinstance(payload, list) else payload.get("events") or payload.get("calendar") or []
    lo = session_date - timedelta(days=1)
    hi = session_date + timedelta(days=6)
    for row in rows:
        if not isinstance(row, dict):
            continue
        country = str(row.get("country") or row.get("countryCode") or "").upper()
        if country not in {"US", "USA", "UNITED STATES", ""}:
            # Keep US only; empty country allowed if title looks US-macro.
            title_l = str(row.get("title") or row.get("event") or "").lower()
            if not any(k in title_l for k in ("fomc", "cpi", "nonfarm", "payroll", "fed ", "gdp", "pce")):
                continue
        title = str(row.get("title") or row.get("event") or "Event")
        impact = _impact(row.get("impact") or row.get("importance") or "")
        dt = _ff_date(row)
        if dt is None or dt < lo or dt > hi:
            continue
        tm = ""
        if row.get("time"):
            tm = str(row["time"])[:5]
        elif row.get("date"):
            tm = str(row["date"])[11:16]
        events.append(
            CalendarEvent(
                date=dt.isoformat(),
                time=tm,
                title=title,
                impact=impact,
                country="US",
                source="forexfactory_json",
                forecast=str(row.get("forecast") or ""),
                previous=str(row.get("previous") or ""),
            )
        )
    return events


def _impact(raw) -> str:
    s = str(raw).strip().lower()
    if s in {"high", "red", "3", "holiday"}:
        return "high" if s != "holiday" else "low"
    if s in {"medium", "orange", "2"}:
        return "medium"
    if s in {"low", "yellow", "1"}:
        return "low"
    if "high" in s:
        return "high"
    if "medium" in s:
        return "medium"
    return "low"


def _ff_date(row: dict) -> Optional[date]:
    for key in ("date", "datetime", "timestamp"):
        val = row.get(key)
        if val is None:
            continue
        try:
            if isinstance(val, (int, float)):
                ts = val / 1000 if val > 10_000_000_000 else val
                return datetime.utcfromtimestamp(ts).date()
            s = str(val)[:10]
            return date.fromisoformat(s)
        except Exception:
            continue
    return None


def _within(iso: str, session: date, days: int) -> bool:
    try:
        d = date.fromisoformat(iso)
    except Exception:
        return False
    return abs((d - session).days) <= days


def _as_dates(raw) -> list[date]:
    if raw is None:
        return []
    if hasattr(raw, "tolist"):
        raw = raw.tolist()
    if not isinstance(raw, (list, tuple)):
        raw = [raw]
    out = []
    for item in raw:
        try:
            if hasattr(item, "date"):
                out.append(item.date() if not isinstance(item, date) else item)
            else:
                out.append(date.fromisoformat(str(item)[:10]))
        except Exception:
            continue
    return out
