"""
Micro E-mini Futures education panel for CPRP.

Explains what micros are, tick values, and position sizing under the hard-stop rule.
$/point values from CME Group (and matching Ironbeam published specs):

  MES  — $5.00 per index point  (tick 0.25 → $1.25)
  MNQ  — $2.00 per index point  (tick 0.25 → $0.50)
  MYM  — $0.50 per index point  (tick 1.00 → $0.50)
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
from wallstreet_ui import candle_expander, desk_section, link_label, page_hero

EDU_DIR = Path(__file__).resolve().parent / "assets" / "education"

OVERVIEW_IMG = EDU_DIR / "micro_emini_overview.png"
TICKS_IMG = EDU_DIR / "micro_tick_values.png"
SIZING_IMG = EDU_DIR / "micro_position_sizing.png"

# Public contract / education references (no partnership)
CME_MES_URL = "https://www.cmegroup.com/markets/equities/sp/micro-e-mini-sandp-500.html"
CME_MNQ_URL = "https://www.cmegroup.com/markets/equities/nasdaq/micro-e-mini-nasdaq-100.html"
CME_MICROS_URL = "https://www.cmegroup.com/markets/equities/micro-emini-equity.html"
IRONBEAM_SPECS_URL = "https://www.ironbeam.com/micro-e-mini-futures-contract-specs/"
NINJATRADER_MICROS_URL = "https://ninjatrader.com/futures/futures-contracts/micro-emini/"
NINJATRADER_MICRO_FUTURES_URL = "https://ninjatrader.com/futures/futures-contracts/micro-futures/"
NINJATRADER_MES_BLOG_URL = (
    "https://ninjatrader.com/futures/blogs/what-are-micro-e-mini-s-p-500-futures-mes/"
)


def _stop_pts(point_value: float, hard_stop: float) -> float:
    return hard_stop / point_value if point_value else 0.0


def _money(v: float) -> str:
    """Format dollars clearly (always show two decimals + $)."""
    return f"${v:,.2f}"


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
dollar risk per point**, so traders can size risk more precisely under a fixed hard stop.

Under CPRP you trade **micros only**:

| Symbol | Name | Role in CPRP | **$ / Point** (CME) |
|--------|------|----------------|---------------------|
| **MES** | Micro E-mini S&P 500 | **Primary** default | **$5.00** |
| **MNQ** | Micro E-mini Nasdaq-100 | Secondary — when clearly superior | **$2.00** |
| **MYM** | Micro E-mini Dow | Tertiary — lower $ volatility option | **$0.50** |

No full-size contracts (ES, NQ, YM, etc.) are part of this protocol.
"""
        )
        if OVERVIEW_IMG.is_file():
            st.image(str(OVERVIEW_IMG), use_container_width=True, caption="Micro E-mini overview")

    desk_section("Contract specifications (CME)", side="bull")
    with candle_expander("Tick values & $ per point (CME reference)", side="bull", expanded=True, kind="page"):
        st.markdown(
            """
A **point** is one full index point. **$ / point** is how many dollars one contract gains or loses  
when the index moves **one full point**.

A **tick** is the minimum price increment. **Tick value** = min tick size × $ / point.

### CME Micro E-mini values (each contract is different)
"""
        )

        # Primary clear table — values from config (aligned to CME / Ironbeam)
        rows = []
        for short in ("MES", "MNQ", "MYM"):
            inst = INSTRUMENTS[short]
            rows.append(
                {
                    "Symbol": short,
                    "Contract": inst.name,
                    "$ / Point": _money(inst.point_value),
                    "Min tick (pts)": f"{inst.tick_size:g}",
                    "Tick value": _money(inst.tick_value),
                    "Check": (
                        f"{inst.tick_size:g} × {_money(inst.point_value)} "
                        f"= {_money(inst.tick_size * inst.point_value)}"
                    ),
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)

        st.markdown(
            f"""
| Symbol | Multiplier (CME) | Min tick | Tick value | Why it differs |
|--------|------------------|----------|------------|----------------|
| **MES** | **$5** × S&P 500 Index | 0.25 pt | **$1.25** | 1/10 of full ES ($50/pt) |
| **MNQ** | **$2** × Nasdaq-100 Index | 0.25 pt | **$0.50** | 1/10 of full NQ ($20/pt) |
| **MYM** | **$0.50** × Dow Jones Index | 1.00 pt | **$0.50** | 1/10 of full YM ($5/pt) |

**Examples (1 contract)**  
- MES moves **+10 points** → **+$50** (10 × $5.00)  
- MNQ moves **+10 points** → **+$20** (10 × $2.00)  
- MYM moves **+10 points** → **+$5** (10 × $0.50)
"""
        )

        if TICKS_IMG.is_file():
            st.image(
                str(TICKS_IMG),
                use_container_width=True,
                caption="Tick values — MES $5.00 · MNQ $2.00 · MYM $0.50 per point (CME)",
            )

        st.markdown("##### Official / broker reference (free public pages)")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.link_button(
                link_label("CME Micro E-mini hub"),
                CME_MICROS_URL,
                use_container_width=True,
            )
        with c2:
            st.link_button(
                link_label("CME MES contract"),
                CME_MES_URL,
                use_container_width=True,
            )
        with c3:
            st.link_button(
                link_label("NinjaTrader Micro Specs"),
                NINJATRADER_MICROS_URL,
                use_container_width=True,
            )
        with c4:
            st.link_button(
                link_label("Ironbeam Micro specs"),
                IRONBEAM_SPECS_URL,
                use_container_width=True,
            )
        st.caption(
            "Values above match CME Group published multipliers and common broker education pages "
            "(NinjaTrader, Ironbeam). Always re-confirm live contract specifications with your broker "
            "and CME before trading — specifications, margins, and fees can change."
        )

    with candle_expander("NinjaTrader Micro Specs", side="bull", expanded=True, kind="link"):
        st.markdown(
            """
**NinjaTrader** publishes education and contract pages for **Micro E-mini** products
(MES, MNQ, MYM, and related micros). Specs on those pages align with **CME** multipliers:

| Symbol | Contract | $ / Point (NinjaTrader / CME) | Tick | Tick $ |
|--------|----------|-------------------------------|------|--------|
| **MES** | Micro E-mini S&P 500 | **$5.00** | 0.25 | **$1.25** |
| **MNQ** | Micro E-mini Nasdaq-100 | **$2.00** | 0.25 | **$0.50** |
| **MYM** | Micro E-mini Dow | **$0.50** | 1.00 | **$0.50** |

NinjaTrader often highlights Micro E-minis as **1/10th** the size of full E-minis (e.g. MES vs ES),
with lower notional exposure per contract — useful under CPRP’s hard dollar stop.

**CPRP Strategies is not affiliated with, partnered with, or endorsed by NinjaTrader.**
Links are for convenience and education only. Margins and fees are set by your broker account
and can change.
"""
        )
        n1, n2, n3 = st.columns(3)
        with n1:
            st.link_button(
                link_label("NinjaTrader Micro E-mini"),
                NINJATRADER_MICROS_URL,
                type="primary",
                use_container_width=True,
            )
        with n2:
            st.link_button(
                link_label("NinjaTrader Micro Futures hub"),
                NINJATRADER_MICRO_FUTURES_URL,
                use_container_width=True,
            )
        with n3:
            st.link_button(
                link_label("NinjaTrader MES overview"),
                NINJATRADER_MES_BLOG_URL,
                use_container_width=True,
            )

    with candle_expander("Position sizing under the CPRP hard stop", side="bear", expanded=True, kind="down"):
        st.markdown(
            f"""
CPRP hard risk rule (non-negotiable):

- **Max loss per trade: −${HARD_STOP_MIN_USD:.0f} to −${HARD_STOP_MAX_USD:.0f}**
- Exit immediately at the limit · **no averaging down**

**Stop distance (index points)** for **one** micro contract:

`points = hard_stop_dollars ÷ dollars_per_point`

Because **$ / point differs by product**, the same hard stop allows a **different** number of points on each micro:
"""
        )

        size_rows = []
        for short in ("MES", "MNQ", "MYM"):
            inst = INSTRUMENTS[short]
            size_rows.append(
                {
                    "Symbol": short,
                    "$ / Point": _money(inst.point_value),
                    f"Stop @ {_money(HARD_STOP_MIN_USD)}": f"{_stop_pts(inst.point_value, HARD_STOP_MIN_USD):.1f} pts",
                    f"Stop @ {_money(HARD_STOP_DEFAULT_USD)}": f"{_stop_pts(inst.point_value, HARD_STOP_DEFAULT_USD):.1f} pts",
                    f"Stop @ {_money(HARD_STOP_MAX_USD)}": f"{_stop_pts(inst.point_value, HARD_STOP_MAX_USD):.1f} pts",
                    "Tick $": _money(inst.tick_value),
                }
            )
        st.dataframe(size_rows, use_container_width=True, hide_index=True)

        st.markdown(
            f"""
| Symbol | $ / Point | Max stop width @ −$100 | Meaning |
|--------|-----------|------------------------|---------|
| **MES** | **$5.00** | **20.0 points** | Tighter structure needed than MNQ/MYM |
| **MNQ** | **$2.00** | **50.0 points** | More room in points, same dollar risk |
| **MYM** | **$0.50** | **200 points** | Widest point allowance for −$100 |

Example: hard stop **−$75**  
- MES → 75 ÷ 5.00 = **15.0 pts**  
- MNQ → 75 ÷ 2.00 = **37.5 pts**  
- MYM → 75 ÷ 0.50 = **150 pts**
"""
        )

        if SIZING_IMG.is_file():
            st.image(
                str(SIZING_IMG),
                use_container_width=True,
                caption="Position sizing vs CPRP hard stop (−$50 / −$75 / −$100) using CME $ / point",
            )

        st.markdown(
            f"""
### Practical CPRP sizing rules

1. **Structure first** — only trade if the stop fits **inside** the −${HARD_STOP_MIN_USD:.0f} to −${HARD_STOP_MAX_USD:.0f} band.  
2. **Prefer MES** when uncertain — fewer points of stop distance per dollar of risk ($5/pt).  
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
visible structure width roughly fits your hard dollar stop (using each micro’s **different**
$ / point). **You** still confirm structure and place orders on your own platform/broker.
This tool does **not** place orders.
"""
        )

    st.caption(
        f"Educational content for {PROTOCOL_SHORT} members. "
        f"Contract multipliers: CME MES $5/pt · MNQ $2/pt · MYM $0.50/pt. "
        f"© {CREATOR}. Not financial advice. Futures trading involves substantial risk of loss."
    )
