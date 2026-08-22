"""Dataclasses for market snapshots, factor scores, and the daily recommendation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Optional


def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if hasattr(obj, "item"):  # numpy scalar
        try:
            return obj.item()
        except Exception:
            return obj
    return obj


@dataclass
class DataGap:
    key: str
    detail: str
    score_effect: str


@dataclass
class CalendarEvent:
    date: str
    time: str
    title: str
    impact: str  # high | medium | low
    country: str = "US"
    source: str = "unknown"
    forecast: str = ""
    previous: str = ""


@dataclass
class OvernightStats:
    high: float
    low: float
    last: float
    range_pts: float
    range_usd: float
    position: float  # 0 = low, 1 = high
    efficiency: float
    bar_count: int
    source: str  # live | user | mock | prior_session
    note: str = ""


@dataclass
class VolumeProfileProxy:
    poc: float
    vah: float
    val: float
    hvn_levels: list[float]
    lvn_levels: list[float]
    peakedness: float  # 0–100
    clarity: float  # 0–100
    balance_label: str  # balanced | unbalanced | unknown
    is_proxy: bool
    source: str
    notes: str = ""
    bin_count: int = 0
    value_area_width_pts: float = 0.0


@dataclass
class HtfContext:
    bias: str  # up | down | ranging | unknown
    label: str
    last: float
    high: float
    low: float
    efficiency: float
    note: str


@dataclass
class InstrumentMetrics:
    short: str
    name: str
    last_price: float
    price_source: str  # MES=F | ES=F | mock | user
    overnight: OvernightStats
    htf: HtfContext
    profile: VolumeProfileProxy
    atr14_pts: float
    atr14_usd: float
    recent_rth_range_pts: float
    recent_rth_range_usd: float
    expected_rth_pts: float
    expected_rth_usd: float
    prior_day_volume: float
    volume_vs_20d: float  # 1.0 = average
    open_interest: Optional[float]
    etf_overnight_pct: Optional[float]
    dual_side_high_tests: int
    dual_side_low_tests: int
    path_efficiency: float
    rsi14: float
    position_in_htf_range: float
    typical_rth_pts: tuple[float, float]
    tick_value: float
    point_value: float
    tick_size: float
    warnings: list[str] = field(default_factory=list)


@dataclass
class InternalsSnapshot:
    spy_pct: Optional[float]
    qqq_pct: Optional[float]
    dia_pct: Optional[float]
    leader: str  # SPY | QQQ | DIA | mixed | unknown
    laggard: str
    spread_qqq_spy: Optional[float]
    vix_last: Optional[float]
    vix_change: Optional[float]
    vix_regime: str  # grind | fadeable | elevated | event | unknown
    tick_last: Optional[float] = None
    add_last: Optional[float] = None
    vold_last: Optional[float] = None
    notes: list[str] = field(default_factory=list)


@dataclass
class FactorScore:
    key: str
    label: str
    weight: float
    raw: float  # 0–100
    weighted: float
    bullets: list[str] = field(default_factory=list)


@dataclass
class ScoredInstrument:
    short: str
    name: str
    composite: float  # includes MES bias
    composite_pre_bias: float
    mes_bias: float
    confidence_contrib: float
    grade: str
    factors: list[FactorScore]
    metrics: InstrumentMetrics
    reasons: list[str]
    warnings: list[str]
    max_contracts_50: int
    max_contracts_100: int
    stop_pts_at_default: float
    suggested_stop_pts: float
    suggested_stop_usd: float


@dataclass
class UserOverlays:
    """Optional trader-supplied overnight / VP / delta notes.

    Empty fields are ignored; filled fields override Yahoo proxies.
    """

    on_high: dict[str, Optional[float]] = field(default_factory=dict)
    on_low: dict[str, Optional[float]] = field(default_factory=dict)
    poc: dict[str, Optional[float]] = field(default_factory=dict)
    vah: dict[str, Optional[float]] = field(default_factory=dict)
    val: dict[str, Optional[float]] = field(default_factory=dict)
    delta_lean: dict[str, str] = field(default_factory=dict)  # bid | ask | mixed | unknown
    profile_shape: dict[str, str] = field(default_factory=dict)  # balanced | unbalanced | trend | auto
    notes: dict[str, str] = field(default_factory=dict)
    high_impact_override: Optional[bool] = None  # True = treat as red-folder day


@dataclass
class MarketBundle:
    as_of: str
    session_date: str  # target RTH date YYYY-MM-DD
    session_phase: str
    overnight_ready: bool
    using_mock: bool
    mock_scenario: Optional[str]
    price_notes: list[str]
    gaps: list[DataGap]
    metrics: dict[str, InstrumentMetrics]
    internals: InternalsSnapshot
    calendar: list[CalendarEvent]
    calendar_source: str
    mega_cap_earnings: list[str]
    sources_used: list[dict]


@dataclass
class Recommendation:
    pick: str
    pick_name: str
    confidence: int
    summary: str
    sit_out_warning: bool
    switch_from_mes: bool
    mode: str
    hard_stop_usd: float
    session_date: str
    session_phase: str
    as_of: str
    using_mock: bool
    scores: list[ScoredInstrument]
    weights: dict[str, float]
    mes_bias_points: float
    switch_margin: float
    internals: InternalsSnapshot
    calendar: list[CalendarEvent]
    gaps: list[DataGap]
    sources_used: list[dict]
    formula: str
    override_notes: str = ""

    def to_dict(self) -> dict:
        return _to_jsonable(asdict(self))
