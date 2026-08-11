"""
Economic Calendar panel for CPRP members.

Primary source framing: Bloomberg (Economic Calendar link + Live news desk).
Bloomberg does not publish a free embeddable calendar widget, so the in-app
event table uses Investing.com when a structured calendar is needed inside
the window. Forex Factory remains an external link only (blocks iframes).

No partnership with Bloomberg, YouTube, Investing.com, or Forex Factory.
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from disclosure import render_disclosure, render_third_party_disclosure
from live_news import render_bloomberg_player
from wallstreet_ui import candle_expander, desk_section, link_label, page_hero

# Bloomberg markets calendar + live desk (primary CPRP framing)
BLOOMBERG_CALENDAR_URL = "https://www.bloomberg.com/markets/economic-calendar"
BLOOMBERG_MARKETS_URL = "https://www.bloomberg.com/markets"
BLOOMBERG_HOME_URL = "https://www.bloomberg.com"

FOREX_FACTORY_CALENDAR_URL = "https://www.forexfactory.com/calendar"
INVESTING_CALENDAR_URL = "https://www.investing.com/economic-calendar/"


def _investing_calendar_iframe(*, height: int = 720) -> str:
    """Structured calendar table embed (allows framing when available)."""
    src = (
        "https://sslecal2.investing.com?"
        "columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous"
        "&features=datepicker,timezone,timeselector,filters"
        "&countries=5,4,72,17,37,6,25,32,10,35,26,12"
        "&calType=week"
        "&timeZone=8"
        "&lang=1"
    )
    return f"""
<div style="width:100%;border:2px solid rgba(201,168,76,0.35);border-radius:2px;
            overflow:hidden;background:#060a0e;
            box-shadow:0 0 0 1px rgba(0,0,0,0.6), 0 8px 28px rgba(0,0,0,0.45);">
  <div style="display:flex;justify-content:space-between;align-items:center;
              padding:0.4rem 0.75rem;background:linear-gradient(180deg,#1a160e,#0a0c10);
              border-bottom:1px solid rgba(201,168,76,0.35);
              font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.1em;
              color:#C9A84C;text-transform:uppercase;">
    <span>Event Table · In-App Grid</span>
    <span style="color:#8a8478;">Third-party structured feed</span>
  </div>
  <iframe
    src="{src}"
    title="Economic Calendar event table"
    width="100%"
    height="{height}"
    style="border:0;background:#060a0e;"
    loading="lazy"
    referrerpolicy="no-referrer-when-downgrade"
  ></iframe>
</div>
<p style="font-size:12px;color:#8a8478;margin:8px 0 0 0;font-family:IBM Plex Mono,monospace;">
  Structured table embed for in-app viewing. Content belongs to its publisher.
  CPRP is independent and not partnered with this site. Prefer Bloomberg for
  primary calendar / live desk coverage.
</p>
"""


def _bloomberg_calendar_try_iframe(*, height: int = 720) -> str:
    """
    Attempt to frame Bloomberg Economic Calendar.
    Often blocked by X-Frame-Options — UI always offers Open Bloomberg buttons.
    """
    return f"""
<div style="width:100%;border:2px solid rgba(201,168,76,0.4);border-radius:2px;
            overflow:hidden;background:#060a0e;
            box-shadow:0 0 0 1px rgba(0,0,0,0.6), 0 8px 28px rgba(0,0,0,0.45);">
  <div style="display:flex;justify-content:space-between;align-items:center;
              padding:0.4rem 0.75rem;background:linear-gradient(180deg,#1a160e,#0a0c10);
              border-bottom:1px solid rgba(201,168,76,0.4);
              font-family:Cinzel,serif;font-size:11px;letter-spacing:0.14em;
              color:#C9A84C;text-transform:uppercase;">
    <span>Bloomberg · Economic Calendar</span>
    <span style="color:#7dcea0;font-family:IBM Plex Mono,monospace;">● DESK</span>
  </div>
  <iframe
    src="{BLOOMBERG_CALENDAR_URL}"
    title="Bloomberg Economic Calendar"
    width="100%"
    height="{height}"
    style="border:0;background:#060a0e;"
    loading="lazy"
    referrerpolicy="no-referrer-when-downgrade"
  ></iframe>
</div>
<p style="font-size:12px;color:#8a8478;margin:8px 0 0 0;font-family:IBM Plex Mono,monospace;">
  If this frame stays blank, Bloomberg is blocking embeds in your browser —
  use <strong>Open Bloomberg Economic Calendar</strong> above (new tab).
</p>
"""


def render_economic_calendar_panel() -> None:
    """Dedicated Economic Calendar page — Bloomberg primary framing."""
    page_hero(
        "Economic Calendar",
        "High-impact news risk filter · Bloomberg desk framing · live third-party sources",
        side="bear",
        desk_tag="EVENT RISK DESK · BLOOMBERG FRAMED",
    )

    with candle_expander("What this is & CPRP use", side="bull", expanded=True, kind="up"):
        st.markdown(
            """
An **economic calendar** lists scheduled macroeconomic releases and events
(e.g. CPI, employment, FOMC, GDP, central-bank speeches) with expected impact levels.

This desk is framed around **Bloomberg**:
- **Bloomberg Economic Calendar** — official markets calendar (open in a new tab; full site).
- **Bloomberg Business News Live** — in-app YouTube live desk for breaking coverage around releases.

**Bloomberg does not offer a free embeddable calendar widget**, so if you need a
**structured event table inside this window**, use the optional in-app table source below.
**Forex Factory blocks iframe embedding** — open it externally if you prefer that site.

**CPRP Strategies is not affiliated with, partnered with, or endorsed by** Bloomberg,
YouTube, Forex Factory, Investing.com, or any other news / calendar provider.

### Recommended use with CPRP

For the **Cooper Precision Reversion Protocol**, the calendar is best used as a
**risk / context filter**, not as a trade signal:

1. **Know when high-impact news hits** — volatility and false structure breaks are common around major releases.  
2. **Protect the hard risk rule** — avoid forcing boundary fades around red-folder events unless your plan allows it.  
3. **Structure-break awareness** — after news, ranges often expand; respect the **30-minute pause**.  
4. **Session selection** — prefer clearer tape *after* major risk events when structure re-forms.  
5. **Journal context** — note which events were live when you log wins and losses.

**Not recommended as:** an entry trigger, a substitute for confirmed S/R, or a reason to ignore the hard stop.
"""
        )

    render_disclosure(expanded=False)
    render_third_party_disclosure(expanded=False)

    # ── Bloomberg primary actions ─────────────────────────────────────────
    desk_section("Bloomberg desk (primary)", side="bull")
    st.caption(
        "Primary calendar and live desk for CPRP event-risk context. "
        "Open Bloomberg for the full Economic Calendar; stream Live in-app for coverage."
    )

    b1, b2, b3 = st.columns(3)
    with b1:
        st.link_button(
            link_label("Open Bloomberg Economic Calendar"),
            BLOOMBERG_CALENDAR_URL,
            use_container_width=True,
            type="primary",
        )
    with b2:
        st.link_button(
            link_label("Open Bloomberg Markets"),
            BLOOMBERG_MARKETS_URL,
            use_container_width=True,
        )
    with b3:
        st.link_button(
            link_label("Open Bloomberg.com"),
            BLOOMBERG_HOME_URL,
            use_container_width=True,
        )

    desk_section("Bloomberg Business News Live", side="bear")
    st.caption(
        "Live desk feed while high-impact releases hit. Toggle off to stop audio completely."
    )
    render_bloomberg_player(
        height=420,
        key_prefix="econ_bb",
        compact=True,
        title="Bloomberg Business News Live · Event Desk",
        default_on=False,
    )

    # ── In-app calendar view ──────────────────────────────────────────────
    desk_section("Live calendar (in-app)", side="bear")

    source = st.radio(
        "In-app view",
        [
            "Bloomberg Economic Calendar (try embed)",
            "Event table grid (structured · in-window)",
        ],
        horizontal=True,
        key="econ_cal_source",
        help=(
            "Bloomberg is primary. Their site often blocks iframes — use the Open button "
            "if the embed is blank. Event table is a free third-party structured grid only."
        ),
    )

    c1, c2 = st.columns(2)
    with c1:
        st.link_button(
            link_label("Open Forex Factory Calendar"),
            FOREX_FACTORY_CALENDAR_URL,
            use_container_width=True,
        )
    with c2:
        st.link_button(
            link_label("Open Investing.com Calendar"),
            INVESTING_CALENDAR_URL,
            use_container_width=True,
        )

    height = 720
    if source.startswith("Bloomberg"):
        st.caption(
            "Attempting **Bloomberg Economic Calendar** inside the desk frame. "
            "If blank / refused, use **Open Bloomberg Economic Calendar** (primary)."
        )
        components.html(
            _bloomberg_calendar_try_iframe(height=height),
            height=height + 70,
            scrolling=True,
        )
        st.info(
            "**Tip:** Bloomberg commonly blocks embedding. The **Open Bloomberg Economic Calendar** "
            "button above is the reliable full calendar. Keep **Bloomberg Live** on for desk coverage."
        )
    else:
        st.caption(
            "Structured **event table** for in-window scanning (third-party free embed). "
            "Use Bloomberg links above for primary calendar / live desk."
        )
        components.html(
            _investing_calendar_iframe(height=height),
            height=height + 70,
            scrolling=True,
        )

    st.caption(
        "Forex Factory deliberately blocks embedding (`refused to connect`). "
        "Use its external button if you want that site in a new browser tab."
    )

    with candle_expander("Quick CPRP checklist around news", side="bear", expanded=False, kind="down"):
        st.markdown(
            f"""
| Step | Action |
|------|--------|
| Before high-impact release | Reduce new risk; avoid mid-structure trades |
| During release | Expect wicks / breaks; do not chase lower-TF noise |
| After release | Re-confirm structure on **15m+5m** (or **30m+15m**); apply full confluence |
| Structure breaks | Flatten, pause 30 minutes or wait for new clear range |

**Primary:** [Bloomberg Economic Calendar]({BLOOMBERG_CALENDAR_URL}) · [Bloomberg Markets]({BLOOMBERG_MARKETS_URL})  
**Live desk:** Bloomberg Business News Live (in-app above)  
**External alt:** [Forex Factory]({FOREX_FACTORY_CALENDAR_URL}) · [Investing.com]({INVESTING_CALENDAR_URL})
"""
        )


def render_economic_calendar_compact(*, key_prefix: str = "econ") -> None:
    """Optional compact expander for other pages — Bloomberg primary."""
    with candle_expander(
        "Economic Calendar — news risk filter",
        side="bear",
        expanded=False,
        kind="link",
    ):
        st.markdown(
            "Use **Bloomberg** calendar / live desk to **avoid or respect high-impact news** "
            "around CPRP range fades. Not a trade signal. Free third-party sources — **no partnership**."
        )
        st.link_button(
            link_label("Open Bloomberg Economic Calendar"),
            BLOOMBERG_CALENDAR_URL,
            use_container_width=True,
            key=f"{key_prefix}_bb_cal_link",
            type="primary",
        )
        st.link_button(
            link_label("Open Forex Factory Calendar"),
            FOREX_FACTORY_CALENDAR_URL,
            use_container_width=True,
            key=f"{key_prefix}_ff_link",
        )
        render_third_party_disclosure(expanded=False)
