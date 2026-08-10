"""
Wall Street market theme for CPRP Streamlit app.

Dark terminal / trading-desk aesthetic with bullish (green) and bearish (red)
candlestick-styled expanders and professional page headers.
"""

from __future__ import annotations

from typing import Literal

import streamlit as st

# Bullish = green candle, Bearish = red candle
CandleSide = Literal["bull", "bear"]

WS_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

/* ── Base trading-desk canvas ─────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"], .stApp {
  background: radial-gradient(1200px 600px at 10% -10%, #0b1f17 0%, transparent 50%),
              radial-gradient(900px 500px at 100% 0%, #1a0a0a 0%, transparent 45%),
              #05080f !important;
  color: #e2e8f0 !important;
  font-family: 'IBM Plex Sans', 'Segoe UI', system-ui, sans-serif !important;
}

[data-testid="stHeader"] {
  background: rgba(5, 8, 15, 0.85) !important;
  border-bottom: 1px solid rgba(34, 197, 94, 0.15);
}

/* ── Sidebar terminal ─────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0a0f18 0%, #070b12 100%) !important;
  border-right: 1px solid rgba(148, 163, 184, 0.12) !important;
}
[data-testid="stSidebar"] * {
  font-family: 'IBM Plex Sans', system-ui, sans-serif !important;
}
[data-testid="stSidebar"] .stRadio label {
  padding: 0.45rem 0.55rem !important;
  margin: 0.15rem 0 !important;
  border-radius: 6px !important;
  border-left: 3px solid transparent !important;
  transition: background 0.15s ease, border-color 0.15s ease;
}
[data-testid="stSidebar"] .stRadio label:hover {
  background: rgba(15, 23, 42, 0.9) !important;
}
/* Alternating bull / bear accent on nav rows via nth-child of radio options */
[data-testid="stSidebar"] .stRadio > div > label:nth-child(odd) {
  border-left-color: #22c55e !important;
}
[data-testid="stSidebar"] .stRadio > div > label:nth-child(even) {
  border-left-color: #ef4444 !important;
}

/* ── Typography ───────────────────────────────────────────────────────── */
h1, h2, h3 {
  font-family: 'IBM Plex Sans', system-ui, sans-serif !important;
  letter-spacing: 0.02em !important;
  color: #f8fafc !important;
}
h1 {
  font-weight: 700 !important;
  border-bottom: 1px solid rgba(34, 197, 94, 0.25);
  padding-bottom: 0.35rem;
}
code, .stCaption, [data-testid="stCaption"] {
  font-family: 'IBM Plex Mono', ui-monospace, monospace !important;
}

/* ── Cards / containers ───────────────────────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: rgba(15, 23, 42, 0.55) !important;
  border: 1px solid rgba(148, 163, 184, 0.14) !important;
  border-radius: 10px !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.35);
}

/* ── Expanders as candlestick panels ──────────────────────────────────── */
[data-testid="stExpander"] {
  background: linear-gradient(180deg, rgba(15,23,42,0.95), rgba(8,12,20,0.98)) !important;
  border: 1px solid rgba(148, 163, 184, 0.18) !important;
  border-radius: 10px !important;
  margin-bottom: 0.65rem !important;
  overflow: hidden;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.03), 0 6px 18px rgba(0,0,0,0.25);
}
[data-testid="stExpander"] summary {
  font-weight: 600 !important;
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: 0.95rem !important;
  letter-spacing: 0.03em;
  padding: 0.65rem 0.85rem !important;
}
[data-testid="stExpander"] summary:hover {
  background: rgba(30, 41, 59, 0.5) !important;
}

/* Bullish candle expanders (green) */
.ws-bull + div [data-testid="stExpander"],
div.ws-bull [data-testid="stExpander"] {
  border-left: 4px solid #22c55e !important;
  border-color: rgba(34, 197, 94, 0.35) !important;
}
/* Bearish candle expanders (red) */
.ws-bear + div [data-testid="stExpander"],
div.ws-bear [data-testid="stExpander"] {
  border-left: 4px solid #ef4444 !important;
  border-color: rgba(239, 68, 68, 0.35) !important;
}

/* Streamlit doesn't parent expander under our div reliably — style summary text prefixes via global */
[data-testid="stExpander"] summary p {
  margin: 0 !important;
}

/* ── Primary / secondary buttons ──────────────────────────────────────── */
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
  background: linear-gradient(180deg, #16a34a 0%, #15803d 100%) !important;
  border: 1px solid #22c55e !important;
  color: #f0fdf4 !important;
  font-weight: 600 !important;
  border-radius: 6px !important;
  box-shadow: 0 0 0 1px rgba(34,197,94,0.15), 0 4px 12px rgba(22,163,74,0.25);
}
.stButton > button[kind="secondary"],
.stButton > button {
  border-radius: 6px !important;
  border: 1px solid rgba(148,163,184,0.25) !important;
  background: rgba(15, 23, 42, 0.9) !important;
  color: #e2e8f0 !important;
}
.stButton > button:hover {
  border-color: rgba(34, 197, 94, 0.55) !important;
}

/* ── Metrics / tape ───────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 8px;
  padding: 0.5rem 0.75rem;
}
[data-testid="stMetricValue"] {
  font-family: 'IBM Plex Mono', monospace !important;
  color: #86efac !important;
}

/* ── Tabs ─────────────────────────────────────────────────────────────── */
button[data-baseweb="tab"] {
  font-family: 'IBM Plex Mono', monospace !important;
  font-weight: 500 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
  color: #86efac !important;
  border-bottom-color: #22c55e !important;
}

/* ── Inputs ───────────────────────────────────────────────────────────── */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
  background: rgba(8, 12, 20, 0.95) !important;
  border-color: rgba(148, 163, 184, 0.25) !important;
  color: #e2e8f0 !important;
  font-family: 'IBM Plex Mono', monospace !important;
}

/* ── Dataframes ───────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 8px;
  overflow: hidden;
}

/* ── Market header band ───────────────────────────────────────────────── */
.ws-tape {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
  align-items: center;
  padding: 0.55rem 0.9rem;
  margin: 0 0 1rem 0;
  background: linear-gradient(90deg, rgba(15,23,42,0.95), rgba(8,15,12,0.95), rgba(20,10,10,0.95));
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 8px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.78rem;
  letter-spacing: 0.04em;
  color: #94a3b8;
}
.ws-tape .bull { color: #4ade80; font-weight: 600; }
.ws-tape .bear { color: #f87171; font-weight: 600; }
.ws-tape .sym { color: #e2e8f0; font-weight: 600; }
.ws-tape .sep { opacity: 0.35; }

.ws-page-hero {
  padding: 0.85rem 1rem 0.65rem 1rem;
  margin-bottom: 1rem;
  background: linear-gradient(135deg, rgba(15,23,42,0.98) 0%, rgba(10,18,14,0.95) 50%, rgba(22,12,12,0.95) 100%);
  border: 1px solid rgba(34, 197, 94, 0.2);
  border-left: 5px solid #22c55e;
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.35);
}
.ws-page-hero.bear-edge {
  border-left-color: #ef4444;
  border-color: rgba(239, 68, 68, 0.22);
}
.ws-page-hero h1 {
  margin: 0 0 0.25rem 0 !important;
  border: none !important;
  padding: 0 !important;
  font-size: 1.65rem !important;
}
.ws-page-hero .sub {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.82rem;
  color: #94a3b8;
  margin: 0;
}
.ws-candle-mark {
  display: inline-block;
  width: 0.55rem;
  height: 1.1rem;
  margin-right: 0.45rem;
  vertical-align: middle;
  border-radius: 1px;
  position: relative;
}
.ws-candle-mark.bull {
  background: #22c55e;
  box-shadow: 0 -4px 0 0 #22c55e, 0 4px 0 0 #22c55e;
}
.ws-candle-mark.bear {
  background: #ef4444;
  box-shadow: 0 -4px 0 0 #ef4444, 0 4px 0 0 #ef4444;
}

/* ── Links ────────────────────────────────────────────────────────────── */
a { color: #4ade80 !important; }
a:hover { color: #86efac !important; }

/* ── Divider ──────────────────────────────────────────────────────────── */
hr {
  border-color: rgba(148, 163, 184, 0.12) !important;
}
</style>
"""


def inject_wallstreet_theme() -> None:
    """Inject global Wall Street CSS once per run."""
    st.markdown(WS_CSS, unsafe_allow_html=True)


def market_tape(
    *,
    protocol: str = "CPRP",
    version: str = "1.5",
    instruments: str = "MES · MNQ · MYM",
    risk: str = "−$50 / −$100",
) -> None:
    """Top-of-page tape strip (trading desk feel)."""
    st.markdown(
        f"""
<div class="ws-tape">
  <span class="sym">{protocol}</span><span class="sep">|</span>
  <span>RULEBOOK <span class="bull">v{version}</span></span><span class="sep">|</span>
  <span class="bull">▲ BULL</span> / <span class="bear">▼ BEAR</span><span class="sep">|</span>
  <span class="sym">{instruments}</span><span class="sep">|</span>
  <span>HARD RISK <span class="bear">{risk}</span></span><span class="sep">|</span>
  <span>MICROS ONLY</span>
</div>
""",
        unsafe_allow_html=True,
    )


def page_hero(
    title: str,
    subtitle: str = "",
    *,
    side: CandleSide = "bull",
) -> None:
    """Professional market page header with bull/bear edge."""
    edge = "bear-edge" if side == "bear" else ""
    mark = "bear" if side == "bear" else "bull"
    st.markdown(
        f"""
<div class="ws-page-hero {edge}">
  <h1><span class="ws-candle-mark {mark}"></span>{title}</h1>
  <p class="sub">{subtitle}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def candle_label(text: str, *, side: CandleSide = "bull") -> str:
    """Label for nav / expanders with bullish or bearish candle glyph."""
    if side == "bull":
        return f"🟢🕯️ {text}"
    return f"🔴🕯️ {text}"


def candle_expander(
    title: str,
    *,
    side: CandleSide = "bull",
    expanded: bool = False,
):
    """
    Expander that reads as a candlestick panel control.
    Bull = green open · Bear = red open.
    """
    label = candle_label(title, side=side)
    # Marker div helps CSS target following expander when Streamlit allows
    marker = "ws-bull" if side == "bull" else "ws-bear"
    st.markdown(f'<div class="{marker}"></div>', unsafe_allow_html=True)
    return st.expander(label, expanded=expanded)


def nav_candle_pages(pages: list[str]) -> list[str]:
    """Prefix nav page names with alternating bull/bear candles."""
    out = []
    for i, name in enumerate(pages):
        side: CandleSide = "bull" if i % 2 == 0 else "bear"
        out.append(candle_label(name, side=side))
    return out


def strip_candle_prefix(label: str) -> str:
    """Map candle-prefixed nav label back to clean page name."""
    for prefix in ("🟢🕯️ ", "🔴🕯️ ", "🟢 ", "🔴 "):
        if label.startswith(prefix):
            return label[len(prefix) :]
    return label
