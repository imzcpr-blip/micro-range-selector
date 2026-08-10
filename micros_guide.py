"""
Micro E-mini Futures education panel for CPRP.

Explains what micros are, tick values, and position sizing under the hard-stop rule.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from config import (
    CREATOR,
    HARD_STOP_DEFAULT_USD,
    HARD_STOP_MAX_USD,
    HARD_STOP_MIN_USD,
    INSTRUMENTS,
    PROTOCOL_NAME,
    PROTOCOL_SHORT,
)
from disclosure import render_disclosure, render_third_party_disclosure
from wallstreet_ui import candle_expander, desk_section, page_hero

EDU_DIR = Path(__file__).resolve().parent / "assets" / "education"

OVERVIEW_IMG = EDU_DIR / "micro_emini_overview.png"
TICKS_IMG = EDU_DIR / "micro_tick_values.png"
SIZING_IMG = EDU_DIR / "micro_position_sizing.png"


def _stop_pts(point_value: float, hard_stop: float) -> float:
    return hard_stop / point_value if point_value else 0.0


def render_micros_guide_panel() -> None:
    page_hero(
        "Micro E-mini Futures",
        f"Educational instrument desk · {PROTOCOL_NAME} ({PROTOCOL_SHORT}) · MES · MNQ · MYM",
        side="bull",
        desk_tag="INSTRUMENT DESK · CME MICROS",
    )

    render_disclosure(expanded=False)
    render_third_party_disclosure(expanded=False)

    with candle_expander("What are Micro E-mini Futures?", side="bull", expanded=True, kind="up"):
        st.markdown(
            """
**Micro E-mini futures** are smaller versions of CME’s popular equity-index futures.
They track the same major US indexes as the full-size E-minis, but with **smaller
dollar risk per point**, so traders can size risk more precisely.

Under CPRP you trade **micros only**:

| Symbol | Name | Role in CPRP |
|--------|------|----------------|
| **MES** | Micro E-mini S&P 500 | **Primary** default |
| **MNQ** | Micro E-mini Nasdaq-100 | Secondary — when clearly superior |
| **MYM** | Micro E-mini Dow | Tertiary — lower $ volatility option |

No full-size contracts (ES, NQ, YM, etc.) are part of this protocol.
"""
        )
        if OVERVIEW_IMG.is_file():
            st.image(str(OVERVIEW_IMG), use_container_width=True, caption="Micro E-mini overview")

    desk_section("Contract specifications", side="bull")
    with candle_expander("Tick values (CME reference)", side="bull", expanded=False, kind="page"):
        st.markdown(
            """
A **tick** is the minimum price increment. **Tick value** is how many dollars you gain or lose
when price moves one tick (for one contract).
"""
        )
        if TICKS_IMG.is_file():
            st.image(str(TICKS_IMG), use_container_width=True, caption="Tick values — MES / MNQ / MYM")

        rows = []
        for short in ("MES", "MNQ", "MYM"):
            inst = INSTRUMENTS[short]
            rows.append(
                {
                    "Symbol": short,
                    "Contract": inst.name,
                    "$ / point": f"${inst.point_value:.2f}",
                    "Min tick": f"{inst.tick_size:g} pt",
                    "Tick value": f"${inst.tick_value:.2f}",
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption(
            "Always confirm live contract specifications with your broker and the CME. "
            "Specifications can change."
        )

    with candle_expander("Position sizing under the CPRP hard stop", side="bear", expanded=True, kind="down"):
        st.markdown(
            f"""
CPRP hard risk rule (non-negotiable):

- **Max loss per trade: −${HARD_STOP_MIN_USD:.0f} to −${HARD_STOP_MAX_USD:.0f}**
- Exit immediately at the limit · **no averaging down**

**Stop distance (index points)** for one micro contract:

`points = hard_stop_dollars ÷ dollars_per_point`
"""
        )
        if SIZING_IMG.is_file():
            st.image(
                str(SIZING_IMG),
                use_container_width=True,
                caption="Position sizing vs CPRP hard stop (−$50 / −$75 / −$100)",
            )

        size_rows = []
        for short in ("MES", "MNQ", "MYM"):
            inst = INSTRUMENTS[short]
            size_rows.append(
                {
                    "Symbol": short,
                    f"Stop @ ${HARD_STOP_MIN_USD:.0f}": f"{_stop_pts(inst.point_value, HARD_STOP_MIN_USD):.1f} pts",
                    f"Stop @ ${HARD_STOP_DEFAULT_USD:.0f}": f"{_stop_pts(inst.point_value, HARD_STOP_DEFAULT_USD):.1f} pts",
                    f"Stop @ ${HARD_STOP_MAX_USD:.0f}": f"{_stop_pts(inst.point_value, HARD_STOP_MAX_USD):.1f} pts",
                    "Tick $": f"${inst.tick_value:.2f}",
                }
            )
        st.dataframe(size_rows, use_container_width=True, hide_index=True)

        st.markdown(
            f"""
### Practical CPRP sizing rules

1. **Structure first** — only trade if the stop fits **inside** the −${HARD_STOP_MIN_USD:.0f} to −${HARD_STOP_MAX_USD:.0f} band.  
2. **Prefer MES** when uncertain — fewer points of stop distance per dollar of risk.  
3. **If the structure is too wide** for −${HARD_STOP_MAX_USD:.0f}, **stand aside**.  
4. **Never average down** to “make room.”  
5. **One trade, one hard limit** — integrity over recovery.

These figures assume **one micro contract**. Adding size multiplies dollar risk; under CPRP
you must still keep **total** risk per trade inside −${HARD_STOP_MIN_USD:.0f} to −${HARD_STOP_MAX_USD:.0f}.
"""
        )

    with candle_expander("How this fits the Session Micro Selector", side="bull", expanded=False, kind="doc"):
        st.markdown(
            """
This app ranks **MES / MNQ / MYM** for range/channel-reversion conditions and checks whether
visible structure width roughly fits your hard dollar stop. **You** still confirm structure
and place orders on your own platform/broker. This tool does **not** place orders.
"""
        )

    st.caption(
        f"Educational content for {PROTOCOL_SHORT} members. "
        f"© {CREATOR}. Not financial advice. Futures trading involves substantial risk of loss."
    )
