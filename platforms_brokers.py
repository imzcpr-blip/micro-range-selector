"""
Platforms & Brokers panel — popular tools among micro futures traders.

Links only (no partnership). NinjaTrader & Ironbeam are independent third parties.
"""

from __future__ import annotations

import streamlit as st

from disclosure import render_disclosure, render_third_party_disclosure

NINJATRADER_URL = "https://ninjatrader.com"
IRONBEAM_URL = "https://www.ironbeam.com"


def render_platforms_brokers_panel() -> None:
    """Dedicated Platforms & Brokers page for members."""
    st.title("Platforms & Brokers")
    st.caption("Popular with micro futures traders · links for convenience only")

    st.markdown(
        """
### Popular with micro traders

Many independent day traders who work with **Micro** contracts (MES, MNQ, MYM, etc.)
use a charting / execution platform together with a futures broker. Two sites often
mentioned in that context are:

| Role | Site |
|------|------|
| Platform / charting & order tools | **NinjaTrader** |
| Futures broker | **Ironbeam** |

These links are provided because they are **commonly used** in the micro futures space
and because the CPRP workflow (structure on NinjaTrader-style charts, orders through a
broker) matches how many people already trade. **Inclusion is not an endorsement, referral
program, or business partnership.**

### Recommended use with CPRP

- Use your platform to mark **confirmed S/R structure**, run **15m+5m** (or **30m+15m**),
  and keep a static **1-Hour** context chart.
- Route live orders only through **your** broker account under **your** risk limits
  (−$50 to −$100 hard stop under CPRP).
- This CPRP app **does not place or cancel orders** and is not connected to either firm.

### Open the sites
"""
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### NinjaTrader")
        st.markdown(
            "Charting and trading platform often used for futures and micros.  \n"
            f"[https://ninjatrader.com]({NINJATRADER_URL})"
        )
        st.link_button(
            "Visit NinjaTrader",
            NINJATRADER_URL,
            type="primary",
            use_container_width=True,
        )
    with c2:
        st.markdown("#### Ironbeam")
        st.markdown(
            "Futures broker used by many micro futures traders.  \n"
            f"[https://www.ironbeam.com]({IRONBEAM_URL})"
        )
        st.link_button(
            "Visit Ironbeam",
            IRONBEAM_URL,
            type="primary",
            use_container_width=True,
        )

    st.markdown("---")
    st.subheader("Important notices")
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
    render_third_party_disclosure(expanded=True)

    st.caption(
        "External websites open in a new browser context via the buttons above. "
        "You leave the CPRP app when you visit those sites."
    )
