"""
Platforms & Brokers panel — popular tools among micro futures traders.

Links only (no partnership). NinjaTrader & Ironbeam are independent third parties.
"""

from __future__ import annotations

import streamlit as st

from disclosure import render_disclosure, render_third_party_disclosure
from wallstreet_ui import candle_expander, desk_section, link_label, page_hero

NINJATRADER_URL = "https://ninjatrader.com"
IRONBEAM_URL = "https://www.ironbeam.com"


def render_platforms_brokers_panel() -> None:
    """Dedicated Platforms & Brokers page for members."""
    page_hero(
        "Platforms & Brokers",
        "Popular micro-futures stack · convenience links only · no partnership or endorsement",
        side="bull",
        desk_tag="EXECUTION DESK · EXTERNAL VENDORS",
    )

    with candle_expander("Popular with micro traders", side="bull", expanded=True, kind="up"):
        st.markdown(
            """
Many independent day traders who work with **Micro** contracts (MES, MNQ, MYM, and others)
use a charting and execution platform together with a futures broker:

| Role | Site |
|------|------|
| Platform / charting & order tools | **NinjaTrader** |
| Futures broker | **Ironbeam** |

**Inclusion is not an endorsement, referral program, or business partnership.**
"""
        )

    with candle_expander("Recommended use with CPRP", side="bear", expanded=False, kind="down"):
        st.markdown(
            """
- Use your platform to mark **confirmed S/R structure**, run **15m+5m** (or **30m+15m**),
  and keep a static **1-Hour** context chart.
- Route live orders only through **your** broker account under **your** risk limits
  (−$50 to −$100 hard stop under CPRP).
- This CPRP app **does not place or cancel orders** and is not connected to either firm.
"""
        )

    desk_section("Open the sites", side="bull")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### NinjaTrader")
        st.markdown(
            "Charting and trading platform often used for futures and micros.  \n"
            f"🔗 [https://ninjatrader.com]({NINJATRADER_URL})"
        )
        st.link_button(
            link_label("Visit NinjaTrader"),
            NINJATRADER_URL,
            type="primary",
            use_container_width=True,
        )
    with c2:
        st.markdown("#### Ironbeam")
        st.markdown(
            "Futures broker used by many micro futures traders.  \n"
            f"🔗 [https://www.ironbeam.com]({IRONBEAM_URL})"
        )
        st.link_button(
            link_label("Visit Ironbeam"),
            IRONBEAM_URL,
            type="primary",
            use_container_width=True,
        )

    with candle_expander(
        "Important notices (read before opening accounts)",
        side="bear",
        expanded=True,
        kind="doc",
    ):
        st.markdown(
            """
- **No partnership:** CPRP Strategies and this tool are **not** owned by, sponsored by,
  endorsed by, or partnered with NinjaTrader, Ironbeam, or any other broker or platform.
- **No referral fees stated:** These are public websites listed for education and convenience.
- **Your account, your risk:** Account approval, fees, margin, and product availability are
  between you and that company alone.
- **Do your own due diligence** before opening any brokerage or platform account.
"""
        )

    render_disclosure(expanded=False)
    render_third_party_disclosure(expanded=False)

    st.caption(
        "External websites open in a new browser context via the buttons above. "
        "You leave the CPRP app when you visit those sites."
    )
