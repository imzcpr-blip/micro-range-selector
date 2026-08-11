"""
Micro E-mini Futures education panel for CPRP.

Shows CME contract multipliers ($/point, tick size, tick value) plus
**live market snapshots** (last, session high/low, range) refreshed from Yahoo Finance
for MES / MNQ / MYM continuous futures.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import streamlit as st

from analyzer import fetch_bars
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

ET = ZoneInfo("America/New_York")

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


@dataclass
class LiveMicroQuote:
    short: str
    name: str
    symbol: str
    point_value: float
    tick_size: float
    tick_value: float
    last: float
    session_high: float
    session_low: float
    range_pts: float
    range_usd: float
    change_pts: float
    change_usd: float
    open_price: float
    as_of: str
    error: Optional[str] = None


def _stop_pts(point_value: float, hard_stop: float) -> float:
    return hard_stop / point_value if point_value else 0.0


def _money(v: float) -> str:
    """Format dollars clearly (always show two decimals + $)."""
    return f"${v:,.2f}"


def _pts(v: float) -> str:
    return f"{v:,.2f}"


@st.cache_data(ttl=45, show_spinner=False)
def _fetch_live_quote(short: str) -> LiveMicroQuote:
    """Fetch latest bars and compute live snapshot for one micro (cached ~45s)."""
    inst = INSTRUMENTS[short]
    try:
        bars = fetch_bars(inst.symbol)
        last = float(bars["Close"].iloc[-1])
        # Prefer today's session window when available
        today = datetime.now(ET).date()
        day = bars[bars.index.date == today] if hasattr(bars.index, "date") else bars.tail(78)
        if day is None or len(day) < 2:
            day = bars.tail(78)
        session_high = float(day["High"].max())
        session_low = float(day["Low"].min())
        open_price = float(day["Open"].iloc[0])
        range_pts = session_high - session_low
        change_pts = last - open_price
        as_of = bars.index[-1]
        if hasattr(as_of, "strftime"):
            as_of_s = as_of.strftime("%Y-%m-%d %H:%M %Z")
        else:
            as_of_s = str(as_of)
        return LiveMicroQuote(
            short=short,
            name=inst.name,
            symbol=inst.symbol,
            point_value=inst.point_value,
            tick_size=inst.tick_size,
            tick_value=inst.tick_value,
            last=round(last, 2),
            session_high=round(session_high, 2),
            session_low=round(session_low, 2),
            range_pts=round(range_pts, 2),
            range_usd=round(range_pts * inst.point_value, 2),
            change_pts=round(change_pts, 2),
            change_usd=round(change_pts * inst.point_value, 2),
            open_price=round(open_price, 2),
            as_of=as_of_s,
            error=None,
        )
    except Exception as exc:  # noqa: BLE001
        return LiveMicroQuote(
            short=short,
            name=inst.name,
            symbol=inst.symbol,
            point_value=inst.point_value,
            tick_size=inst.tick_size,
            tick_value=inst.tick_value,
            last=0.0,
            session_high=0.0,
            session_low=0.0,
            range_pts=0.0,
            range_usd=0.0,
            change_pts=0.0,
            change_usd=0.0,
            open_price=0.0,
            as_of="—",
            error=str(exc),
        )


def fetch_all_live_quotes() -> list[LiveMicroQuote]:
    return [_fetch_live_quote(s) for s in ("MES", "MNQ", "MYM")]


def render_micros_guide_panel() -> None:
    page_hero(
        "Micro E-mini Futures",
        f"Live market tape + CME specs · {PROTOCOL_NAME} ({PROTOCOL_SHORT}) · MES · MNQ · MYM",
        side="bull",
        desk_tag="INSTRUMENT DESK · LIVE CME MICROS",
    )

    render_disclosure(expanded=False)
    render_third_party_disclosure(expanded=False)

    # ── Live market values (auto-updating) ───────────────────────────────
    desk_section("Live micro values (auto-refresh)", side="bull")
    c_ref, c_info = st.columns([1, 3])
    with c_ref:
        if st.button("Refresh quotes now", type="primary", use_container_width=True, key="micro_live_refresh"):
            _fetch_live_quote.clear()
            st.rerun()
    with c_info:
        auto = st.toggle(
            "Auto-refresh quotes every 60s",
            value=True,
            key="micro_live_auto",
            help="Re-pulls Yahoo bars on a timer while this page is open. Cache TTL is 45s.",
        )
        st.caption(
            "Live last / high / low / range update from the market feed. "
            "CME **$ / point** and **tick $** are exchange multipliers (stable unless CME changes the contract)."
        )

    # Optional continuous refresh while this page is open
    if auto:
        try:
            from streamlit_autorefresh import st_autorefresh  # type: ignore

            st_autorefresh(interval=60_000, key="micro_live_autorefresh")
        except Exception:
            # Built-in fragment timer when streamlit-autorefresh not installed
            try:
                @st.fragment(run_every=60)
                def _auto_tick() -> None:
                    st.caption(f"Auto-refresh armed · {datetime.now(ET).strftime('%H:%M:%S %Z')}")

                _auto_tick()
            except Exception:
                st.caption("Open this page or click **Refresh quotes now** to update (auto-timer unavailable).")

    with st.spinner("Pulling latest MES / MNQ / MYM bars…"):
        quotes = fetch_all_live_quotes()

    # Metric strip
    mcols = st.columns(3)
    for col, q in zip(mcols, quotes):
        with col:
            if q.error:
                st.metric(q.short, "—", help=q.error)
                st.caption(f"Unavailable: {q.error[:80]}")
            else:
                delta = f"{q.change_pts:+.2f} pts · {_money(q.change_usd)}"
                st.metric(q.short, f"{q.last:,.2f}", delta=delta, help=q.name)
                st.caption(
                    f"$/pt {_money(q.point_value)} · tick {_money(q.tick_value)} "
                    f"({q.tick_size:g} pt)"
                )

    # Full live table
    live_rows = []
    for q in quotes:
        if q.error:
            live_rows.append(
                {
                    "Symbol": q.short,
                    "Contract": q.name,
                    "Last": "—",
                    "Session high": "—",
                    "Session low": "—",
                    "Range (pts)": "—",
                    "Range ($)": "—",
                    "Change (pts)": "—",
                    "Change ($)": "—",
                    "$ / Point": _money(q.point_value),
                    "Tick size": f"{q.tick_size:g}",
                    "Tick $": _money(q.tick_value),
                    "As of": q.error[:60],
                }
            )
        else:
            live_rows.append(
                {
                    "Symbol": q.short,
                    "Contract": q.name,
                    "Last": _pts(q.last),
                    "Session high": _pts(q.session_high),
                    "Session low": _pts(q.session_low),
                    "Range (pts)": _pts(q.range_pts),
                    "Range ($)": _money(q.range_usd),
                    "Change (pts)": f"{q.change_pts:+.2f}",
                    "Change ($)": f"{q.change_usd:+,.2f}",
                    "$ / Point": _money(q.point_value),
                    "Tick size": f"{q.tick_size:g}",
                    "Tick $": _money(q.tick_value),
                    "As of": q.as_of,
                }
            )
    st.dataframe(live_rows, use_container_width=True, hide_index=True)

    # Live examples: 10-pt move, 1-tick move at current structure
    st.markdown("##### Live risk translation (1 contract)")
    ex_rows = []
    for q in quotes:
        ex_rows.append(
            {
                "Symbol": q.short,
                "1 tick move": _money(q.tick_value),
                "10 pts move": _money(10 * q.point_value),
                f"Hard stop pts @ {_money(HARD_STOP_DEFAULT_USD)}": f"{_stop_pts(q.point_value, HARD_STOP_DEFAULT_USD):.1f}",
                "Session range $": _money(q.range_usd) if not q.error else "—",
                "Fits −$100 hard stop?": (
                    "Yes" if (not q.error and q.range_usd <= HARD_STOP_MAX_USD) else
                    ("No — structure wider than max hard stop" if not q.error else "—")
                ),
            }
        )
    st.dataframe(ex_rows, use_container_width=True, hide_index=True)
    st.caption(
        "Live prices via Yahoo Finance continuous futures (delayed). "
        "**$ / Point** and **tick value** are CME contract multipliers (fixed by exchange; not delayed quotes). "
        "Always confirm on NinjaTrader / Ironbeam / CME before trading."
    )

    with candle_expander("What are Micro E-mini Futures?", side="bull", expanded=False, kind="up"):
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

    desk_section("Contract specifications (CME multipliers)", side="bull")
    with candle_expander("Tick values & $ per point (CME — exchange fixed)", side="bull", expanded=True, kind="page"):
        st.markdown(
            """
A **point** is one full index point. **$ / point** is how many dollars one contract gains or loses  
when the index moves **one full point**. These multipliers are set by **CME** and only change if
the exchange updates the contract (rare).

A **tick** is the minimum price increment. **Tick value** = min tick size × $ / point.

### CME Micro E-mini multipliers (authoritative)
"""
        )

        rows = []
        for short in ("MES", "MNQ", "MYM"):
            inst = INSTRUMENTS[short]
            rows.append(
                {
                    "Symbol": short,
                    "Contract": inst.name,
                    "Yahoo symbol": inst.symbol,
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
            """
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
            "Contract multipliers match CME Group and common broker education pages "
            "(NinjaTrader, Ironbeam). Live last/high/low above are market data (delayed). "
            "Always re-confirm specs and margins with your broker before trading."
        )

    with candle_expander("NinjaTrader Micro Specs", side="bull", expanded=False, kind="link"):
        st.markdown(
            """
**NinjaTrader** publishes education and contract pages for **Micro E-mini** products
(MES, MNQ, MYM, and related micros). Specs on those pages align with **CME** multipliers:

| Symbol | Contract | $ / Point (NinjaTrader / CME) | Tick | Tick $ |
|--------|----------|-------------------------------|------|--------|
| **MES** | Micro E-mini S&P 500 | **$5.00** | 0.25 | **$1.25** |
| **MNQ** | Micro E-mini Nasdaq-100 | **$2.00** | 0.25 | **$0.50** |
| **MYM** | Micro E-mini Dow | **$0.50** | 1.00 | **$0.50** |

**CPRP Strategies is not affiliated with, partnered with, or endorsed by NinjaTrader.**
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

        # Live session range vs hard stop using latest quotes
        st.markdown("##### Live session range vs hard stop (from quotes above)")
        live_size = []
        for q in quotes:
            if q.error:
                live_size.append({"Symbol": q.short, "Session range $": "—", "Note": q.error[:50]})
            else:
                fits = q.range_usd <= HARD_STOP_MAX_USD
                live_size.append(
                    {
                        "Symbol": q.short,
                        "Session range $": _money(q.range_usd),
                        "Session range pts": _pts(q.range_pts),
                        f"Max stop pts @ {_money(HARD_STOP_MAX_USD)}": f"{_stop_pts(q.point_value, HARD_STOP_MAX_USD):.1f}",
                        "Fits −$100 hard stop?": "Yes" if fits else "No — wider than max hard stop",
                    }
                )
        st.dataframe(live_size, use_container_width=True, hide_index=True)

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
"""
        )

    with candle_expander("How this fits the Session Micro Selector", side="bull", expanded=False, kind="doc"):
        st.markdown(
            """
This app ranks **MES / MNQ / MYM** for range/channel-reversion conditions and checks whether
visible structure width roughly fits your hard dollar stop (using each micro’s **different**
$ / point). Live values on this page use the same delayed Yahoo feed as the Session Selector.
**You** still confirm structure and place orders on your own platform/broker.
"""
        )

    st.caption(
        f"Educational content for {PROTOCOL_SHORT} members. "
        f"CME multipliers: MES $5/pt · MNQ $2/pt · MYM $0.50/pt. "
        f"Live tape: Yahoo Finance (delayed). © {CREATOR}. Not financial advice."
    )
