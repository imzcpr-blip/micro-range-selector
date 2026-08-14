"""
Platforms & Brokers panel — popular tools among micro futures traders.

Links only (no partnership). NinjaTrader, Ironbeam, and TradingView are
independent third parties.
"""

from __future__ import annotations

import streamlit as st

from pathlib import Path

from config import PLATFORM_IRONBEAM_STRUCTURE_IMAGE, RULEBOOK_VERSION
from disclosure import render_disclosure, render_third_party_disclosure
from wallstreet_ui import candle_expander, desk_section, link_label, page_hero

NINJATRADER_URL = "https://ninjatrader.com"
IRONBEAM_URL = "https://www.ironbeam.com"
TRADINGVIEW_URL = "https://www.tradingview.com"


def render_platforms_brokers_panel() -> None:
    """Dedicated Platforms & Brokers page for members."""
    page_hero(
        "Platforms & Brokers",
        "Where independent micro traders often work · links only · zero partnership",
        side="bull",
        desk_tag="EXECUTION DESK · EXTERNAL VENDORS",
    )

    with candle_expander("A common micro stack (not a sales pitch)", side="bull", expanded=True, kind="up"):
        st.markdown(
            """
Serious Micro traders usually need three rooms: a place to **see** structure, a place to **manage** orders, and a **broker** that clears the trade. These names show up often in that conversation:

| Role | Site |
|------|------|
| Platform / charting & order tools | **NinjaTrader** |
| Charting, multi-market study, watchlists | **TradingView** |
| Futures broker | **Ironbeam** |

**Listing them here is not an endorsement, referral fee, or partnership.** CPRP Strategies stays independent. You choose vendors; you own the account.
"""
        )

    with candle_expander("How CPRP expects you to use them", side="bear", expanded=False, kind="down"):
        st.markdown(
            f"""
**Stack (Official Rulebook v{RULEBOOK_VERSION}):** **Ironbeam + NinjaTrader (Web preferred)** for live tickets and structure.

- Keep a **static 1H (or 4H)** context chart open — trend & major S/R only; **never entries**.  
- Define the active **S/R range/channel** on higher TFs (15m / 30m).  
- **Execution is adaptive:** use **1m or 5m** — whichever is **respecting RSI** (fade ≥70 / bounce ≤30).  
- If **neither** 1m nor 5m respects RSI extremes → **stand aside**.  
- Send live risk only through **your** broker under **your** hard stop (−$50 to −$100 under CPRP).  
- This app **never** places or cancels orders and is not wired into any of these firms.
"""
        )

    desk_section("Ironbeam + NinjaTrader structure desk", side="bull")
    st.caption(
        "Reference layout from the founder desk: MES structure window, bid/ask, RSI + EMAs, "
        "account panel, and notifications. Educational screenshot — not a signal."
    )
    _ib_img = Path(PLATFORM_IRONBEAM_STRUCTURE_IMAGE)
    if _ib_img.is_file():
        st.image(
            str(_ib_img),
            use_container_width=True,
            caption="Ironbeam · Structure desk · MES · 1m execution TF with RSI (CPRP adaptive selection)",
        )
    else:
        st.info("Ironbeam structure desk image not found in assets/platforms/.")

    desk_section("Open the sites", side="bull")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### NinjaTrader")
        st.markdown(
            "Charting and trading platform often used for futures and micros — "
            "structure charts, execution, and order tools in one workspace. "
            "**Web preferred** for clear High/Low display (Rulebook v"
            f"{RULEBOOK_VERSION}).  \n"
            f"🔗 [https://ninjatrader.com]({NINJATRADER_URL})"
        )
        st.link_button(
            link_label("Visit NinjaTrader"),
            NINJATRADER_URL,
            type="primary",
            use_container_width=True,
        )
    with c2:
        st.markdown("#### TradingView")
        st.markdown(
            "Popular web charting and market-analysis platform used by many traders for "
            "multi-timeframe structure, indicators, watchlists, and layout sharing. "
            "Useful for reviewing MES / MNQ / MYM ranges; **not a futures broker** — "
            "orders still go through your own brokerage.  \n"
            f"🔗 [https://www.tradingview.com]({TRADINGVIEW_URL})"
        )
        st.link_button(
            link_label("Visit TradingView"),
            TRADINGVIEW_URL,
            type="primary",
            use_container_width=True,
        )
    with c3:
        st.markdown("#### Ironbeam")
        st.markdown(
            "Futures broker used for account setup, margin, and order routing "
            "(MES / MNQ / MYM). Often paired with NinjaTrader for the structure + ticket stack.  \n"
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
  endorsed by, or partnered with NinjaTrader, TradingView, Ironbeam, or any other broker
  or platform.
- **No referral fees stated:** These are public websites listed for education and convenience.
- **Your account, your risk:** Account approval, fees, margin, subscriptions, and product
  availability are between you and that company alone.
- **TradingView is not a futures broker:** charting and analysis only unless you connect
  a separate broker integration under **their** terms.
- **Do your own due diligence** before opening any brokerage, platform, or paid account.
"""
        )

    render_disclosure(expanded=False)
    render_third_party_disclosure(expanded=False)

    st.caption(
        "External websites open in a new browser context via the buttons above. "
        "You leave the CPRP app when you visit those sites."
    )
