"""Cooper Precision Reversion Protocol (CPRP) — instrument & risk config.

Aligned to Official Rulebook v1.6 + Quick Reference v1.6
(Multi-Timeframe Hierarchy & Order Flow Clarified — Aug 12, 2026).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROTOCOL_NAME = "Cooper Precision Reversion Protocol"
PROTOCOL_SHORT = "CPRP"
RULEBOOK_VERSION = "1.6"
RULEBOOK_BASE_VERSION = "1.6"  # Official full rulebook edition
RULEBOOK_EDITION_DATE = "2026-08-12"
CREATOR = "Raymon Michael Cooper"

# ONLY this account may see/use the Admin / Founder panel (case-insensitive).
# Display form: ImzCpr@gmail.com  |  normalized login key: imzcpr@gmail.com
ADMIN_EMAILS = ("imzcpr@gmail.com", "ImzCpr@gmail.com")
ADMIN_EMAIL = "imzcpr@gmail.com"
ADMIN_ROLE_LABEL = "ADMIN / FOUNDER"


@dataclass(frozen=True)
class Instrument:
    symbol: str  # Yahoo Finance continuous futures ticker
    short: str  # MES / MNQ / MYM
    name: str
    priority: int  # 1 = primary (preferred on ties)
    point_value: float  # $ per full index point
    tick_size: float
    tick_value: float
    notes: str


# Approved instruments only (Rulebook §2) — Micro futures only
INSTRUMENTS = {
    "MES": Instrument(
        symbol="MES=F",
        short="MES",
        name="Micro E-mini S&P 500",
        priority=1,
        point_value=5.0,
        tick_size=0.25,
        tick_value=1.25,
        notes="Primary — default instrument (§7)",
    ),
    "MNQ": Instrument(
        symbol="MNQ=F",
        short="MNQ",
        name="Micro E-mini Nasdaq-100",
        priority=2,
        point_value=2.0,
        tick_size=0.25,
        tick_value=0.50,
        notes="Secondary — use only when clearly superior",
    ),
    "MYM": Instrument(
        symbol="MYM=F",
        short="MYM",
        name="Micro E-mini Dow",
        priority=3,
        point_value=0.50,
        tick_size=1.0,
        tick_value=0.50,
        notes="Tertiary — lower volatility option",
    ),
}

# Hard risk (Rulebook §5) — non-negotiable −$50 to −$100 per contract
HARD_STOP_MIN_USD = 50.0
HARD_STOP_MAX_USD = 100.0
HARD_STOP_DEFAULT_USD = 75.0

# Structure break pause (Rulebook §5)
STRUCTURE_BREAK_PAUSE_MINUTES = 30

# Static higher timeframe for long-term trend context (Rulebook §2)
# Mandatory context filter only — never generates entries
STATIC_HTF_INTERVAL = "1h"
STATIC_HTF_PERIOD = "10d"
STATIC_HTF_ALT_LABEL = "4-Hour (acceptable alternative)"

# Chart pair hierarchy (Rulebook v1.6 — multi-timeframe hierarchy)
# 60m = bias · 15m/30m = structure · 5m/15m = timing. Only two working pairs.
# No chart lower than 5-minute for structure or execution. 5m+1m fully retired.
CHART_PAIR_DEFAULT = "15m + 5m (default / normal volume · active session)"
CHART_PAIR_SLOW = "30m + 15m (pre-market · low volume · lunch · wide/choppy)"

# Range/channel-reversion scoring thresholds
MIN_SCORE_TO_TRADE = 55.0  # below this → primary CPRP quiet (sit-out or scalping option)
TIE_BREAK_MARGIN = 5.0  # if scores within this, prefer lower priority number (MES → MNQ → MYM)

# CPRP Scalping (secondary · v1.1) — offered only when primary CPRP is quiet
# and market is sideways / accumulation (see Official Scalping Rulebook)
SCALPING_VERSION = "1.1"
SCALPING_MIN_SCORE = 58.0  # minimum environment score to offer scalping option
SCALPING_HARD_STOP_MIN_USD = 30.0
SCALPING_HARD_STOP_MAX_USD = 50.0
SCALPING_TIMEFRAME = "1-minute only"
SCALPING_STYLE = "1-Minute Keltner Mean-Reversion (secondary)"

# Polling / alerts
DEFAULT_REFRESH_SECONDS = 60
ALERT_ON_RECOMMENDATION_CHANGE = True

# Yahoo intraday bars for active structure analysis (max free lookback ~7 days)
INTRADAY_INTERVAL = "5m"
INTRADAY_PERIOD = "5d"

# App branding
APP_NAME = "CPRP Session Micro Selector"
APP_NOTIFY_NAME = "CPRP Micro Selector"

# Local branding / reference assets (relative to project root)
_ASSETS = Path(__file__).resolve().parent / "assets"
BRANDING_DIR = _ASSETS / "branding"
# Prefer looping logo GIFs over MP4 / static stills in the UI
BRANDING_LOGO_VIDEO = _ASSETS / "cprp_logo_video.gif"
BRANDING_LOGO_VIDEO_ALT = _ASSETS / "cprp_logo_video_alt.gif"
BRANDING_LOGO_ICON = _ASSETS / "cprp_logo_icon.jpg"  # favicon / tiny fallback only
BRANDING_LOGO_IMAGE = _ASSETS / "cprp_logo_primary.jpg"  # static fallback
# Sidebar panel media (prefer GIF for seamless loop; MP4 fallback)
SIDEBAR_VIDEO_GIF = _ASSETS / "cprp_sidebar_video.gif"
SIDEBAR_VIDEO = _ASSETS / "cprp_sidebar_video.mp4"
SIDEBAR_VIDEO_BRAND = BRANDING_DIR / "cprp_sidebar_video.mp4"
SIDEBAR_VIDEO_BRAND_GIF = BRANDING_DIR / "cprp_sidebar_video.gif"
# Session Selector header (prefer GIF; MP4 fallback)
SESSION_SELECTOR_VIDEO_GIF = _ASSETS / "cprp_session_selector_video.gif"
SESSION_SELECTOR_VIDEO = _ASSETS / "cprp_session_selector_video.mp4"
SESSION_SELECTOR_VIDEO_BRAND = BRANDING_DIR / "cprp_session_selector_video.mp4"
SESSION_SELECTOR_VIDEO_BRAND_GIF = BRANDING_DIR / "cprp_session_selector_video.gif"
# Also reuse existing variant GIF when session gif missing
SESSION_SELECTOR_VARIANT_GIF = BRANDING_DIR / "cprp_logo_video_variant_2.gif"
# Official CPRP seal (landing page + branding suite) — PNG has transparent background
BRANDING_OFFICIAL_SEAL = _ASSETS / "cprp_official_seal.png"
BRANDING_OFFICIAL_SEAL_JPG = _ASSETS / "cprp_official_seal.jpg"  # original fallback
BRANDING_OFFICIAL_SEAL_ANIM = _ASSETS / "cprp_official_seal_anim.gif"
BRANDING_OFFICIAL_SEAL_BRAND = BRANDING_DIR / "cprp_official_seal.png"
BRANDING_OFFICIAL_SEAL_BRAND_JPG = BRANDING_DIR / "cprp_official_seal.jpg"
BRANDING_OFFICIAL_SEAL_ANIM_BRAND = BRANDING_DIR / "cprp_official_seal_anim.gif"
BRANDING_BANNER = _ASSETS / "cprp_banner_horizontal.jpg"
MEMBER_CHAT_HERO_VIDEO = _ASSETS / "cprp_member_chat_hero.gif"
MEMBER_CHAT_HERO_IMAGE = _ASSETS / "cprp_member_chat_poster.jpg"

# Legacy static session charts folder (optional seed images)
SESSIONS_DIR = _ASSETS / "sessions"
QUICK_REFERENCE_IMAGE = _ASSETS / f"CPRP_Quick_Reference_v{RULEBOOK_VERSION}.jpg"
QUICK_REFERENCE_PDF = _ASSETS / f"CPRP_Quick_Reference_v{RULEBOOK_VERSION}.pdf"
QUICK_REFERENCE_DOWNLOAD_NAME = f"CPRP_Quick_Reference_v{RULEBOOK_VERSION}.jpg"
# v1.6 ships as a full Official Rulebook (no separate Update PDF). Fall back to base.
_update_candidate = _ASSETS / f"CPRP_Rulebook_Update_v{RULEBOOK_VERSION}.pdf"
RULEBOOK_UPDATE_PDF = (
    _update_candidate
    if _update_candidate.is_file()
    else _ASSETS / f"CPRP_Official_Rulebook_v{RULEBOOK_BASE_VERSION}.pdf"
)
RULEBOOK_UPDATE_DOWNLOAD_NAME = (
    f"CPRP_Rulebook_Update_v{RULEBOOK_VERSION}.pdf"
    if _update_candidate.is_file()
    else f"CPRP_Official_Rulebook_v{RULEBOOK_BASE_VERSION}.pdf"
)
RULEBOOK_BASE_PDF = _ASSETS / f"CPRP_Official_Rulebook_v{RULEBOOK_BASE_VERSION}.pdf"
RULEBOOK_BASE_DOWNLOAD_NAME = f"CPRP_Official_Rulebook_v{RULEBOOK_BASE_VERSION}.pdf"

# CPRP Scalping documents (secondary strategy)
SCALPING_RULEBOOK_PDF = _ASSETS / f"CPRP_Scalping_Official_Rulebook_v{SCALPING_VERSION}.pdf"
SCALPING_RULEBOOK_DOWNLOAD_NAME = f"CPRP_Scalping_Official_Rulebook_v{SCALPING_VERSION}.pdf"
SCALPING_QUICK_REFERENCE_PDF = _ASSETS / f"CPRP_Scalping_Quick_Reference_v{SCALPING_VERSION}.pdf"
SCALPING_QUICK_REFERENCE_IMAGE = _ASSETS / f"CPRP_Scalping_Quick_Reference_v{SCALPING_VERSION}.jpg"
SCALPING_QUICK_REFERENCE_DOWNLOAD_NAME = f"CPRP_Scalping_Quick_Reference_v{SCALPING_VERSION}.pdf"
# Scalping brand motion (looping GIF preferred; MP4 fallback)
SCALPING_VIDEO_GIF = _ASSETS / "cprp_scalping_video.gif"
SCALPING_VIDEO_GIF_BRAND = BRANDING_DIR / "cprp_scalping_video.gif"
SCALPING_VIDEO_MP4 = _ASSETS / "cprp_scalping_video.mp4"
SCALPING_VIDEO_MP4_BRAND = BRANDING_DIR / "cprp_scalping_video.mp4"

# CPRP Trading folder — primary source for document + branding sync
CPRP_TRADING_DIR = Path(r"C:\Users\imzcp\OneDrive\Desktop\CPRP Trading")

# Founder / personal page
FOUNDER_NAME = "Raymon Michael Cooper"
FOUNDER_TITLE = "Founder — CPRP Strategies · Micro E-mini Chart Analyst"
FOUNDER_BIO = """
I’m **Raymon Michael Cooper** — father, former logistics driver, and the person who built **CPRP Strategies** from the ground up.

For years my days were measured by reliability: show up, do the work, protect what matters. At home I’m a dad; I share the house with a couple of cats who never care about the open. Those same habits — consistency, accountability, no drama — are what I brought into the markets.

I studied Data Analytics at Southern New Hampshire University because I wanted real analytical muscle. Classrooms never fit how I learn. Charts did. What started as curiosity about patterns became a serious craft: structure, probability, and the discipline to wait.

That craft became the **Cooper Precision Reversion Protocol (CPRP)** and, around it, **CPRP Strategies** — a Micro E-mini futures day-trading desk that treats chart analysis as a profession. Multiple protocols for different market conditions. Backtested. Stress-tested in live accounts. Bound to written rulebooks, not vibes.

I didn’t buy a system off a shelf. I wrote the rules, broke them, rewrote them, and kept only what survived the tape. I’m still building — deliberately, with structure — and I’m sharing the work with traders who want the same standard.
""".strip()

FOUNDER_TAGLINE = (
    "Structure over noise. Rules over ego. Micros only — built in the open."
)

# Legal / community disclosure (landing page + key member pages)
DISCLOSURE_TITLE = "Acknowledgement & Disclosure"
DISCLOSURE_BODY = """
**CPRP Strategies** and the Cooper Precision Reversion Protocol (CPRP) — including rulebooks, tools, journals, and community spaces — were built for my own work as an independent day trader. I’m sharing them freely with people who find them useful.

This is **not** personalized financial, investment, or trading advice. You own your decisions, your risk, and your results. Futures trading can move against you quickly and is not suitable for everyone. Past performance does not guarantee future results.

You’re joining a free, informal circle of independent traders — not a brokerage, signal service, or managed account. Participation is voluntary. Nothing here obligates you to take a trade.

By using CPRP materials or joining the conversation, you accept full responsibility for your own outcomes.

— **Raymon Michael Cooper**  
Founder, CPRP Strategies
""".strip()

DISCLOSURE_THIRD_PARTY_TITLE = "Third-Party Tools, Free Sources & No Partnerships"
DISCLOSURE_THIRD_PARTY_BODY = """
**CPRP Strategies** stands alone. We are not owned by, sponsored by, or partnered with any broker, data vendor, news network, calendar site, or platform — even when we link or embed their free tools for convenience.

Those services belong to their owners. We don’t control their accuracy, uptime, ads, or terms.

- Links and embeds are **convenience only** — not endorsements.  
- No paid partnership exists unless we say so in writing.  
- You use third-party sites under **their** rules.  
- Everything here is for personal education and situational awareness — **not** personalized advice.

If an embed won’t load, use the open-in-browser link. That’s normal for some providers.

— **Raymon Michael Cooper**  
Founder, CPRP Strategies
""".strip()
