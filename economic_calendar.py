"""
Economic Calendar panel for CPRP members.

Primary in-app view: TradingView Economic Calendar widget, pre-filtered to
**high-importance** events that matter most for US Micro equity-index futures
(MES / MNQ / MYM) — mainly US red-folder releases (FOMC, CPI, NFP, etc.).

Bloomberg remains available as live desk + external calendar links.
Forex Factory is external only (blocks iframes).

No partnership with TradingView, Bloomberg, YouTube, Investing.com, or Forex Factory.
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from disclosure import render_disclosure, render_third_party_disclosure
from live_news import render_bloomberg_player
from wallstreet_ui import candle_expander, desk_section, link_label, page_hero

TRADINGVIEW_CALENDAR_URL = "https://www.tradingview.com/economic-calendar/"
BLOOMBERG_CALENDAR_URL = "https://www.bloomberg.com/markets/economic-calendar"
BLOOMBERG_MARKETS_URL = "https://www.bloomberg.com/markets"
FOREX_FACTORY_CALENDAR_URL = "https://www.forexfactory.com/calendar"
INVESTING_CALENDAR_URL = "https://www.investing.com/economic-calendar/"

# Tall enough that TV widget chrome + week list + filters fit without a cramped box
TV_CALENDAR_HEIGHT = 920

# High-importance only (TradingView: -1 low · 0 medium · 1 high)
# US-focused: Micro E-minis (MES/MNQ/MYM) react hardest to US macro / Fed.
# Optional G7 majors that still move US equity futures risk on big prints.
TV_IMPORTANCE_HIGH = "1"
TV_COUNTRIES_MICROS = "us"  # primary
TV_COUNTRIES_MICROS_PLUS = "us,eu,gb,jp,ca"  # high-impact global that can move ES/NQ/YM


def _tradingview_calendar_html(
    *,
    height: int = TV_CALENDAR_HEIGHT,
    importance: str = TV_IMPORTANCE_HIGH,
    countries: str = TV_COUNTRIES_MICROS,
) -> str:
    """
    TradingView Economic Calendar embed — dark desk theme.

    Filtered for Micro futures risk:
      • importanceFilter = high only (\"1\")
      • countryFilter    = US (or US + major G7 when expanded)
    Large fixed height so toolbar, filters, and event list all fit in-frame.
    """
    chart_h = max(480, int(height) - 32)
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    html, body {{
      margin: 0; padding: 0;
      background: #060a0e;
      height: 100%;
      overflow: hidden;
      font-family: 'IBM Plex Mono', 'IBM Plex Sans', system-ui, sans-serif;
    }}
    .tv-frame {{
      width: 100%;
      height: {height}px;
      border: 2px solid rgba(201,168,76,0.4);
      box-sizing: border-box;
      background: #060a0e;
      box-shadow: 0 0 0 1px rgba(0,0,0,0.6), 0 8px 28px rgba(0,0,0,0.45);
      display: flex;
      flex-direction: column;
    }}
    .tv-head {{
      flex: 0 0 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 12px;
      background: linear-gradient(180deg, #1a160e, #0a0c10);
      border-bottom: 1px solid rgba(201,168,76,0.4);
      font-size: 10px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #C9A84C;
    }}
    .tv-head .live {{
      color: #7dcea0;
      font-family: 'IBM Plex Mono', monospace;
    }}
    .tv-head a {{ color: #C9A84C; text-decoration: none; }}
    .tradingview-widget-container {{
      flex: 1 1 auto;
      width: 100%;
      height: {chart_h}px;
      min-height: {chart_h}px;
    }}
    .tradingview-widget-container__widget {{
      width: 100% !important;
      height: {chart_h}px !important;
      min-height: {chart_h}px !important;
    }}
  </style>
</head>
<body>
  <div class="tv-frame">
    <div class="tv-head">
      <span>TradingView · High-Impact · Micro Futures Filter</span>
      <span class="live">
        ● HIGH ONLY · {countries.upper().replace(",", " · ")}
        &nbsp;·&nbsp;
        <a href="{TRADINGVIEW_CALENDAR_URL}" target="_blank" rel="noopener noreferrer">Full site</a>
      </span>
    </div>
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript"
        src="https://s3.tradingview.com/external-embedding/embed-widget-events.js"
        async>
      {{
        "colorTheme": "dark",
        "isTransparent": false,
        "width": "100%",
        "height": "{chart_h}",
        "locale": "en",
        "importanceFilter": "{importance}",
        "countryFilter": "{countries}"
      }}
      </script>
    </div>
  </div>
</body>
</html>
"""


def _investing_calendar_iframe(*, height: int = 720) -> str:
    """Fallback structured calendar table (high importance via site filters when available)."""
    src = (
        "https://sslecal2.investing.com?"
        "columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous"
        "&features=datepicker,timezone,timeselector,filters"
        "&countries=5"  # United States
        "&importance=3"  # high
        "&calType=week"
        "&timeZone=8"
        "&lang=1"
    )
    return f"""
<div style="width:100%;border:2px solid rgba(201,168,76,0.35);border-radius:2px;
            overflow:hidden;background:#060a0e;">
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
"""


def render_economic_calendar_panel() -> None:
    """Dedicated Economic Calendar — TradingView high-impact Micro filter + Bloomberg desk."""
    page_hero(
        "Economic Calendar",
        "High-impact news risk filter · TradingView embed (Micro-focused) · Bloomberg live desk",
        side="bear",
        desk_tag="EVENT RISK DESK · HIGH IMPACT · MICROS",
    )

    with candle_expander("What this is & CPRP use", side="bull", expanded=False, kind="up"):
        st.markdown(
            """
An **economic calendar** lists scheduled macroeconomic releases and events
(e.g. CPI, employment, FOMC, GDP) with expected impact levels.

### In-app TradingView filter (Micro E-minis)

The embedded calendar is pre-set for **highest-priority** events that matter most
to **MES / MNQ / MYM**:

| Filter | Setting | Why |
|--------|---------|-----|
| **Importance** | **High only** | Red-folder / market-moving prints |
| **Countries** | **US** (default) or **US + major G7** | US equity-index micros react hardest to US macro & Fed |
| **Size** | Tall full-width embed | Toolbar, filters, and event list fit in one view |

Typical watched events: **FOMC / Fed speakers · CPI / PPI · NFP / unemployment · GDP · Retail sales · PCE**.

**Bloomberg** remains available for live desk coverage and their full economic calendar in a new tab.

**CPRP Strategies is not affiliated with, partnered with, or endorsed by** TradingView,
Bloomberg, YouTube, Forex Factory, Investing.com, or any other provider.

### Recommended use with CPRP

1. **Know when high-impact news hits** — volatility and false structure breaks are common.  
2. **Protect the hard risk rule** — avoid forcing boundary fades around red-folder events unless your plan allows it.  
3. **Structure-break awareness** — after news, ranges often expand; respect the **30-minute pause**.  
4. **Session selection** — prefer clearer tape *after* major risk events when structure re-forms.  
5. **Journal context** — note which events were live when you log wins and losses.

**Not recommended as:** an entry trigger, a substitute for confirmed S/R, or a reason to ignore the hard stop.
"""
        )

    render_disclosure(expanded=False)
    render_third_party_disclosure(expanded=False)

    # ── Primary: TradingView high-impact Micro calendar ───────────────────
    desk_section("TradingView · High-Impact Calendar (Micro filter)", side="bull")

    f1, f2 = st.columns([2, 1])
    with f1:
        scope = st.radio(
            "Country scope (high importance only)",
            [
                "US only (MES · MNQ · MYM primary)",
                "US + major G7 (EU · UK · JP · CA)",
            ],
            horizontal=True,
            key="econ_tv_scope",
            help=(
                "US-only is the tightest Micro futures filter. "
                "US+G7 adds ECB / BOE / BOJ / BoC high-impact prints that can still move ES/NQ/YM."
            ),
        )
    with f2:
        height = st.select_slider(
            "Embed height",
            options=[780, 860, 920, 1000, 1100],
            value=TV_CALENDAR_HEIGHT,
            key="econ_tv_height",
            help="Taller = more of the calendar list visible without inner scrolling.",
        )

    countries = (
        TV_COUNTRIES_MICROS
        if scope.startswith("US only")
        else TV_COUNTRIES_MICROS_PLUS
    )

    st.caption(
        f"**Filter locked to HIGH importance** · countries: **{countries.upper().replace(',', ' · ')}** · "
        f"height **{height}px** so the widget chrome + event list fit in the embed.  "
        "You can still adjust day/week inside the TradingView widget."
    )

    l1, l2, l3, l4 = st.columns(4)
    with l1:
        st.link_button(
            link_label("Open TradingView Calendar"),
            TRADINGVIEW_CALENDAR_URL,
            use_container_width=True,
            type="primary",
        )
    with l2:
        st.link_button(
            link_label("Open Bloomberg Calendar"),
            BLOOMBERG_CALENDAR_URL,
            use_container_width=True,
        )
    with l3:
        st.link_button(
            link_label("Open Forex Factory"),
            FOREX_FACTORY_CALENDAR_URL,
            use_container_width=True,
        )
    with l4:
        st.link_button(
            link_label("Open Investing.com"),
            INVESTING_CALENDAR_URL,
            use_container_width=True,
        )

    # Streamlit iframe taller than widget so brass header + full calendar body fit
    components.html(
        _tradingview_calendar_html(
            height=int(height),
            importance=TV_IMPORTANCE_HIGH,
            countries=countries,
        ),
        height=int(height) + 16,
        scrolling=False,
    )

    st.info(
        "**Micro futures focus:** High-impact **US** prints (FOMC, CPI, NFP, GDP, PCE, etc.) "
        "drive MES / MNQ / MYM volatility. Medium/low events are hidden so the list stays "
        "readable inside the embed. Use **US + major G7** if you also watch ECB / BOE / BOJ risk."
    )

    # ── Bloomberg live desk (secondary) ───────────────────────────────────
    desk_section("Bloomberg Business News Live (desk coverage)", side="bear")
    st.caption(
        "Optional live audio/video while high-impact releases hit. Toggle off to stop sound."
    )
    render_bloomberg_player(
        height=360,
        key_prefix="econ_bb",
        compact=True,
        title="Bloomberg Business News Live · Event Desk",
        default_on=False,
    )

    # ── Optional fallback table ───────────────────────────────────────────
    with candle_expander(
        "Fallback event table (if TradingView is blocked)",
        side="bear",
        expanded=False,
        kind="link",
    ):
        st.caption(
            "US-focused structured grid (third-party). Prefer TradingView embed above."
        )
        components.html(
            _investing_calendar_iframe(height=640),
            height=680,
            scrolling=True,
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

**In-app:** TradingView Economic Calendar · **High importance** · US (Micro filter)  
**Live desk:** Bloomberg Business News Live  
**External:** [TradingView]({TRADINGVIEW_CALENDAR_URL}) · [Bloomberg]({BLOOMBERG_CALENDAR_URL}) · [Forex Factory]({FOREX_FACTORY_CALENDAR_URL})
"""
        )


def render_economic_calendar_compact(*, key_prefix: str = "econ") -> None:
    """Optional compact expander for other pages — high-impact Micro focus."""
    with candle_expander(
        "Economic Calendar — high-impact Micro filter",
        side="bear",
        expanded=False,
        kind="link",
    ):
        st.markdown(
            "Pre-filtered for **high-importance US** events that move **MES / MNQ / MYM**. "
            "Not a trade signal. Free third-party sources — **no partnership**."
        )
        components.html(
            _tradingview_calendar_html(
                height=520,
                importance=TV_IMPORTANCE_HIGH,
                countries=TV_COUNTRIES_MICROS,
            ),
            height=536,
            scrolling=False,
        )
        st.link_button(
            link_label("Open full TradingView Calendar"),
            TRADINGVIEW_CALENDAR_URL,
            use_container_width=True,
            key=f"{key_prefix}_tv_link",
            type="primary",
        )
        st.link_button(
            link_label("Open Bloomberg Economic Calendar"),
            BLOOMBERG_CALENDAR_URL,
            use_container_width=True,
            key=f"{key_prefix}_bb_cal_link",
        )
        render_third_party_disclosure(expanded=False)
