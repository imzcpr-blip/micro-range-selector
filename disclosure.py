"""Shared Acknowledgement & Disclosure for CPRP pages."""

from __future__ import annotations

import streamlit as st

from config import (
    DISCLOSURE_BODY,
    DISCLOSURE_THIRD_PARTY_BODY,
    DISCLOSURE_THIRD_PARTY_TITLE,
    DISCLOSURE_TITLE,
)


def render_disclosure(*, expanded: bool = False, key: str | None = None) -> None:
    """
    Render the official Acknowledgement & Disclosure.
    Use expanded=True on the landing page; collapsed expander on member pages.
    """
    with st.expander(DISCLOSURE_TITLE, expanded=expanded):
        st.markdown(f"### {DISCLOSURE_TITLE}")
        st.markdown(DISCLOSURE_BODY)


def render_third_party_disclosure(*, expanded: bool = False) -> None:
    """Free sources, embeds, and no-partnership acknowledgement."""
    with st.expander(DISCLOSURE_THIRD_PARTY_TITLE, expanded=expanded):
        st.markdown(f"### {DISCLOSURE_THIRD_PARTY_TITLE}")
        st.markdown(DISCLOSURE_THIRD_PARTY_BODY)


def render_disclosure_footer() -> None:
    """Short always-visible footer line + full disclosures."""
    st.markdown("---")
    st.caption(
        "Not financial advice. Futures trading involves substantial risk of loss. "
        "Free third-party tools (if any) are not partnerships. "
        "See **Acknowledgement & Disclosure** below."
    )
    render_disclosure(expanded=False)
    render_third_party_disclosure(expanded=False)
