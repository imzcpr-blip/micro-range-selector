"""
Economic Calendar panel — Forex Factory calendar for CPRP members.

Source (free, third-party, no partnership): https://www.forexfactory.com/calendar
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from disclosure import render_disclosure, render_third_party_disclosure
from wallstreet_ui import candle_expander, desk_section, link_label, page_hero

FOREX_FACTORY_CALENDAR_URL = "https://www.forexfactory.com/calendar"
# Some browsers/providers block full-page iframes; still try + always offer direct link.
FOREX_FACTORY_EMBED_URL = "https://www.forexfactory.com/calendar"


def render_economic_calendar_panel() -> None:
    """Dedicated Economic Calendar page."""
    page_hero(
        "Economic Calendar",
        f"High-impact news risk filter · free Forex Factory source · "
        f"🔗 [Open calendar]({FOREX_FACTORY_CALENDAR_URL})",
        side="bear",
        desk_tag="EVENT RISK DESK · THIRD-PARTY",
    )

    with candle_expander("What this is & CPRP use", side="bull", expanded=True, kind="up"):
        st.markdown(
            """
An **economic calendar** lists scheduled macroeconomic releases and events
(e.g. CPI, employment, FOMC, GDP, central-bank speeches) with expected impact levels.

This panel uses the **public Forex Factory calendar** as a free convenience link/embed.
**CPRP Strategies is not affiliated with, partnered with, or endorsed by Forex Factory.**

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

    desk_section("Live calendar feed", side="bear")
    st.info(
        "If the calendar does not appear inside the window below, your browser or Forex Factory "
        "may block embedding. Use **Open full calendar** — the live site always works in a new tab."
    )

    st.link_button(
        link_label("Open full calendar on Forex Factory"),
        FOREX_FACTORY_CALENDAR_URL,
        type="primary",
        use_container_width=True,
    )

    height = 720
    iframe = f"""
    <div style="width:100%;border:1px solid rgba(148,163,184,0.3);border-radius:10px;overflow:hidden;">
      <iframe
        src="{FOREX_FACTORY_EMBED_URL}"
        title="Forex Factory Economic Calendar"
        width="100%"
        height="{height}"
        style="border:0;background:#0f172a;"
        loading="lazy"
        referrerpolicy="no-referrer-when-downgrade"
      ></iframe>
    </div>
    <p style="font-size:12px;opacity:0.75;margin-top:8px;">
      Embedded view of a free public page. Content belongs to Forex Factory / its owners.
      CPRP is independent and not partnered with this site.
    </p>
    """
    components.html(iframe, height=height + 60, scrolling=True)

    with candle_expander("Quick CPRP checklist around news", side="bear", expanded=False, kind="down"):
        st.markdown(
            f"""
| Step | Action |
|------|--------|
| Before high-impact release | Reduce new risk; avoid mid-structure trades |
| During release | Expect wicks / breaks; do not chase lower-TF noise |
| After release | Re-confirm structure on **15m+5m** (or **30m+15m**); apply full confluence |
| Structure breaks | Flatten, pause 30 minutes or wait for new clear range |

**Source:** [{FOREX_FACTORY_CALENDAR_URL}]({FOREX_FACTORY_CALENDAR_URL}) — free third-party resource.
"""
        )


def render_economic_calendar_compact(*, key_prefix: str = "econ") -> None:
    """Optional compact expander for other pages."""
    with candle_expander(
        "Economic Calendar (Forex Factory) — news risk filter",
        side="bear",
        expanded=False,
        kind="link",
    ):
        st.markdown(
            "Use the calendar to **avoid or respect high-impact news** around CPRP range fades. "
            "Not a trade signal. Free third-party source — **no partnership** with Forex Factory."
        )
        st.link_button(
            link_label("Open Forex Factory Calendar"),
            FOREX_FACTORY_CALENDAR_URL,
            use_container_width=True,
            key=f"{key_prefix}_ff_link",
        )
        render_third_party_disclosure(expanded=False)
