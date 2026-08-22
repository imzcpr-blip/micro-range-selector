"""CPRP Micro Selector — protocol constants, instruments, and default weights.

Cooper Precision Reversion Protocol (CPRP)
Order-flow + session volume-profile mean reversion on Micro E-mini equity index futures.

Hard risk: −$50 to −$100 per trade. Micros only. MES is the default book.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROTOCOL_NAME = "Cooper Precision Reversion Protocol"
PROTOCOL_SHORT = "CPRP"
APP_NAME = "CPRP Micro Selector"
APP_TAGLINE = "Cleanest book. Realistic R. Stick with MES unless another clearly wins."
CREATOR = "Raymon Michael Cooper"
RULEBOOK_VERSION = "1.7"

_PKG = Path(__file__).resolve().parent
ROOT = _PKG.parent  # micro-range-selector repo root
CACHE_DIR = ROOT / "cache"
LOG_DIR = ROOT / "logs"
SAMPLES_DIR = _PKG / "samples"

ET_TZ = "America/New_York"
RTH_OPEN = (9, 30)
RTH_CLOSE = (16, 0)
GLOBEX_OPEN = (18, 0)

HARD_STOP_MIN_USD = 50.0
HARD_STOP_MAX_USD = 100.0
HARD_STOP_DEFAULT_USD = 75.0

# Composite 0–100. Below this we still name a focus book, but flag low conviction.
MIN_SCORE_TO_TRADE = 55.0

# Challenger must beat MES by this much AFTER the MES bias is applied.
SWITCH_MARGIN = 8.0

# Added to MES composite only. Liquidity, smoother tape, protocol familiarity.
MES_BIAS_POINTS = 6.0

# When volume-profile depth is a Yahoo VAP proxy (not CME footprint / NT profile).
VP_PROXY_CLEANLINESS_MULT = 0.88
VP_PROXY_CONFIDENCE_HAIRCUT = 8.0
MISSING_CALENDAR_HAIRCUT = 4.0
MISSING_VIX_HAIRCUT = 3.0
MOCK_OR_PARTIAL_HAIRCUT = 6.0

# Scoring category weights — must sum to 1.0. Sidebar sliders re-normalize.
DEFAULT_WEIGHTS: dict[str, float] = {
    "cleanliness": 0.28,
    "profit_potential": 0.22,
    "liquidity": 0.18,
    "cprp_alignment": 0.18,
    "leadership": 0.14,
}

WEIGHT_LABELS = {
    "cleanliness": "Setup Cleanliness",
    "profit_potential": "Profit Potential",
    "liquidity": "Liquidity & Execution",
    "cprp_alignment": "CPRP Alignment",
    "leadership": "Relative Leadership",
}

WEIGHT_HELP = {
    "cleanliness": (
        "Clarity of the higher-timeframe range, dual-side tests, and HVN/LVN edges. "
        "Balanced profiles score higher than one-way imbalance."
    ),
    "profit_potential": (
        "Expected RTH dollar range versus a $50–$100 hard stop. "
        "Sweet spot is roughly 2.5×–5.5× the stop — enough R, still mean-reversion sized."
    ),
    "liquidity": (
        "Fill quality and depth. MES is structurally first. Prior-day volume and "
        "open interest (when Yahoo provides it) adjust the base."
    ),
    "cprp_alignment": (
        "Mean-reversion friendliness: two-sided overnight, overlapping value, "
        "VIX in a fadeable regime, no red-folder blow-off into the open."
    ),
    "leadership": (
        "Which index has the opportunity without being the runaway trend vehicle. "
        "Moderate rotation beats a vertical leader for limit-at-the-node entries."
    ),
}


@dataclass(frozen=True)
class Instrument:
    short: str
    name: str
    yahoo_micro: str
    yahoo_emini: str  # more reliable Yahoo continuous; same index points
    etf: str
    point_value: float
    tick_size: float
    tick_value: float
    typical_rth_pts: tuple[float, float]
    liquidity_base: float  # 0–100 structural liquidity score
    priority: int  # 1 = MES
    notes: str


INSTRUMENTS: dict[str, Instrument] = {
    "MES": Instrument(
        short="MES",
        name="Micro E-mini S&P 500",
        yahoo_micro="MES=F",
        yahoo_emini="ES=F",
        etf="SPY",
        point_value=5.0,
        tick_size=0.25,
        tick_value=1.25,
        typical_rth_pts=(30.0, 70.0),
        liquidity_base=90.0,
        priority=1,
        notes="Primary book — default unless another instrument clearly wins.",
    ),
    "MNQ": Instrument(
        short="MNQ",
        name="Micro E-mini Nasdaq-100",
        yahoo_micro="MNQ=F",
        yahoo_emini="NQ=F",
        etf="QQQ",
        point_value=2.0,
        tick_size=0.25,
        tick_value=0.50,
        typical_rth_pts=(140.0, 320.0),
        liquidity_base=78.0,
        priority=2,
        notes="Secondary — only when cleanliness + opportunity beat MES by the switch margin.",
    ),
    "MYM": Instrument(
        short="MYM",
        name="Micro E-mini Dow",
        yahoo_micro="MYM=F",
        yahoo_emini="YM=F",
        etf="DIA",
        point_value=0.50,
        tick_size=1.0,
        tick_value=0.50,
        typical_rth_pts=(180.0, 420.0),
        liquidity_base=58.0,
        priority=3,
        notes="Tertiary — quieter tape, smaller dollar range, weaker depth.",
    ),
}

ORDERED_BOOKS = ("MES", "MNQ", "MYM")

ETF_SYMBOLS = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq-100",
    "DIA": "Dow Jones",
}

VIX_SYMBOL = "^VIX"
TICK_SYMBOLS = ("^TICK", "^ADD", "^VOLD")  # often unavailable on Yahoo; tried, then skipped

MEGA_CAPS = ("AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA")

# Static US high-impact dates used when the live calendar fetch fails.
# Decision/release times are Eastern. FOMC rate decision 14:00 ET.
STATIC_HIGH_IMPACT_2026: list[dict] = [
    {"date": "2026-08-19", "time": "14:00", "title": "FOMC Minutes", "impact": "medium", "source": "static"},
    {"date": "2026-08-26", "time": "08:30", "title": "GDP (Second Estimate) Q2", "impact": "high", "source": "static"},
    {"date": "2026-09-04", "time": "08:30", "title": "Nonfarm Payrolls (August)", "impact": "high", "source": "static"},
    {"date": "2026-09-11", "time": "08:30", "title": "CPI (August)", "impact": "high", "source": "static"},
    {"date": "2026-09-16", "time": "14:00", "title": "FOMC Rate Decision + SEP / Dot Plot", "impact": "high", "source": "static"},
    {"date": "2026-10-02", "time": "08:30", "title": "Nonfarm Payrolls (September)", "impact": "high", "source": "static"},
    {"date": "2026-10-14", "time": "08:30", "title": "CPI (September)", "impact": "high", "source": "static"},
    {"date": "2026-10-28", "time": "14:00", "title": "FOMC Rate Decision", "impact": "high", "source": "static"},
    {"date": "2026-12-09", "time": "14:00", "title": "FOMC Rate Decision + SEP / Dot Plot", "impact": "high", "source": "static"},
]

# Yahoo fetch windows
INTRADAY_INTERVAL = "5m"
INTRADAY_PERIOD = "7d"
STRUCTURE_INTERVAL = "15m"
STRUCTURE_PERIOD = "15d"
HTF_INTERVAL = "1h"
HTF_PERIOD = "15d"
DAILY_PERIOD = "90d"

CACHE_TTL_SECONDS = 300  # 5 minutes in-memory / Streamlit
DISK_CACHE_MAX_AGE_HOURS = 6

# Volume-at-price proxy
VP_VALUE_AREA = 0.70
VP_HVN_FRAC = 0.70
VP_LVN_FRAC = 0.30

# Kaufman efficiency: low = two-sided / MR-friendly
ER_RANGE_MAX = 0.38
ER_MIXED_MAX = 0.55
ER_TREND_MAX = 0.70

# VIX regime bands for mean-reversion
VIX_GRIND_MAX = 13.0
VIX_FADE_MAX = 22.0
VIX_EVENT_MAX = 28.0
