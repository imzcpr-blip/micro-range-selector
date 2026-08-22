"""Market-data providers. Live Yahoo first, mock fallback, overlays last."""

from __future__ import annotations

from selector.models import MarketBundle, UserOverlays
from selector.providers.base import apply_overlays, disk_cache_load, disk_cache_save, session_clock
from selector.providers.calendar_provider import fetch_calendar, fetch_mega_cap_earnings
from selector.providers.mock_provider import SCENARIOS, load_mock_bundle
from selector.providers.yfinance_provider import fetch_live_bundle


def load_market_bundle(
    *,
    force_mock: bool = False,
    scenario: str = "mes_default",
    overlays: UserOverlays | None = None,
    use_disk_cache: bool = True,
) -> MarketBundle:
    clock = session_clock()
    cache_key = clock.target_rth.isoformat()

    if force_mock:
        bundle = load_mock_bundle(scenario, clock)
        if overlays:
            apply_overlays(bundle, overlays)
        return bundle

    if use_disk_cache:
        cached = disk_cache_load(cache_key)
        if cached is not None and not cached.using_mock:
            if overlays:
                apply_overlays(cached, overlays)
            return cached

    try:
        bundle = fetch_live_bundle(clock)
        bundle.calendar, bundle.calendar_source = fetch_calendar(clock.target_rth)
        bundle.mega_cap_earnings = fetch_mega_cap_earnings()
        if use_disk_cache:
            disk_cache_save(cache_key, bundle)
    except Exception as exc:  # noqa: BLE001 — live data is best-effort
        bundle = load_mock_bundle(scenario, clock, fallback_reason=str(exc))

    if overlays:
        apply_overlays(bundle, overlays)
    return bundle


__all__ = [
    "SCENARIOS",
    "load_market_bundle",
    "session_clock",
]
