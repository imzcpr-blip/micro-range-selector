"""Shared Acknowledgement & Disclosure for CPRP pages."""

from __future__ import annotations

import streamlit as st

from config import DISCLOSURE_BODY, DISCLOSURE_TITLE


def render_disclosure(*, expanded: bool = False, key: str | None = None) -> None:
    """
    Render the official Acknowledgement & Disclosure.
    Use expanded=True on the landing page; collapsed expander on member pages.
    """
    label = DISCLOSURE_TITLE
    with st.expander(label, expanded=expanded):
        st.markdown(f"### {DISCLOSURE_TITLE}")
        st.markdown(DISCLOSURE_BODY)


def render_disclosure_footer() -> None:
    """Short always-visible footer line + full text in expander."""
    st.markdown("---")
    st.caption(
        "Not financial advice. Futures trading involves substantial risk of loss. "
        "See **Acknowledgement & Disclosure** below."
    )
    render_disclosure(expanded=False)
