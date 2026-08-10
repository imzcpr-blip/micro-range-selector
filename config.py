"""Cooper Precision Reversion Protocol (CPRP) — instrument & risk config.

Aligned to Official Rulebook v1.5 (Final) + Quick Reference v1.5
(Chart Pair Hierarchy Locked — Aug 10, 2026).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROTOCOL_NAME = "Cooper Precision Reversion Protocol"
PROTOCOL_SHORT = "CPRP"
RULEBOOK_VERSION = "1.5"
RULEBOOK_BASE_VERSION = "1.5"  # Official full rulebook edition
RULEBOOK_EDITION_DATE = "2026-08-10"
CREATOR = "Raymon Michael Cooper"

# ONLY this account may see/use the Admin / Founder panel (case-insensitive).
ADMIN_EMAILS = ("imzcpr@gmail.com",)
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
INSTRUMENTS: dict[str, Instrument] = {
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

# Chart pair hierarchy (Rulebook Update v1.5 final)
# Only two working pairs. No chart lower than 5-minute for structure or execution.
CHART_PAIR_DEFAULT = "15m + 5m (default / most sessions)"
CHART_PAIR_SLOW = "30m + 15m (larger / slower / lower volume)"

# Range/channel-reversion scoring thresholds
MIN_SCORE_TO_TRADE = 55.0  # below this → "SIT OUT"
TIE_BREAK_MARGIN = 5.0  # if scores within this, prefer lower priority number (MES → MNQ → MYM)

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
# Official CPRP seal (landing page + branding suite)
BRANDING_OFFICIAL_SEAL = _ASSETS / "cprp_official_seal.jpg"
BRANDING_OFFICIAL_SEAL_ANIM = _ASSETS / "cprp_official_seal_anim.gif"
BRANDING_OFFICIAL_SEAL_BRAND = BRANDING_DIR / "cprp_official_seal.jpg"
BRANDING_OFFICIAL_SEAL_ANIM_BRAND = BRANDING_DIR / "cprp_official_seal_anim.gif"
BRANDING_BANNER = _ASSETS / "cprp_banner_horizontal.jpg"
MEMBER_CHAT_HERO_VIDEO = _ASSETS / "cprp_member_chat_hero.gif"
MEMBER_CHAT_HERO_IMAGE = _ASSETS / "cprp_member_chat_poster.jpg"

# Legacy static session charts folder (optional seed images)
SESSIONS_DIR = _ASSETS / "sessions"
QUICK_REFERENCE_IMAGE = _ASSETS / f"CPRP_Quick_Reference_v{RULEBOOK_VERSION}.jpg"
QUICK_REFERENCE_PDF = _ASSETS / f"CPRP_Quick_Reference_v{RULEBOOK_VERSION}.pdf"
QUICK_REFERENCE_DOWNLOAD_NAME = f"CPRP_Quick_Reference_v{RULEBOOK_VERSION}.jpg"
RULEBOOK_UPDATE_PDF = _ASSETS / f"CPRP_Rulebook_Update_v{RULEBOOK_VERSION}.pdf"
RULEBOOK_UPDATE_DOWNLOAD_NAME = f"CPRP_Rulebook_Update_v{RULEBOOK_VERSION}.pdf"
RULEBOOK_BASE_PDF = _ASSETS / f"CPRP_Official_Rulebook_v{RULEBOOK_BASE_VERSION}.pdf"
RULEBOOK_BASE_DOWNLOAD_NAME = f"CPRP_Official_Rulebook_v{RULEBOOK_BASE_VERSION}.pdf"

# CPRP Trading folder — primary source for document + branding sync
CPRP_TRADING_DIR = Path(r"C:\Users\imzcp\OneDrive\Desktop\CPRP Trading")

# Founder / personal page
FOUNDER_NAME = "Raymon Michael Cooper"
FOUNDER_TITLE = "Founder — Cooper Precision Reversion Protocol (CPRP)"
FOUNDER_BIO = """
I’m **Raymon Michael Cooper**. For years I worked as a Delivery/Logistics Driver, showing up consistently and taking care of what needed to be done. At home I’m a father to my son and share the house with a couple of cats who’ve been part of the family for a long time. Those responsibilities have always grounded me — they also pushed me to look for a better long-term path.

I’ve always been drawn to research, patterns, and data. I enrolled at Southern New Hampshire University for Data Analytics because I wanted to build real analytical skills. Classroom-based learning didn’t fit how I process information, so I stepped away and started applying that same curiosity directly to the markets. What began as an interest in data quickly turned into a deep focus on chart structure, price behavior, and probability.

That process led me to develop my own system — the **Cooper Precision Reversion Protocol (CPRP)**. It’s a rules-based approach to Micro futures that centers on confirmed range and channel structure, multi-timeframe confirmation, strict risk limits, and disciplined execution. I didn’t copy a method. I built one through observation, testing, and holding myself accountable to clear standards.

This transition isn’t about escaping work. It’s about taking the same reliability and consistency I brought to the road and applying them to a craft I can own and improve every day. I’m still early in making trading my primary path, but I’m fully committed. Between the responsibility of being a father, the quiet company of the cats, and the daily work of refining my process, I’m betting on myself — deliberately and with structure.
""".strip()

FOUNDER_TAGLINE = (
    "Father, researcher, and builder of CPRP — structure, data, and deliberate discipline."
)

# Legal / community disclosure (landing page + key member pages)
DISCLOSURE_TITLE = "Acknowledgement & Disclosure"
DISCLOSURE_BODY = """
The Cooper Precision Reversion Protocol (CPRP), including all related tools, rulebooks, guidelines, applications, and educational materials, has been developed solely for my personal use as an independent day trader. I am freely sharing these resources with others who may find them useful.

Nothing contained in this protocol, its tools, or any associated community discussions constitutes personalized financial, investment, or trading advice. Every trader is solely responsible for their own decisions, risk management, and results. Futures trading involves substantial risk of loss and is not suitable for all individuals. Past performance is not indicative of future results.

This is a free, informal community of independent day traders who choose to share ideas, observations, and understanding with one another. Participation is voluntary. No one is obligated to follow any strategy, rule, or suggestion shared here.

By accessing or using any CPRP materials or participating in related discussions, you acknowledge that you do so at your own risk and that I accept no liability for any trading decisions, losses, or outcomes that may result.

— **Raymon Michael Cooper**  
Founder, CPRP Strategies
""".strip()

DISCLOSURE_THIRD_PARTY_TITLE = "Third-Party Tools, Free Sources & No Partnerships"
DISCLOSURE_THIRD_PARTY_BODY = """
CPRP Strategies and this Session Micro Range Selector Tool are **independent**. They are not owned by, sponsored by, endorsed by, or partnered with any broker, data vendor, news network, calendar provider, social platform, or other commercial service.

Some features link to or embed **free third-party resources** for convenience only (for example: economic calendars, live news streams, or market data). Those sites and streams are owned and controlled by their respective owners. I do **not** control their content, accuracy, availability, advertising, or terms of use.

- **No partnership or affiliation** is implied by linking to or embedding free public tools.
- **No payment or sponsorship** relationship exists with those providers unless explicitly stated in writing.
- You use third-party sites **at your own risk** and subject to **their** terms, privacy policies, and disclaimers.
- CPRP materials and third-party information are for **personal educational / situational awareness** only and are **not** personalized financial advice.

If a third-party embed does not load (blocked by the provider or your browser), use the direct link they provide.

— **Raymon Michael Cooper**  
Founder, CPRP Strategies
""".strip()
