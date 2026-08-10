"""
Bloomberg Business News Live — YouTube embed for CPRP members.

Source: https://www.youtube.com/watch?v=QB5BNdBFujE
Members can watch/listen, pause (hide player stops playback), or open a full panel.
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from wallstreet_ui import candle_expander, desk_section, page_hero

BLOOMBERG_VIDEO_ID = "QB5BNdBFujE"
BLOOMBERG_WATCH_URL = f"https://www.youtube.com/watch?v={BLOOMBERG_VIDEO_ID}"
BLOOMBERG_EMBED_BASE = f"https://www.youtube.com/embed/{BLOOMBERG_VIDEO_ID}"

# Session keys
KEY_ENABLED = "bloomberg_live_enabled"
KEY_MUTED = "bloomberg_live_muted"


def _embed_src(*, autoplay: bool = False, mute: bool = False) -> str:
    # autoplay often requires mute=1 in browsers
    params = [
        "rel=0",
        "modestbranding=1",
        "playsinline=1",
        f"autoplay={1 if autoplay else 0}",
        f"mute={1 if mute else 0}",
    ]
    return BLOOMBERG_EMBED_BASE + "?" + "&".join(params)


def render_bloomberg_player(
    *,
    height: int = 360,
    key_prefix: str = "bb",
    compact: bool = False,
    title: str = "Bloomberg Business News Live",
    default_on: bool = False,
) -> None:
    """
    Embed YouTube live player with on/off control.
    Turning OFF removes the iframe so audio/video stops (pause/stop).
    """
    enabled_key = f"{KEY_ENABLED}_{key_prefix}"
    if enabled_key not in st.session_state:
        # Share global preference across pages when possible
        if KEY_ENABLED in st.session_state:
            st.session_state[enabled_key] = st.session_state[KEY_ENABLED]
        else:
            st.session_state[enabled_key] = default_on

    if compact:
        st.markdown(f"**{title}**")
    else:
        st.subheader(title)

    st.caption(
        "Live stream via YouTube · "
        f"[Open on YouTube]({BLOOMBERG_WATCH_URL}) · "
        "Toggle off to pause / stop the stream."
    )

    c1, c2 = st.columns([2, 1])
    with c1:
        on = st.toggle(
            "Play Bloomberg Live",
            value=bool(st.session_state[enabled_key]),
            key=f"{key_prefix}_toggle",
            help="On = embed player. Off = remove player (stops sound).",
        )
    with c2:
        mute = st.toggle(
            "Start muted",
            value=bool(st.session_state.get(KEY_MUTED, False)),
            key=f"{key_prefix}_mute",
            help="Browsers often require mute for autoplay. You can unmute in the player.",
        )

    st.session_state[enabled_key] = on
    st.session_state[KEY_ENABLED] = on  # global preference
    st.session_state[KEY_MUTED] = mute

    if not on:
        st.info(
            "Bloomberg Live is **paused / off**. Turn **Play Bloomberg Live** on to watch or listen."
        )
        return

    # When enabling, autoplay so audio/video starts (mute recommended for browser policy)
    src = _embed_src(autoplay=True, mute=mute)
    iframe = f"""
    <div style="position:relative;padding-bottom:0;width:100%;">
      <iframe
        width="100%"
        height="{height}"
        src="{src}"
        title="Bloomberg Business News Live"
        frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        allowfullscreen
        referrerpolicy="strict-origin-when-cross-origin"
        style="border-radius:10px;border:1px solid rgba(148,163,184,0.25);"
      ></iframe>
    </div>
    """
    components.html(iframe, height=height + 20, scrolling=False)
    st.caption(
        "Use the YouTube controls to pause, change volume, or go fullscreen. "
        "Toggle **Play Bloomberg Live** off to stop the stream completely."
    )


def render_bloomberg_panel() -> None:
    """Dedicated full-page Bloomberg Live experience."""
    page_hero(
        "Bloomberg Business News Live",
        "External YouTube live desk feed · watch or listen while you trade · not affiliated with Bloomberg",
        side="bear",
        desk_tag="NEWS DESK · EXTERNAL FEED",
    )
    with candle_expander("What this desk is for", side="bull", expanded=True):
        st.markdown(
            """
Watch or listen to **Bloomberg Business News Live** while you trade.  
This is an external YouTube live stream — **CPRP is not affiliated with Bloomberg or YouTube.**
"""
        )
    render_bloomberg_player(
        height=520,
        key_prefix="panel",
        compact=False,
        default_on=True,
    )
    desk_section("Desk tips", side="bear")
    with candle_expander("How to use the news feed", side="bear", expanded=False):
        st.markdown(
            f"""
- Leave this panel open for continuous news while you work.
- Or enable the player on **Session Selector**, **Trading Journal**, or **Member Chat**.
- Toggle off anytime to stop audio/video.
- Direct link: [{BLOOMBERG_WATCH_URL}]({BLOOMBERG_WATCH_URL})
"""
        )
    st.caption(
        "External news stream only. Not affiliated with Bloomberg or YouTube. "
        "Not financial advice — see disclosures below."
    )
    from disclosure import render_disclosure, render_third_party_disclosure

    render_disclosure(expanded=False)
    render_third_party_disclosure(expanded=False)


def render_bloomberg_audio_option(*, key_prefix: str, height: int = 280) -> None:
    """Compact block for main / journal / chat pages."""
    with candle_expander("Bloomberg Business News Live — watch or listen", side="bear", expanded=False):
        render_bloomberg_player(
            height=height,
            key_prefix=key_prefix,
            compact=True,
            default_on=False,
        )
