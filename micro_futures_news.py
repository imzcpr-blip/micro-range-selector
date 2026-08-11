"""
Micro Futures News panel — TradingView Top Stories for MES / MNQ / MYM.

Uses the free TradingView Timeline / Top Stories embed, scoped to continuous
Micro futures symbols (MES1! / MNQ1! / MYM1!), with related full-size
continuous contracts (ES1! / NQ1! / YM1!) as a secondary feed.

Auto-refreshes the embeds every 60 seconds (Streamlit fragment) and supports
a manual refresh that remounts the widgets.

No partnership with TradingView. Stories open on TradingView; we do not
republish full article text.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components

from config import PROTOCOL_SHORT
from disclosure import render_disclosure, render_third_party_disclosure
from wallstreet_ui import candle_expander, desk_section, link_label, page_hero

ET = ZoneInfo("America/New_York")

# Micro → TradingView continuous symbols
MICRO_TV_NEWS: dict[str, dict[str, Any]] = {
    "MES": {
        "label": "Micro E-mini S&P 500",
        "index": "S&P 500",
        "tv_primary": "CME_MINI:MES1!",
        "tv_related": "CME_MINI:ES1!",
        "tv_url": "https://www.tradingview.com/symbols/CME_MINI-MES1!/news/",
    },
    "MNQ": {
        "label": "Micro E-mini Nasdaq-100",
        "index": "Nasdaq-100",
        "tv_primary": "CME_MINI:MNQ1!",
        "tv_related": "CME_MINI:NQ1!",
        "tv_url": "https://www.tradingview.com/symbols/CME_MINI-MNQ1!/news/",
    },
    "MYM": {
        "label": "Micro E-mini Dow",
        "index": "Dow Jones",
        "tv_primary": "CBOT_MINI:MYM1!",
        "tv_related": "CBOT_MINI:YM1!",
        "tv_url": "https://www.tradingview.com/symbols/CBOT_MINI-MYM1!/news/",
    },
}

TV_NEWS_HEIGHT = 620
TV_AUTO_REFRESH_SEC = 60
_KEY_TICK = "mfn_tv_refresh_tick"
_KEY_LAST = "mfn_tv_last_refresh"


def _tv_symbol_path(symbol: str) -> str:
    """CME_MINI:MES1! → CME_MINI-MES1! for TradingView URLs."""
    return symbol.replace(":", "-")


def _tradingview_timeline_html(
    symbol: str,
    *,
    height: int = TV_NEWS_HEIGHT,
    label: str = "",
    bust: int = 0,
) -> str:
    """
    TradingView Top Stories / Timeline widget for one symbol (dark desk theme).
    `bust` is included in a data attribute so remounts force a fresh load.
    """
    chart_h = max(360, int(height) - 30)
    tag = label or symbol
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
      overflow: hidden;
      font-family: 'IBM Plex Mono', system-ui, sans-serif;
    }}
    .tv-news {{
      width: 100%;
      height: {height}px;
      border: 2px solid rgba(201,168,76,0.4);
      box-sizing: border-box;
      background: #060a0e;
      display: flex;
      flex-direction: column;
    }}
    .tv-news-head {{
      flex: 0 0 30px;
      height: 30px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 12px;
      background: linear-gradient(180deg, #1a160e, #0a0c10);
      border-bottom: 1px solid rgba(201,168,76,0.4);
      font-size: 10px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: #C9A84C;
    }}
    .tv-news-head a {{ color: #C9A84C; text-decoration: none; }}
    .tradingview-widget-container {{
      flex: 1 1 auto;
      width: 100%;
      height: {chart_h}px;
    }}
    .tradingview-widget-container__widget {{
      width: 100% !important;
      height: {chart_h}px !important;
    }}
  </style>
</head>
<body data-refresh-bust="{bust}">
  <div class="tv-news">
    <div class="tv-news-head">
      <span>TradingView News · {tag}</span>
      <a href="https://www.tradingview.com/symbols/{_tv_symbol_path(symbol)}/news/"
         target="_blank" rel="noopener noreferrer">{symbol}</a>
    </div>
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript"
        src="https://s3.tradingview.com/external-embedding/embed-widget-timeline.js"
        async>
      {{
        "feedMode": "symbol",
        "symbol": "{symbol}",
        "colorTheme": "dark",
        "isTransparent": false,
        "displayMode": "regular",
        "width": "100%",
        "height": {chart_h},
        "locale": "en"
      }}
      </script>
    </div>
  </div>
</body>
</html>
"""


def _bump_refresh() -> None:
    st.session_state[_KEY_TICK] = int(st.session_state.get(_KEY_TICK, 0)) + 1
    st.session_state[_KEY_LAST] = datetime.now(tz=ET).isoformat()


def _refresh_tick() -> int:
    return int(st.session_state.get(_KEY_TICK, 0))


def _fmt_last_refresh() -> str:
    raw = st.session_state.get(_KEY_LAST)
    if not raw:
        return "—"
    try:
        dt = datetime.fromisoformat(str(raw))
        return dt.strftime("%H:%M:%S ET")
    except Exception:
        return str(raw)[:19]


def _render_tradingview_news_for_micro(
    short: str,
    *,
    height: int = TV_NEWS_HEIGHT,
    bust: int = 0,
) -> None:
    """Embed TradingView timeline for micro + related full-size continuous."""
    cfg = MICRO_TV_NEWS[short]
    tv_primary = cfg["tv_primary"]
    tv_related = cfg["tv_related"]

    st.markdown(
        f"**{short}** · `{tv_primary}` continuous · {cfg['label']}  \n"
        f"Related full-size: `{tv_related}` · same {cfg['index']} risk"
    )
    l1, l2 = st.columns(2)
    with l1:
        st.link_button(
            link_label(f"Open {short} news on TradingView"),
            cfg["tv_url"],
            use_container_width=True,
            type="secondary",
            key=f"mfn_tv_open_{short}_{bust}",
        )
    with l2:
        st.link_button(
            link_label(f"Open {tv_related} on TradingView"),
            f"https://www.tradingview.com/symbols/{_tv_symbol_path(tv_related)}/news/",
            use_container_width=True,
            type="secondary",
            key=f"mfn_tv_rel_{short}_{bust}",
        )

    sub_p, sub_r = st.tabs(
        [f"● {short} · {tv_primary}", f"● Related · {tv_related}"]
    )
    with sub_p:
        components.html(
            _tradingview_timeline_html(
                tv_primary,
                height=height,
                label=f"{short} · {tv_primary}",
                bust=bust,
            ),
            height=height + 8,
            scrolling=False,
        )
    with sub_r:
        st.caption(
            f"Full-size continuous **{tv_related}** — often denser news than the micro ticker."
        )
        components.html(
            _tradingview_timeline_html(
                tv_related,
                height=height,
                label=f"{short} related · {tv_related}",
                bust=bust,
            ),
            height=height + 8,
            scrolling=False,
        )


@st.fragment(run_every=timedelta(seconds=TV_AUTO_REFRESH_SEC))
def _auto_refreshing_tv_news(*, height: int) -> None:
    """
    Fragment re-runs every 60s so TradingView embeds remount with fresh news.
    Only bumps the remount tick when ≥60s have passed since last refresh
    (avoids double-bump on parent reruns / slider changes).
    """
    now = datetime.now(tz=ET)
    last_raw = st.session_state.get(_KEY_LAST)
    if not last_raw:
        st.session_state[_KEY_LAST] = now.isoformat()
    else:
        try:
            last = datetime.fromisoformat(str(last_raw))
            if last.tzinfo is None:
                last = last.replace(tzinfo=ET)
            elapsed = (now - last).total_seconds()
        except Exception:
            elapsed = TV_AUTO_REFRESH_SEC
        # Timer fired (or clock skew): remount widgets
        if elapsed >= (TV_AUTO_REFRESH_SEC - 2):
            st.session_state[_KEY_TICK] = int(st.session_state.get(_KEY_TICK, 0)) + 1
            st.session_state[_KEY_LAST] = now.isoformat()

    bust = _refresh_tick()
    last = _fmt_last_refresh()

    st.caption(
        f"● Auto-refresh every **{TV_AUTO_REFRESH_SEC}s** · "
        f"Last update **{last}** · refresh #{bust} · {PROTOCOL_SHORT} desk"
    )

    tv_tabs = st.tabs(
        [
            "● MES · MES1!",
            "● MNQ · MNQ1!",
            "● MYM · MYM1!",
            "● All three",
        ]
    )
    for tab, short in zip(tv_tabs[:3], ("MES", "MNQ", "MYM")):
        with tab:
            _render_tradingview_news_for_micro(short, height=height, bust=bust)

    with tv_tabs[3]:
        st.caption(
            "Side-by-side continuous micro feeds. Use individual tabs for related full-size news."
        )
        c1, c2, c3 = st.columns(3)
        for col, short in zip((c1, c2, c3), ("MES", "MNQ", "MYM")):
            with col:
                cfg = MICRO_TV_NEWS[short]
                st.markdown(f"**{short}** · `{cfg['tv_primary']}`")
                components.html(
                    _tradingview_timeline_html(
                        cfg["tv_primary"],
                        height=min(height, 560),
                        label=short,
                        bust=bust,
                    ),
                    height=min(height, 560) + 8,
                    scrolling=False,
                )


def render_micro_futures_news_panel() -> None:
    """Full-page Micro Futures News desk — TradingView only."""
    page_hero(
        "Micro Futures News",
        "TradingView Top Stories for MES1! · MNQ1! · MYM1! · auto-refresh every 60s",
        side="bull",
        desk_tag="NEWS DESK · TRADINGVIEW · MICROS",
    )

    st.caption(
        "Live **TradingView** news for CPRP continuous micros "
        "(`CME_MINI:MES1!` · `CME_MINI:MNQ1!` · `CBOT_MINI:MYM1!`), "
        "with related full-size feeds (ES1! / NQ1! / YM1!).  "
        "Feeds **auto-refresh every 60 seconds**; use **Refresh now** to reload immediately."
    )

    render_disclosure(expanded=False)
    render_third_party_disclosure(expanded=False)

    desk_section("TradingView news links", side="bull")
    t1, t2, t3 = st.columns(3)
    for col, short in zip((t1, t2, t3), ("MES", "MNQ", "MYM")):
        cfg = MICRO_TV_NEWS[short]
        with col:
            st.link_button(
                link_label(f"TV · {short} · {cfg['tv_primary'].split(':')[-1]}"),
                cfg["tv_url"],
                use_container_width=True,
                type="secondary",
                key=f"mfn_tq_{short}",
            )

    desk_section("Live Top Stories", side="bear")

    ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 2])
    with ctrl1:
        if st.button(
            "Refresh now",
            type="primary",
            use_container_width=True,
            key="mfn_manual_refresh",
            help="Remount all TradingView news widgets immediately.",
        ):
            _bump_refresh()
            st.rerun()
    with ctrl2:
        auto_on = st.toggle(
            "Auto-refresh (60s)",
            value=True,
            key="mfn_auto_on",
            help="When on, news widgets reload every 60 seconds.",
        )
    with ctrl3:
        height = st.select_slider(
            "Embed height",
            options=[480, 560, 620, 720, 840],
            value=TV_NEWS_HEIGHT,
            key="mfn_tv_height",
            help="Taller = more stories visible without scrolling the embed.",
        )

    st.caption(
        f"Symbols: **MES1!** · **MNQ1!** · **MYM1!**  ·  "
        f"Related: **ES1!** · **NQ1!** · **YM1!**  ·  "
        f"Last refresh: **{_fmt_last_refresh()}**"
    )

    if auto_on:
        _auto_refreshing_tv_news(height=int(height))
    else:
        # Manual-only mode: static render (still remounts on Refresh now)
        bust = _refresh_tick()
        if _KEY_LAST not in st.session_state:
            st.session_state[_KEY_LAST] = datetime.now(tz=ET).isoformat()
        st.caption(
            f"Auto-refresh **off** · last update **{_fmt_last_refresh()}** · "
            f"refresh #{bust} · use **Refresh now** to update"
        )
        tv_tabs = st.tabs(
            [
                "● MES · MES1!",
                "● MNQ · MNQ1!",
                "● MYM · MYM1!",
                "● All three",
            ]
        )
        for tab, short in zip(tv_tabs[:3], ("MES", "MNQ", "MYM")):
            with tab:
                _render_tradingview_news_for_micro(
                    short, height=int(height), bust=bust
                )
        with tv_tabs[3]:
            c1, c2, c3 = st.columns(3)
            for col, short in zip((c1, c2, c3), ("MES", "MNQ", "MYM")):
                with col:
                    cfg = MICRO_TV_NEWS[short]
                    st.markdown(f"**{short}** · `{cfg['tv_primary']}`")
                    components.html(
                        _tradingview_timeline_html(
                            cfg["tv_primary"],
                            height=min(int(height), 560),
                            label=short,
                            bust=bust,
                        ),
                        height=min(int(height), 560) + 8,
                        scrolling=False,
                    )

    with candle_expander("How this feed works", side="bull", expanded=False, kind="doc"):
        st.markdown(
            f"""
### TradingView Top Stories

| Micro | Continuous | Related full-size |
|-------|------------|-------------------|
| **MES** | `CME_MINI:MES1!` | `CME_MINI:ES1!` |
| **MNQ** | `CME_MINI:MNQ1!` | `CME_MINI:NQ1!` |
| **MYM** | `CBOT_MINI:MYM1!` | `CBOT_MINI:YM1!` |

- Free **Timeline / Top Stories** embed (`feedMode: symbol`).  
- **Auto-refresh every {TV_AUTO_REFRESH_SEC} seconds** remounts the widgets for fresh stories.  
- **Refresh now** reloads immediately.  
- Stories open on TradingView inside the widget.  
- Related full-size continuous often has denser coverage than the micro.

**CPRP Strategies is not affiliated with TradingView.**
"""
        )
