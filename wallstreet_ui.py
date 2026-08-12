"""
Wall Street market theme for CPRP Streamlit app.

Retro day-trader / stock-exchange floor aesthetic, aligned to CPRP branding:
  Mahogany pit desk · Brass rails · Amber CRT quote boards · Green phosphor ticks ·
  Scanlines · Exchange floor tape · Order-ticket panels.
"""

from __future__ import annotations

from typing import Literal

import streamlit as st
import streamlit.components.v1 as components

# Panel sides: bull = brand gold / bear = steel risk accent
CandleSide = Literal["bull", "bear"]

# CPRP brand palette (seal + candlestick logo)
# Navy: #0A1628  #0F1B2D  #1A2744
# Gold: #C9A84C  #D4AF37  #E8D5A3
# Steel: #94A3B8  #C0C5CE
# Amber ticker: #F0C14B  #E8B923
# Wood: #1a1008  #0d0a06

WS_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0&display=swap');

/* ═══════════════════════════════════════════════════════════════════════════
   RETRO WALL STREET DAY-TRADER FLOOR
   Pit desk · CRT quote boards · Amber LEDs · Scanlines · Order tickets
   ═══════════════════════════════════════════════════════════════════════════ */

/* ── Base canvas — exchange floor + CRT glow ───────────────────────────── */
html, body, [data-testid="stAppViewContainer"], .stApp {
  background:
    /* CRT horizontal scanlines */
    repeating-linear-gradient(
      0deg,
      transparent 0px,
      transparent 2px,
      rgba(0,0,0,0.12) 2px,
      rgba(0,0,0,0.12) 3px
    ),
    /* wood grain */
    repeating-linear-gradient(
      90deg,
      rgba(0,0,0,0.05) 0px,
      rgba(0,0,0,0.05) 1px,
      transparent 1px,
      transparent 8px
    ),
    radial-gradient(1000px 480px at 8% -4%, rgba(240,193,75,0.09) 0%, transparent 50%),
    radial-gradient(900px 500px at 100% 0%, rgba(61,40,12,0.22) 0%, transparent 48%),
    radial-gradient(700px 400px at 50% 100%, rgba(8,40,24,0.18) 0%, transparent 55%),
    linear-gradient(180deg, #0c0a08 0%, #080a10 35%, #050608 100%) !important;
  color: #e8e0cc !important;
  font-family: 'IBM Plex Mono', 'IBM Plex Sans', ui-monospace, system-ui, sans-serif !important;
}

/* Soft vignette over main app (day-trader booth) */
[data-testid="stAppViewContainer"]::before {
  content: "";
  pointer-events: none;
  position: fixed;
  inset: 0;
  z-index: 9998;
  background: radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.35) 100%);
}

[data-testid="stHeader"] {
  background: linear-gradient(180deg, #1a140c 0%, #0a0c10 100%) !important;
  border-bottom: 3px double #C9A84C !important;
  box-shadow: 0 2px 0 rgba(232,213,163,0.2), 0 6px 20px rgba(0,0,0,0.65);
}

/* Main content — blotter pad with brass left rail */
[data-testid="stMain"] {
  background: transparent !important;
}
[data-testid="stMain"] > div {
  border-left: 3px double rgba(201,168,76,0.35);
  padding-left: 0.25rem;
  box-shadow: inset 8px 0 24px rgba(0,0,0,0.25);
}

/* ── Sidebar — order-ticket booth / pit station ───────────────────────── */
[data-testid="stSidebar"] {
  background:
    repeating-linear-gradient(
      0deg,
      transparent 0px,
      transparent 3px,
      rgba(0,0,0,0.08) 3px,
      rgba(0,0,0,0.08) 4px
    ),
    linear-gradient(180deg,
      #1a1208 0%,
      #100e0a 20%,
      #0a0c10 55%,
      #06080c 100%) !important;
  border-right: 4px double #C9A84C !important;
  box-shadow: inset -10px 0 28px rgba(0,0,0,0.55), 6px 0 24px rgba(0,0,0,0.5);
  font-family: 'IBM Plex Mono', system-ui, sans-serif !important;
}
[data-testid="stSidebar"]::before {
  content: "▼ CPRP · DAY TRADER DESK · MICROS";
  display: block;
  text-align: center;
  font-family: 'Cinzel', 'Times New Roman', serif !important;
  font-size: 0.58rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  color: #F0C14B;
  padding: 0.6rem 0.35rem 0.5rem;
  margin: 0 0 0.4rem 0;
  border-bottom: 2px solid rgba(201,168,76,0.45);
  background:
    linear-gradient(180deg, rgba(201,168,76,0.18), rgba(10,12,16,0.9));
  text-shadow: 0 0 10px rgba(240,193,75,0.35), 0 1px 0 rgba(0,0,0,0.8);
}
/*
  Apply brand font carefully. Never override Material Symbols / icon spans —
  otherwise Streamlit shows "keyboard_double_arrow_right" as plain text.
*/
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] button,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
  font-family: 'IBM Plex Sans', system-ui, sans-serif !important;
}
[data-testid="stSidebar"] .stRadio label {
  padding: 0.5rem 0.55rem !important;
  margin: 0.1rem 0 !important;
  border-radius: 0 !important;
  border-left: 4px solid transparent !important;
  border-bottom: 1px dashed rgba(201,168,76,0.12) !important;
  transition: background 0.12s ease, border-color 0.12s ease, box-shadow 0.12s ease;
  background: rgba(6,8,12,0.55);
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: 0.84rem !important;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}
[data-testid="stSidebar"] .stRadio label:hover {
  background: rgba(240,193,75,0.1) !important;
  box-shadow: inset 0 0 0 1px rgba(201,168,76,0.28);
  color: #F0C14B !important;
}
[data-testid="stSidebar"] .stRadio > div > label:nth-child(odd) {
  border-left-color: #C9A84C !important;
}
[data-testid="stSidebar"] .stRadio > div > label:nth-child(even) {
  border-left-color: #8B9BB4 !important;
}

/* ── Typography — firm letterhead + floor mono ────────────────────────── */
h1, h2, h3 {
  font-family: 'Cinzel', 'Times New Roman', Georgia, serif !important;
  letter-spacing: 0.04em !important;
  color: #f4efe0 !important;
  text-shadow: 0 1px 0 rgba(0,0,0,0.55);
}
h1 {
  font-weight: 700 !important;
  border-bottom: 2px solid transparent;
  border-image: linear-gradient(90deg, transparent, #C9A84C 12%, #E8D5A3 50%, #C9A84C 88%, transparent) 1;
  padding-bottom: 0.4rem;
}
h2 {
  font-size: 1.25rem !important;
  color: #E8D5A3 !important;
}
h3 {
  font-size: 1.05rem !important;
  letter-spacing: 0.06em !important;
  color: #C9A84C !important;
}
code, .stCaption, [data-testid="stCaption"] {
  font-family: 'IBM Plex Mono', ui-monospace, monospace !important;
  color: #b8b0a0 !important;
  letter-spacing: 0.02em;
}

/* ── Cards / containers — pit booth frames ────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background:
    linear-gradient(180deg, rgba(26,20,12,0.96), rgba(8,10,14,0.98)) !important;
  border: 2px solid rgba(201, 168, 76, 0.35) !important;
  outline: 1px solid rgba(0, 0, 0, 0.5);
  outline-offset: 2px;
  border-radius: 0 !important;
  box-shadow:
    inset 0 1px 0 rgba(232,213,163,0.1),
    inset 0 0 40px rgba(0,0,0,0.3),
    0 8px 28px rgba(0,0,0,0.5);
}

/* ── Expanders — trading-booth / pit panels ───────────────────────────── */
[data-testid="stExpander"] {
  background:
    linear-gradient(180deg, rgba(28,22,12,0.99) 0%, rgba(8,10,14,0.99) 100%) !important;
  border: 2px solid rgba(201, 168, 76, 0.4) !important;
  border-radius: 0 !important;
  margin-bottom: 0.75rem !important;
  overflow: visible;
  box-shadow:
    inset 0 1px 0 rgba(232,213,163,0.1),
    inset 0 0 0 1px rgba(0,0,0,0.5),
    0 0 0 1px rgba(0,0,0,0.7),
    0 8px 22px rgba(0,0,0,0.5);
  transition: border-color 0.12s ease, box-shadow 0.12s ease;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] details summary,
[data-testid="stExpander"] > details > summary {
  font-weight: 700 !important;
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: 0.82rem !important;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.72rem 0.9rem !important;
  cursor: pointer !important;
  color: #f0e6d0 !important;
  list-style: none !important;
  display: flex !important;
  align-items: center !important;
  gap: 0.4rem !important;
  background: linear-gradient(180deg, rgba(201,168,76,0.14), transparent 75%);
  border-bottom: 1px solid rgba(201,168,76,0.22);
}
[data-testid="stExpander"] summary:hover {
  background: linear-gradient(180deg, rgba(201,168,76,0.16), rgba(201,168,76,0.04)) !important;
}
[data-testid="stExpander"] summary p {
  margin: 0 !important;
  color: inherit !important;
}

/* Force Streamlit expander chevron / Material arrow icons to render as icons */
[data-testid="stExpander"] summary svg,
[data-testid="stExpander"] summary [data-testid="stExpanderToggleIcon"],
[data-testid="stSidebar"] [data-testid="stExpander"] summary svg {
  color: #C9A84C !important;
  fill: #C9A84C !important;
  stroke: #C9A84C !important;
  opacity: 1 !important;
  visibility: visible !important;
  display: inline-block !important;
  width: 1.15rem !important;
  height: 1.15rem !important;
  min-width: 1.15rem !important;
  flex-shrink: 0 !important;
}

/* Material Symbols / material icons */
.material-icons,
.material-symbols-rounded,
.material-symbols-outlined,
[data-testid="stIconMaterial"],
[data-testid="stExpanderToggleIcon"],
[data-testid="stExpander"] summary [class*="material"],
[data-testid="stSidebar"] [class*="material-icons"],
[data-testid="stSidebar"] [class*="material-symbols"],
[data-testid="stSidebar"] span[translate="no"] {
  font-family: "Material Symbols Rounded", "Material Icons", "Material Symbols Outlined" !important;
  font-weight: normal !important;
  font-style: normal !important;
  font-size: 1.25rem !important;
  line-height: 1 !important;
  letter-spacing: normal !important;
  text-transform: none !important;
  display: inline-block !important;
  white-space: nowrap !important;
  word-wrap: normal !important;
  direction: ltr !important;
  -webkit-font-feature-settings: "liga" !important;
  font-feature-settings: "liga" !important;
  -webkit-font-smoothing: antialiased !important;
  color: #C9A84C !important;
  opacity: 1 !important;
  visibility: visible !important;
}

[data-testid="stExpander"] summary > div:first-child,
[data-testid="stExpander"] summary > span:first-child {
  color: #C9A84C !important;
  flex-shrink: 0 !important;
}

/* Gold accent panels (📈 / docs / primary) */
[data-testid="stExpander"].ws-candle-bull {
  border-left: 5px solid #C9A84C !important;
  border-color: rgba(201, 168, 76, 0.5) !important;
  box-shadow:
    inset 0 0 0 1px rgba(201,168,76,0.12),
    inset 4px 0 12px rgba(201,168,76,0.06),
    0 6px 18px rgba(0,0,0,0.35);
}
[data-testid="stExpander"].ws-candle-bull summary {
  color: #E8D5A3 !important;
  background: linear-gradient(90deg, rgba(201,168,76,0.18), transparent 60%);
}
/* Steel / risk panels (📉 / risk / TV) */
[data-testid="stExpander"].ws-candle-bear {
  border-left: 5px solid #8B9BB4 !important;
  border-color: rgba(139, 155, 180, 0.42) !important;
  box-shadow:
    inset 0 0 0 1px rgba(139,155,180,0.1),
    0 6px 18px rgba(0,0,0,0.32);
}
[data-testid="stExpander"].ws-candle-bear summary {
  color: #C5D0E0 !important;
  background: linear-gradient(90deg, rgba(139,155,180,0.14), transparent 55%);
}

/* ── Buttons — pit ticket punch / brass CTA ───────────────────────────── */
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
  background: linear-gradient(180deg, #E8C860 0%, #C9A84C 40%, #8B7329 100%) !important;
  border: 2px solid #E8D5A3 !important;
  color: #120e06 !important;
  font-weight: 800 !important;
  font-family: 'IBM Plex Mono', monospace !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase;
  font-size: 0.8rem !important;
  border-radius: 0 !important;
  box-shadow:
    0 1px 0 rgba(255,255,255,0.3) inset,
    0 -2px 0 rgba(0,0,0,0.3) inset,
    0 0 16px rgba(201,168,76,0.2),
    0 4px 12px rgba(0,0,0,0.4);
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
  filter: brightness(1.08);
  box-shadow: 0 0 0 1px #F0C14B, 0 0 18px rgba(240,193,75,0.35);
}
.stButton > button[kind="secondary"],
.stButton > button {
  border-radius: 0 !important;
  border: 1px solid rgba(201,168,76,0.45) !important;
  background: linear-gradient(180deg, rgba(32,26,16,0.98), rgba(10,12,16,0.98)) !important;
  color: #e8e0cc !important;
  font-family: 'IBM Plex Mono', monospace !important;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-size: 0.78rem !important;
  box-shadow: inset 0 1px 0 rgba(232,213,163,0.08);
}
.stButton > button:hover {
  border-color: rgba(240, 193, 75, 0.85) !important;
  color: #F0C14B !important;
}

/* ── Metrics — amber CRT quote tiles ──────────────────────────────────── */
[data-testid="stMetric"] {
  background:
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(0,0,0,0.15) 2px,
      rgba(0,0,0,0.15) 3px
    ),
    linear-gradient(180deg, #0a1208 0%, #060a08 100%);
  border: 2px solid rgba(240, 193, 75, 0.4);
  border-radius: 0;
  padding: 0.55rem 0.75rem;
  box-shadow:
    inset 0 0 24px rgba(240,193,75,0.06),
    inset 0 0 0 1px rgba(0,0,0,0.6),
    0 0 12px rgba(240,193,75,0.08),
    0 4px 14px rgba(0,0,0,0.45);
}
[data-testid="stMetricLabel"] {
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: 0.68rem !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase !important;
  color: #7a9070 !important;
}
[data-testid="stMetricValue"] {
  font-family: 'IBM Plex Mono', monospace !important;
  color: #F0C14B !important;
  text-shadow: 0 0 14px rgba(240,193,75,0.45), 0 0 2px rgba(240,193,75,0.8);
  font-weight: 700 !important;
  letter-spacing: 0.04em;
}
[data-testid="stMetricDelta"] {
  font-family: 'IBM Plex Mono', monospace !important;
}

/* ── Tabs — quote board selectors ─────────────────────────────────────── */
button[data-baseweb="tab"] {
  font-family: 'IBM Plex Mono', monospace !important;
  font-weight: 600 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: #8a8478 !important;
  border-bottom: 2px solid transparent !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
  color: #F0C14B !important;
  border-bottom-color: #C9A84C !important;
  text-shadow: 0 0 10px rgba(240,193,75,0.3);
}
[data-baseweb="tab-list"] {
  border-bottom: 1px solid rgba(201,168,76,0.22) !important;
  gap: 0.15rem;
  background: linear-gradient(180deg, rgba(20,16,10,0.6), transparent);
  padding: 0.15rem 0.15rem 0;
}

/* ── Inputs — order ticket fields ─────────────────────────────────────── */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"],
.stNumberInput input, .stDateInput input {
  background: rgba(6, 10, 14, 0.96) !important;
  border-color: rgba(201, 168, 76, 0.28) !important;
  color: #e8e4d8 !important;
  font-family: 'IBM Plex Mono', monospace !important;
  border-radius: 2px !important;
  box-shadow: inset 0 2px 6px rgba(0,0,0,0.35);
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: #C9A84C !important;
  box-shadow: 0 0 0 1px rgba(201,168,76,0.35), inset 0 2px 6px rgba(0,0,0,0.35) !important;
}

/* ── Dataframes — blotter sheets ──────────────────────────────────────── */
[data-testid="stDataFrame"] {
  border: 1px solid rgba(201, 168, 76, 0.22);
  border-radius: 2px;
  overflow: hidden;
  box-shadow: 0 0 0 1px rgba(0,0,0,0.4);
}

/* ═══════════════════════════════════════════════════════════════════════
   FLOOR TAPE — classic stock-exchange LED ticker board
   ═══════════════════════════════════════════════════════════════════════ */
/* Success / warning / error — pit status lights */
div[data-testid="stAlert"] {
  border-radius: 0 !important;
  border-left-width: 5px !important;
  font-family: 'IBM Plex Mono', monospace !important;
  box-shadow: 0 4px 16px rgba(0,0,0,0.35);
}

/* Progress bars — amber fill like old quote boards */
[data-testid="stProgress"] > div > div {
  background: linear-gradient(90deg, #8B7329, #F0C14B) !important;
}

/* Checkboxes / radio in main — ticket style */
[data-testid="stCheckbox"] label,
[data-testid="stRadio"] label {
  font-family: 'IBM Plex Mono', monospace !important;
  letter-spacing: 0.02em;
}

.ws-tape-wrap {
  margin: 0 0 1.1rem 0;
  border: 2px solid #C9A84C;
  border-radius: 2px;
  background: #050806;
  box-shadow:
    0 0 0 1px rgba(0,0,0,0.8),
    inset 0 0 30px rgba(0,0,0,0.8),
    0 6px 24px rgba(0,0,0,0.5);
  overflow: hidden;
  position: relative;
}
.ws-tape-wrap::before {
  content: "";
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0,0,0,0.12) 2px,
    rgba(0,0,0,0.12) 3px
  );
  pointer-events: none;
  z-index: 2;
}
.ws-tape-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.28rem 0.75rem;
  background: linear-gradient(180deg, #2a2418 0%, #1a160e 100%);
  border-bottom: 1px solid rgba(201,168,76,0.45);
  font-family: 'Cinzel', serif;
  font-size: 0.62rem;
  font-weight: 600;
  letter-spacing: 0.2em;
  color: #C9A84C;
  text-transform: uppercase;
}
.ws-tape-head .live-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #3d9e5a;
  box-shadow: 0 0 8px #3d9e5a;
  margin-right: 0.4rem;
  animation: ws-pulse 1.6s ease-in-out infinite;
}
@keyframes ws-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}
.ws-tape {
  display: flex;
  flex-wrap: nowrap;
  gap: 0;
  align-items: center;
  padding: 0.55rem 0;
  overflow: hidden;
  white-space: nowrap;
  position: relative;
  z-index: 1;
}
.ws-tape-track {
  display: inline-flex;
  align-items: center;
  gap: 1.5rem;
  padding: 0 1.25rem;
  animation: ws-marquee 42s linear infinite;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.82rem;
  letter-spacing: 0.06em;
  color: #F0C14B;
  text-shadow: 0 0 8px rgba(240,193,75,0.35);
}
.ws-tape-track:hover {
  animation-play-state: paused;
}
@keyframes ws-marquee {
  0%   { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}
.ws-tape .bull { color: #7dcea0; font-weight: 600; text-shadow: 0 0 8px rgba(125,206,160,0.35); }
.ws-tape .bear { color: #e07a7a; font-weight: 600; text-shadow: 0 0 8px rgba(224,122,122,0.3); }
.ws-tape .sym  { color: #fff8e0; font-weight: 700; letter-spacing: 0.1em; }
.ws-tape .sep  { opacity: 0.45; color: #C9A84C; margin: 0 0.15rem; }
.ws-tape .label { color: #8a8478; font-size: 0.72rem; letter-spacing: 0.12em; }

/* ═══════════════════════════════════════════════════════════════════════
   BRASS NAMEPLATE — page hero (firm letterhead)
   ═══════════════════════════════════════════════════════════════════════ */
.ws-page-hero {
  position: relative;
  padding: 1.05rem 1.25rem 0.9rem 1.25rem;
  margin-bottom: 1.15rem;
  background:
    linear-gradient(145deg,
      rgba(40,32,16,0.99) 0%,
      rgba(14,16,20,0.99) 48%,
      rgba(8,10,12,0.99) 100%);
  border: 3px double #C9A84C;
  border-radius: 0;
  box-shadow:
    inset 0 1px 0 rgba(232,213,163,0.2),
    inset 0 -1px 0 rgba(0,0,0,0.35),
    0 0 0 1px rgba(0,0,0,0.6),
    0 10px 32px rgba(0,0,0,0.5);
}
/* Brass corner rivets */
.ws-page-hero::before,
.ws-page-hero::after {
  content: "";
  position: absolute;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, #E8D5A3, #C9A84C 45%, #7a6420 100%);
  box-shadow: 0 1px 2px rgba(0,0,0,0.5);
}
.ws-page-hero::before { top: 8px; left: 8px; }
.ws-page-hero::after  { top: 8px; right: 8px; }
.ws-page-hero .rivet-bl,
.ws-page-hero .rivet-br {
  position: absolute;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, #E8D5A3, #C9A84C 45%, #7a6420 100%);
  box-shadow: 0 1px 2px rgba(0,0,0,0.5);
  bottom: 8px;
}
.ws-page-hero .rivet-bl { left: 8px; }
.ws-page-hero .rivet-br { right: 8px; }

.ws-page-hero.bear-edge {
  border-color: #8B9BB4;
  box-shadow:
    inset 0 1px 0 rgba(197,208,224,0.12),
    0 0 0 1px rgba(0,0,0,0.6),
    0 10px 32px rgba(0,0,0,0.5);
}
.ws-page-hero h1 {
  margin: 0 0 0.35rem 0 !important;
  border: none !important;
  padding: 0 !important;
  font-size: 1.5rem !important;
  display: flex;
  align-items: center;
  gap: 0.55rem;
  color: #f4efe0 !important;
  font-family: 'Cinzel', 'Times New Roman', serif !important;
  letter-spacing: 0.06em !important;
}
.ws-page-hero .sub {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.8rem;
  color: #a8a090;
  margin: 0;
  line-height: 1.5;
  letter-spacing: 0.02em;
}
.ws-page-hero .desk-tag {
  display: inline-block;
  font-family: 'Cinzel', serif;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #C9A84C;
  margin-bottom: 0.4rem;
  padding: 0.15rem 0.55rem;
  border: 1px solid rgba(201,168,76,0.4);
  background: rgba(201,168,76,0.08);
}
.ws-candle-mark {
  display: inline-block;
  width: 0.55rem;
  height: 1.15rem;
  margin-right: 0.15rem;
  vertical-align: middle;
  border-radius: 1px;
  position: relative;
  flex-shrink: 0;
}
.ws-candle-mark.bull {
  background: #C9A84C;
  box-shadow: 0 -5px 0 0 #C9A84C, 0 5px 0 0 #C9A84C, 0 0 8px rgba(201,168,76,0.4);
}
.ws-candle-mark.bear {
  background: #8B9BB4;
  box-shadow: 0 -5px 0 0 #8B9BB4, 0 5px 0 0 #8B9BB4;
}

/* ── Section rail — engraved brass divider ────────────────────────────── */
.ws-section {
  font-family: 'Cinzel', serif;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #C9A84C;
  border-bottom: 2px solid rgba(201,168,76,0.28);
  padding: 0.15rem 0 0.4rem 0;
  margin: 1.35rem 0 0.85rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.ws-section::after {
  content: "";
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(201,168,76,0.45), transparent 90%);
  margin-left: 0.35rem;
}
.ws-section .bull { color: #C9A84C; }
.ws-section .bear { color: #8B9BB4; }

/* ── Quote board frame (charts / live panels) ─────────────────────────── */
.ws-quote-board {
  position: relative;
  margin: 0.35rem 0 0.75rem 0;
  padding: 0.65rem 0.75rem 0.75rem;
  background:
    linear-gradient(180deg, #0a0e08 0%, #060a0e 100%);
  border: 2px solid #C9A84C;
  border-radius: 2px;
  box-shadow:
    inset 0 0 40px rgba(0,0,0,0.55),
    0 0 0 1px rgba(0,0,0,0.7),
    0 8px 28px rgba(0,0,0,0.45);
}
.ws-quote-board .qb-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid rgba(201,168,76,0.28);
  font-family: 'Cinzel', serif;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  color: #C9A84C;
  text-transform: uppercase;
}
.ws-quote-board .qb-head .qb-live {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  color: #7dcea0;
}
.ws-quote-board .qb-head .qb-live::before {
  content: "● ";
  animation: ws-pulse 1.6s ease-in-out infinite;
}

/* ── Links — brand gold ───────────────────────────────────────────────── */
a { color: #D4AF37 !important; }
a:hover { color: #E8D5A3 !important; }

/* ── Divider — brass hairline ─────────────────────────────────────────── */
hr {
  border: none !important;
  border-top: 1px solid rgba(201, 168, 76, 0.22) !important;
  background: linear-gradient(90deg, transparent, rgba(201,168,76,0.35), transparent) !important;
  height: 1px !important;
}

/* ── Auth / landing — membership plaque ───────────────────────────────── */
[data-testid="stForm"] {
  background: linear-gradient(180deg, rgba(28,24,16,0.92), rgba(12,16,24,0.95));
  border: 2px solid rgba(201, 168, 76, 0.35);
  border-radius: 2px;
  padding: 0.85rem 1.1rem 1.1rem 1.1rem;
  box-shadow:
    inset 0 1px 0 rgba(232,213,163,0.1),
    0 8px 28px rgba(0,0,0,0.4);
}

/* Progress / sliders — brass */
[data-testid="stProgress"] > div > div {
  background-color: #C9A84C !important;
}
div[data-baseweb="slider"] div[role="slider"] {
  background-color: #C9A84C !important;
}

/* Download buttons sit like desk forms */
[data-testid="stDownloadButton"] > button {
  border-radius: 2px !important;
  border: 1px solid rgba(201,168,76,0.4) !important;
  font-family: 'IBM Plex Mono', monospace !important;
}

/* Alerts — firm notices */
[data-testid="stAlert"] {
  border-radius: 2px !important;
  border-left-width: 4px !important;
}

/* Images — framed like wall charts */
[data-testid="stImage"] {
  border: 1px solid rgba(201,168,76,0.25);
  border-radius: 2px;
  padding: 3px;
  background: rgba(0,0,0,0.35);
  box-shadow: 0 4px 16px rgba(0,0,0,0.35);
}
</style>
"""

# Colors expanders from emoji prefixes (runs in parent via components)
_CANDLE_COLORIZER_JS = """
<script>
(function() {
  function paint() {
    try {
      var doc = window.parent && window.parent.document ? window.parent.document : document;
      var nodes = doc.querySelectorAll('[data-testid="stExpander"]');
      nodes.forEach(function(el) {
        var t = (el.innerText || el.textContent || '');
        el.classList.remove('ws-candle-bull', 'ws-candle-bear');
        /* Green / rising panels */
        if (t.indexOf('📈') !== -1 || t.indexOf('🟢') !== -1) {
          el.classList.add('ws-candle-bull');
        /* Red / falling / risk / TV news */
        } else if (t.indexOf('📉') !== -1 || t.indexOf('🔴') !== -1 || t.indexOf('📺') !== -1) {
          el.classList.add('ws-candle-bear');
        /* Document / link panels — soft gold desk edge */
        } else if (t.indexOf('📂') !== -1 || t.indexOf('📁') !== -1 ||
                   t.indexOf('📃') !== -1 || t.indexOf('📄') !== -1 ||
                   t.indexOf('🔗') !== -1) {
          el.classList.add('ws-candle-bull');
        } else {
          var idx = Array.prototype.indexOf.call(nodes, el);
          el.classList.add(idx % 2 === 0 ? 'ws-candle-bull' : 'ws-candle-bear');
        }
      });
    } catch (e) { /* cross-frame may fail in some hosts */ }
  }
  paint();
  setTimeout(paint, 400);
  setTimeout(paint, 1200);
  try {
    var doc = window.parent && window.parent.document ? window.parent.document : document;
    var obs = new MutationObserver(function() { paint(); });
    obs.observe(doc.body, { childList: true, subtree: true });
  } catch (e2) {}
})();
</script>
"""

# Panel icon sets
DOC_ICONS = ("📂", "📁", "📃", "📄")  # rotate for document panels
ICON_UP = "📈"
ICON_DOWN = "📉"
ICON_TV = "📺"
ICON_LINK = "🔗"

# Sidebar nav: page name → lead emoji (mixed, senseful)
NAV_PAGE_ICONS: dict[str, str] = {
    "Session Selector": ICON_UP,
    "Trading Journal": "📃",
    "CPRP Session Statistics": ICON_DOWN,
    "Community": ICON_UP,
    "Member Chat": ICON_UP,
    "Economic Calendar": ICON_DOWN,
    "Bloomberg Live": ICON_TV,
    "Micro Futures News": "📃",
    "Platforms & Brokers": ICON_LINK,
    "Micro E-mini Futures": ICON_UP,
    "Company Branding": "📁",
    "About the Founder": "📄",
    "Admin / Founder": "📂",
}

# All known label prefixes we may strip from nav labels
_EMOJI_PREFIXES = (
    "🟢🕯️ BULL · ",
    "🔴🕯️ BEAR · ",
    "🟢🕯️ ",
    "🔴🕯️ ",
    "🟢 ",
    "🔴 ",
    f"{ICON_UP} ",
    f"{ICON_DOWN} ",
    f"{ICON_TV} ",
    f"{ICON_LINK} ",
    "📂 ",
    "📁 ",
    "📃 ",
    "📄 ",
    "📊 ",
    "💬 ",
    "📅 ",
)


def inject_wallstreet_theme() -> None:
    """Inject global retro day-trader floor CSS + candle expander colorizer once per run."""
    st.markdown(WS_CSS, unsafe_allow_html=True)
    # Tiny zero-height component so JS can reach parent DOM expanders
    components.html(_CANDLE_COLORIZER_JS, height=0)


def doc_icon_for(text: str) -> str:
    """Pick a document emoji (folder/page mix) from the title for variety."""
    if not text:
        return DOC_ICONS[0]
    return DOC_ICONS[sum(ord(c) for c in text) % len(DOC_ICONS)]


def link_label(text: str) -> str:
    """Prefix a link button / external action with the link emoji."""
    t = text.strip()
    if t.startswith(ICON_LINK):
        return t
    return f"{ICON_LINK} {t}"


def market_tape(
    *,
    protocol: str = "CPRP",
    version: str = "1.6",
    instruments: str = "MES · MNQ · MYM",
    risk: str = "−$50 / −$100",
) -> None:
    """Top-of-page stock-exchange LED ticker board (scrolling floor tape)."""
    # Duplicate track for seamless marquee loop
    segment = f"""
  <span class="sym">{protocol} STRATEGIES</span><span class="sep">◆</span>
  <span class="label">DAY TRADER DESK</span><span class="sep">◆</span>
  <span class="label">RULEBOOK</span> <span class="bull">v{version}</span><span class="sep">◆</span>
  <span class="sym">{instruments}</span><span class="sep">◆</span>
  <span class="label">HARD RISK</span> <span class="bear">{risk}</span><span class="sep">◆</span>
  <span class="label">PRIMARY</span> <span class="bull">RANGE REVERSION</span><span class="sep">◆</span>
  <span class="label">SECONDARY</span> <span class="sym">SCALPING</span><span class="sep">◆</span>
  <span class="label">MICROS ONLY</span><span class="sep">◆</span>
  <span class="label">FLOOR OPEN</span> <span class="bull">LIVE</span><span class="sep">◆</span>
"""
    st.markdown(
        f"""
<div class="ws-tape-wrap">
  <div class="ws-tape-head">
    <span><span class="live-dot"></span>NYSE-STYLE FLOOR TAPE · DAY TRADER DESK</span>
    <span>CPRP STRATEGIES · MICRO E-MINI FUTURES</span>
  </div>
  <div class="ws-tape">
    <div class="ws-tape-track">
      {segment}
      {segment}
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def page_hero(
    title: str,
    subtitle: str = "",
    *,
    side: CandleSide = "bull",
    desk_tag: str = "CPRP DAY TRADER DESK",
) -> None:
    """Brass nameplate page header — retro exchange-floor letterhead."""
    edge = "bear-edge" if side == "bear" else ""
    mark = "bear" if side == "bear" else "bull"
    sub_html = f'<p class="sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
<div class="ws-page-hero {edge}">
  <span class="rivet-bl"></span>
  <span class="rivet-br"></span>
  <div class="desk-tag">{desk_tag}</div>
  <h1><span class="ws-candle-mark {mark}"></span>{title}</h1>
  {sub_html}
</div>
""",
        unsafe_allow_html=True,
    )


def desk_section(title: str, *, side: CandleSide = "bull") -> None:
    """Engraved brass section rail between panels."""
    cls = "bull" if side == "bull" else "bear"
    glyph = "▲" if side == "bull" else "▼"
    st.markdown(
        f'<div class="ws-section"><span class="{cls}">{glyph}</span> {title}</div>',
        unsafe_allow_html=True,
    )


def quote_board_header(title: str = "Quote Board · Live", live_label: str = "LIVE") -> None:
    """
    Classic exchange quote-board plaque (header strip).

    Streamlit cannot wrap widgets inside raw HTML, so this is a matching
    brass header; pair with quote_board_footer() below the content.
    """
    st.markdown(
        f"""
<div class="ws-quote-board" style="margin-bottom:0;border-bottom:none;border-radius:2px 2px 0 0;">
  <div class="qb-head" style="margin-bottom:0;padding-bottom:0;border-bottom:none;">
    <span>{title}</span>
    <span class="qb-live">{live_label}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def quote_board_footer(note: str = "CME / CBOT continuous · TradingView feed · Desk display only") -> None:
    """Brass footer strip under a quote-board content block."""
    st.markdown(
        f"""
<div class="ws-quote-board" style="margin-top:0;border-top:1px solid rgba(201,168,76,0.35);
     border-radius:0 0 2px 2px;padding:0.4rem 0.75rem;">
  <div style="font-family:'IBM Plex Mono',monospace;font-size:0.65rem;letter-spacing:0.08em;
       color:#8a8478;text-align:right;">{note}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def candle_label(
    text: str,
    *,
    side: CandleSide = "bull",
    kind: str | None = None,
    icon: str | None = None,
) -> str:
    """
    Label for nav / expanders with senseful emoji prefixes.

    side bull → 📈  ·  side bear → 📉
    kind: 'doc' | 'folder' | 'page' | 'tv' | 'link' | 'up' | 'down' (overrides default)
    icon: explicit emoji override
    """
    t = text.strip()
    if icon:
        lead = icon
    elif kind in ("doc", "document", "folder", "page"):
        if kind == "folder":
            lead = "📁"
        elif kind == "page":
            lead = "📄"
        else:
            lead = doc_icon_for(t)
    elif kind == "tv":
        lead = ICON_TV
    elif kind == "link":
        lead = ICON_LINK
    elif kind == "up":
        lead = ICON_UP
    elif kind == "down":
        lead = ICON_DOWN
    elif side == "bull":
        lead = ICON_UP
    else:
        lead = ICON_DOWN
    # Avoid double-prefix if caller already added the emoji
    if t.startswith(lead):
        return t
    return f"{lead} {t}"


def candle_expander(
    title: str,
    *,
    side: CandleSide = "bull",
    expanded: bool = False,
    kind: str | None = None,
    icon: str | None = None,
):
    """
    Expander panel with emoji control:
    - Green/up panels → 📈
    - Red/down panels → 📉
    - Documents → 📂 📁 📃 📄 (kind='doc')
    - Bloomberg / video → 📺 (kind='tv')
    - External links → 🔗 (kind='link')
    """
    label = candle_label(title, side=side, kind=kind, icon=icon)
    return st.expander(label, expanded=expanded)


def nav_candle_pages(pages: list[str]) -> list[str]:
    """Prefix nav page names with tab-appropriate emojis."""
    out = []
    for i, name in enumerate(pages):
        icon = NAV_PAGE_ICONS.get(name)
        if icon is None:
            icon = ICON_UP if i % 2 == 0 else ICON_DOWN
        out.append(f"{icon} {name}")
    return out


def strip_candle_prefix(label: str) -> str:
    """Map emoji-prefixed nav label back to clean page name."""
    s = label
    # Strip repeatedly in case of stacked prefixes from older sessions
    for _ in range(3):
        stripped = False
        for prefix in _EMOJI_PREFIXES:
            if s.startswith(prefix):
                s = s[len(prefix) :]
                stripped = True
                break
        if not stripped:
            break
    return s
