"""Shared Acknowledgement & Disclosure for CPRP pages."""

from __future__ import annotations

import streamlit as st

from config import (
    DISCLAIMER_CAPTION,
    DISCLAIMER_SHORT,
    DISCLOSURE_BODY,
    DISCLOSURE_THIRD_PARTY_BODY,
    DISCLOSURE_THIRD_PARTY_TITLE,
    DISCLOSURE_TITLE,
)
from wallstreet_ui import candle_expander


def render_disclosure(*, expanded: bool = False, key: str | None = None) -> None:
    """
    Render the official Acknowledgement & Disclosure.
    Use expanded=True on the landing page; collapsed expander on member pages.
    """
    with candle_expander(DISCLOSURE_TITLE, side="bear", expanded=expanded, kind="doc"):
        st.markdown(f"### {DISCLOSURE_TITLE}")
        st.markdown(DISCLOSURE_BODY)


def render_third_party_disclosure(*, expanded: bool = False) -> None:
    """Free sources, embeds, and no-partnership acknowledgement."""
    with candle_expander(DISCLOSURE_THIRD_PARTY_TITLE, side="bear", expanded=expanded, kind="page"):
        st.markdown(f"### {DISCLOSURE_THIRD_PARTY_TITLE}")
        st.markdown(DISCLOSURE_THIRD_PARTY_BODY)


def render_disclosure_footer() -> None:
    """Always-visible Acknowledgement & Disclosure line + full disclosure panels."""
    st.markdown("---")
    st.markdown(DISCLAIMER_SHORT)
    st.caption(
        "Free third-party tools (if any) are not partnerships. "
        "Expand the disclosure panels below for the full legal text."
    )
    render_disclosure(expanded=False)
    render_third_party_disclosure(expanded=False)


def disclaimer_caption() -> str:
    """Plain-text Acknowledgement & Disclosure for captions."""
    return DISCLAIMER_CAPTION
