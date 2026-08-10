"""
Session Winning vs. Losing Trades panel.

Displays founder-provided session performance charts
(win/loss mix and contracts by instrument).
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from config import (
    CREATOR,
    SESSION_WL_CONTRACTS_IMAGE,
    SESSION_WL_LABEL,
    SESSION_WL_TRADES_IMAGE,
    SESSIONS_DIR,
)
from disclosure import render_disclosure


def _session_chart_files() -> list[tuple[str, Path]]:
    """
    Return (caption, path) for known session charts, newest-friendly order.
    Also picks up any extra Session_*.png files in assets/sessions.
    """
    known = [
        ("Winning vs. losing trades", Path(SESSION_WL_TRADES_IMAGE)),
        ("Contracts traded by instrument", Path(SESSION_WL_CONTRACTS_IMAGE)),
    ]
    out: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    for cap, p in known:
        if p.is_file():
            out.append((cap, p))
            seen.add(p.resolve())

    sessions = Path(SESSIONS_DIR)
    if sessions.is_dir():
        for p in sorted(sessions.glob("Session_*.png"), reverse=True):
            if p.resolve() in seen:
                continue
            # Friendly caption from filename
            label = p.stem.replace("_", " ")
            out.append((label, p))
            seen.add(p.resolve())
    return out


def render_session_wl_panel() -> None:
    """Full page: Session Winning vs. Losing Trades charts."""
    st.title("Session Winning vs. Losing Trades")
    st.caption(
        f"Session performance snapshots for **{SESSION_WL_LABEL}** · shared by {CREATOR}. "
        "Illustrative results only — not a performance guarantee or solicitation."
    )
    render_disclosure(expanded=False)

    charts = _session_chart_files()
    if not charts:
        st.warning(
            "No session charts found. Place PNG files in `assets/sessions/` "
            "(e.g. from CPRP Trading)."
        )
        return

    st.markdown(f"### {SESSION_WL_LABEL}")
    st.markdown(
        """
These charts summarize **winning vs. losing trades** and **contracts traded by instrument**
for a completed CPRP session. Use them as a learning reference alongside your Trading Journal.
"""
    )

    # Side-by-side when we have the two primary charts
    primary = [c for c in charts if c[1].name in {
        Path(SESSION_WL_TRADES_IMAGE).name,
        Path(SESSION_WL_CONTRACTS_IMAGE).name,
    }]
    extras = [c for c in charts if c not in primary]

    if len(primary) >= 2:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**{primary[0][0]}**")
            st.image(str(primary[0][1]), use_container_width=True)
            st.download_button(
                "Download chart",
                data=primary[0][1].read_bytes(),
                file_name=primary[0][1].name,
                mime="image/png",
                key="dl_wl_trades",
                use_container_width=True,
            )
        with c2:
            st.markdown(f"**{primary[1][0]}**")
            st.image(str(primary[1][1]), use_container_width=True)
            st.download_button(
                "Download chart",
                data=primary[1][1].read_bytes(),
                file_name=primary[1][1].name,
                mime="image/png",
                key="dl_wl_contracts",
                use_container_width=True,
            )
    else:
        for cap, path in primary:
            st.markdown(f"**{cap}**")
            st.image(str(path), use_container_width=True)

    for cap, path in extras:
        st.markdown("---")
        st.markdown(f"**{cap}**")
        st.image(str(path), use_container_width=True)
        st.download_button(
            "Download chart",
            data=path.read_bytes(),
            file_name=path.name,
            mime="image/png",
            key=f"dl_session_{path.name}",
            use_container_width=True,
        )

    st.markdown("---")
    st.caption(
        "Charts reflect one session sample under CPRP rules. "
        "Past results do not indicate future performance. "
        "Not financial advice."
    )
