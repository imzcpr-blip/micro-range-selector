"""
Economic Calendar panel for CPRP members.

Forex Factory blocks iframe embeds (X-Frame-Options), so the in-app window uses
TradingView’s free embeddable Economic Calendar widget (dark theme). Forex Factory
remains available as a direct external link only.

No partnership with TradingView, Investing.com, or Forex Factory.
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from disclosure import render_disclosure, render_third_party_disclosure
from wallstreet_ui import candle_expander, desk_section, link_label, page_hero

FOREX_FACTORY_CALENDAR_URL = "https://www.forexfactory.com/calendar"
INVESTING_CALENDAR_URL = "https://www.investing.com/economic-calendar/"
TRADINGVIEW_CALENDAR_URL = "https://www.tradingview.com/economic-calendar/"

# Official TradingView Economic Calendar widget (designed for embedding; dark theme)
def _tradingview_calendar_html(*, height: int = 720) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    html, body {{
      margin: 0; padding: 0;
      background: #0A1628;
      height: 100%;
      overflow: hidden;
      font-family: 'IBM Plex Sans', system-ui, sans-serif;
    }}
    .tradingview-widget-container {{
      width: 100%;
      height: {height}px;
    }}
    .tradingview-widget-container__widget {{
      width: 100%;
      height: {height - 28}px;
    }}
    .tv-footer {{
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      padding: 0 10px;
      font-size: 11px;
      color: #8B9BB4;
      background: #0A1628;
      border-top: 1px solid rgba(201,168,76,0.18);
    }}
    .tv-footer a {{ color: #C9A84C; text-decoration: none; }}
  </style>
</head>
<body>
  <div class="tradingview-widget-container">
    <div class="tradingview-widget-container__widget"></div>
    <div class="tv-footer">
      <a href="{TRADINGVIEW_CALENDAR_URL}" target="_blank" rel="noopener noreferrer">
        Economic Calendar · TradingView
      </a>
    </div>
    <script type="text/javascript"
      src="https://s3.tradingview.com/external-embedding/embed-widget-events.js"
      async>
    {{
      "colorTheme": "dark",
      "isTransparent": false,
      "width": "100%",
      "height": "{height - 28}",
      "locale": "en",
      "importanceFilter": "-1,0,1",
      "countryFilter": "us,eu,gb,jp,cn,ca,au,nz,ch"
    }}
    </script>
  </div>
</body>
</html>
"""


def _investing_calendar_iframe(*, height: int = 720) -> str:
    """Fallback: Investing.com sslecal2 embed (allows framing when available)."""
    # columns + importance + major economies; dark-ish chrome via outer wrapper
    src = (
        "https://sslecal2.investing.com?"
        "columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous"
        "&features=datepicker,timezone,timeselector,filters"
        "&countries=5,4,72,17,37,6,25,32,10,35,26,12"  # US,EU,UK,JP,CN,AU,CA,NZ,CH,DE,FR,IT-ish set
        "&calType=week"
        "&timeZone=8"
        "&lang=1"
    )
    return f"""
<div style="width:100%;border:1px solid rgba(201,168,76,0.25);border-radius:10px;
            overflow:hidden;background:#0A1628;">
  <iframe
    src="{src}"
    title="Investing.com Economic Calendar"
    width="100%"
    height="{height}"
    style="border:0;background:#0A1628;"
    loading="lazy"
    referrerpolicy="no-referrer-when-downgrade"
  ></iframe>
</div>
<p style="font-size:12px;color:#8B9BB4;margin:8px 0 0 0;">
  Free third-party embed. Content belongs to Investing.com / its owners.
  CPRP is independent and not partnered with this site.
</p>
"""


def render_economic_calendar_panel() -> None:
    """Dedicated Economic Calendar page with in-app embed that actually loads."""
    page_hero(
        "Economic Calendar",
        "High-impact news risk filter · live in-app calendar · free third-party sources",
        side="bear",
        desk_tag="EVENT RISK DESK · THIRD-PARTY",
    )

    with candle_expander("What this is & CPRP use", side="bull", expanded=True, kind="up"):
        st.markdown(
            """
An **economic calendar** lists scheduled macroeconomic releases and events
(e.g. CPI, employment, FOMC, GDP, central-bank speeches) with expected impact levels.

The calendar **inside this window** uses **TradingView’s free Economic Calendar widget**
(designed for embedding). **Forex Factory blocks iframe embedding**, so it cannot be
shown inside this app — open it with the external link below if you prefer that site.

**CPRP Strategies is not affiliated with, partnered with, or endorsed by** TradingView,
Forex Factory, Investing.com, or any other calendar provider.

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

    desk_section("Live calendar (in-app)", side="bear")

    source = st.radio(
        "Calendar source",
        [
            "TradingView (recommended · loads in window)",
            "Investing.com widget (fallback)",
        ],
        horizontal=True,
        key="econ_cal_source",
        help="Forex Factory cannot be embedded (site refuses connections in iframes).",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.link_button(
            link_label("Open TradingView Calendar"),
            TRADINGVIEW_CALENDAR_URL,
            use_container_width=True,
        )
    with c2:
        st.link_button(
            link_label("Open Investing.com Calendar"),
            INVESTING_CALENDAR_URL,
            use_container_width=True,
        )
    with c3:
        st.link_button(
            link_label("Open Forex Factory Calendar"),
            FOREX_FACTORY_CALENDAR_URL,
            use_container_width=True,
        )

    height = 720
    if source.startswith("TradingView"):
        st.caption(
            "In-app **TradingView Economic Calendar** (dark theme). "
            "Filter by importance and country inside the widget."
        )
        components.html(_tradingview_calendar_html(height=height), height=height + 20, scrolling=False)
    else:
        st.caption(
            "Fallback **Investing.com** calendar embed. "
            "If this still fails to load in your browser, use **Open Investing.com Calendar** above."
        )
        components.html(_investing_calendar_iframe(height=height), height=height + 50, scrolling=True)

    st.info(
        "**Note:** Forex Factory deliberately blocks embedding (`refused to connect`). "
        "That is why this tab no longer iframes forexfactory.com. Use the Forex Factory button "
        "if you want that site in a new browser tab."
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

**In-app source:** [TradingView Economic Calendar]({TRADINGVIEW_CALENDAR_URL}) (free embed).  
**External:** [Forex Factory]({FOREX_FACTORY_CALENDAR_URL}) · [Investing.com]({INVESTING_CALENDAR_URL})
"""
        )


def render_economic_calendar_compact(*, key_prefix: str = "econ") -> None:
    """Optional compact expander for other pages."""
    with candle_expander(
        "Economic Calendar — news risk filter",
        side="bear",
        expanded=False,
        kind="link",
    ):
        st.markdown(
            "Use the calendar to **avoid or respect high-impact news** around CPRP range fades. "
            "Not a trade signal. Free third-party sources — **no partnership**."
        )
        st.link_button(
            link_label("Open TradingView Calendar"),
            TRADINGVIEW_CALENDAR_URL,
            use_container_width=True,
            key=f"{key_prefix}_tv_link",
        )
        st.link_button(
            link_label("Open Forex Factory Calendar"),
            FOREX_FACTORY_CALENDAR_URL,
            use_container_width=True,
            key=f"{key_prefix}_ff_link",
        )
        render_third_party_disclosure(expanded=False)
