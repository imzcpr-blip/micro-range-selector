"""Dark, modern Wall Street desk theme for the CPRP Micro Selector."""

from __future__ import annotations

import html

import streamlit as st

DESK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

:root {
  --navy: #070b12;
  --navy-2: #0b1220;
  --panel: #0e1624;
  --panel-2: #121c2e;
  --line: rgba(201,168,76,0.28);
  --line-dim: rgba(148,163,184,0.14);
  --gold: #C9A84C;
  --gold-hi: #E8D5A3;
  --ink: #E8EEF6;
  --muted: #8B97A8;
  --green: #3DDC97;
  --red: #FF5C6A;
  --amber: #F0C14B;
}

html, body, [data-testid="stAppViewContainer"], .stApp {
  background:
    linear-gradient(180deg, rgba(201,168,76,0.04) 0px, transparent 90px),
    radial-gradient(900px 420px at 0% -8%, rgba(201,168,76,0.07), transparent 55%),
    radial-gradient(800px 500px at 100% 0%, rgba(16,48,90,0.35), transparent 50%),
    var(--navy) !important;
  color: var(--ink) !important;
  font-family: 'IBM Plex Sans', system-ui, sans-serif !important;
}
[data-testid="stHeader"] {
  background: var(--navy) !important;
  border-bottom: 1px solid var(--line) !important;
}
[data-testid="stToolbar"], [data-testid="stDecoration"] { display: none; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.block-container {
  padding-top: 1.05rem !important;
  padding-bottom: 2.2rem !important;
  max-width: 1280px !important;
}
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0c1422 0%, #080e18 100%) !important;
  border-right: 1px solid var(--line) !important;
}
[data-testid="stSidebar"] * { font-size: 0.90rem; }
[data-testid="stSidebar"] [data-testid="stMarkdown"] p { color: var(--muted); }

.stButton > button {
  font-family: 'IBM Plex Mono', monospace !important;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  font-weight: 600 !important;
  font-size: 0.78rem !important;
  border-radius: 2px !important;
  border: 1px solid var(--line) !important;
  background: #121c2e !important;
  color: var(--gold-hi) !important;
  height: 2.55rem;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
  background: linear-gradient(180deg, #D4B45A, #B8943A) !important;
  color: #0A0E14 !important;
  border: 1px solid #E8D5A3 !important;
  box-shadow: 0 0 0 1px rgba(201,168,76,0.25), 0 8px 22px rgba(0,0,0,0.35);
}
.stDownloadButton > button {
  font-family: 'IBM Plex Mono', monospace !important;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 0.74rem !important;
  border-radius: 2px !important;
  border: 1px solid var(--line) !important;
  background: #121c2e !important;
  color: var(--gold-hi) !important;
}
div[data-testid="stMetric"] {
  background: var(--panel);
  border: 1px solid var(--line-dim);
  border-top: 2px solid var(--gold);
  padding: 0.7rem 0.8rem 0.55rem;
}
[data-testid="stMetricLabel"] {
  font-family: 'IBM Plex Mono', monospace !important;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-size: 0.68rem !important;
  color: var(--muted) !important;
}
[data-testid="stMetricValue"] {
  font-family: 'IBM Plex Mono', monospace !important;
  color: var(--gold-hi) !important;
  font-size: 1.35rem !important;
}
[data-testid="stExpander"] {
  background: var(--panel) !important;
  border: 1px solid var(--line-dim) !important;
  border-radius: 2px !important;
}
[data-testid="stExpander"] summary {
  font-family: 'IBM Plex Mono', monospace !important;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 0.78rem !important;
  color: var(--gold-hi) !important;
}
.stDataFrame, [data-testid="stDataFrame"] {
  font-family: 'IBM Plex Mono', monospace !important;
  border: 1px solid var(--line-dim);
}
textarea, .stTextInput input, .stNumberInput input {
  background: #0A101A !important;
  color: var(--ink) !important;
  border-radius: 2px !important;
}

/* ── Desk chrome ─────────────────────────────────────────── */
.tape {
  display: flex; align-items: center; justify-content: space-between;
  gap: 0.8rem; flex-wrap: wrap;
  border: 1px solid var(--line);
  background: linear-gradient(90deg, #10182a, #0c1422 40%, #10182a);
  padding: 0.42rem 0.85rem;
  margin-bottom: 0.85rem;
}
.tape-left, .tape-right {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--gold);
}
.tape-right { color: var(--muted); letter-spacing: 0.10em; }
.pulse {
  display: inline-block; width: 7px; height: 7px; border-radius: 50%;
  background: var(--green); margin-right: 0.45rem;
  box-shadow: 0 0 8px var(--green);
}

.mast {
  display: flex; align-items: flex-end; justify-content: space-between;
  gap: 1rem; flex-wrap: wrap;
  margin-bottom: 0.85rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--line-dim);
}
.mast h1 {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 1.55rem; font-weight: 600;
  color: var(--ink); margin: 0.12rem 0 0.18rem; letter-spacing: 0.01em;
}
.kicker {
  font-family: 'IBM Plex Mono', monospace;
  letter-spacing: 0.18em; font-size: 0.68rem;
  color: var(--gold); text-transform: uppercase; margin: 0;
}
.tagline { color: var(--muted); font-size: 0.92rem; margin: 0; }

.sec {
  font-family: 'IBM Plex Mono', monospace;
  letter-spacing: 0.16em; font-size: 0.72rem;
  color: var(--gold); text-transform: uppercase;
  margin: 1.15rem 0 0.55rem;
  padding-bottom: 0.28rem;
  border-bottom: 1px solid var(--line);
}

.pick-board {
  display: grid;
  grid-template-columns: 1.35fr 0.85fr;
  gap: 0;
  border: 1px solid var(--line);
  background:
    linear-gradient(180deg, rgba(201,168,76,0.07), transparent 42%),
    var(--panel);
  box-shadow: 0 16px 40px rgba(0,0,0,0.35);
}
.pick-board.warn { border-color: rgba(255,92,106,0.55); }
.pick-board.demo { border-color: rgba(91,111,136,0.7); }
.pick-main { padding: 1.25rem 1.35rem 1.15rem; }
.pick-conf {
  padding: 1.25rem 1.2rem;
  border-left: 1px solid var(--line);
  background: rgba(0,0,0,0.18);
  display: flex; flex-direction: column; justify-content: center;
}
.pick-symbol {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 3.35rem; font-weight: 700; line-height: 0.92;
  color: var(--ink); letter-spacing: 0.06em;
}
.pick-name { color: var(--gold); font-size: 0.98rem; margin-top: 0.35rem; }
.pick-why {
  color: #c9d3e0; font-size: 0.98rem; line-height: 1.5;
  margin: 0.95rem 0 0; max-width: 52rem;
}
.conf-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.68rem; letter-spacing: 0.16em;
  color: var(--muted); text-transform: uppercase;
}
.conf-num {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 2.4rem; font-weight: 600; color: var(--green); line-height: 1.05;
  margin: 0.15rem 0 0.45rem;
}
.conf-num.low { color: var(--red); }
.conf-bar { height: 4px; background: #1c2a40; width: 100%; }
.conf-bar > div { height: 4px; background: var(--gold); }
.chips { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.75rem; }
.chip {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.66rem; letter-spacing: 0.08em;
  border: 1px solid var(--line-dim);
  padding: 0.18rem 0.5rem; color: #c5cdd8; background: #0a101a;
  text-transform: uppercase;
}
.chip.gold { border-color: var(--gold); color: var(--gold); }
.chip.red { border-color: var(--red); color: var(--red); }
.chip.green { border-color: var(--green); color: var(--green); }

.books {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.7rem;
  margin: 0.2rem 0 0.85rem;
}
.book {
  background: var(--panel);
  border: 1px solid var(--line-dim);
  padding: 0.85rem 0.95rem 0.8rem;
  min-height: 132px;
}
.book.pick {
  border: 1px solid var(--gold);
  box-shadow: inset 0 2px 0 var(--gold);
}
.book .sym {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 1.15rem; font-weight: 600; color: var(--ink);
  display: flex; justify-content: space-between; align-items: baseline;
}
.book .score {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 1.55rem; color: var(--gold-hi); font-weight: 600;
}
.book .meta {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.72rem; color: var(--muted); margin-top: 0.35rem;
  letter-spacing: 0.04em;
}
.book .row {
  display: flex; justify-content: space-between;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.72rem; color: #b7c0cc; margin-top: 0.22rem;
}
.book .flag {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.64rem; letter-spacing: 0.12em; color: var(--gold);
  text-transform: uppercase; margin-top: 0.45rem;
}

.ticket {
  border: 1px solid var(--line);
  background: var(--panel);
  font-family: 'IBM Plex Mono', monospace;
}
.ticket-h {
  display: flex; justify-content: space-between;
  padding: 0.45rem 0.85rem;
  background: linear-gradient(90deg, #16120a, #0e1624);
  border-bottom: 1px solid var(--line);
  letter-spacing: 0.14em; font-size: 0.7rem;
  text-transform: uppercase; color: var(--gold);
}
.ticket-b { padding: 0.55rem 0.85rem 0.7rem; }
.ticket-b .tr {
  display: grid; grid-template-columns: 9.5rem 1fr;
  gap: 0.4rem; padding: 0.28rem 0;
  border-bottom: 1px dashed var(--line-dim);
  font-size: 0.82rem; color: #d5dde8;
}
.ticket-b .tr span:first-child { color: var(--muted); letter-spacing: 0.08em; text-transform: uppercase; font-size: 0.7rem; }
.ticket-note { color: var(--gold-hi); padding-top: 0.55rem; font-size: 0.8rem; line-height: 1.45; }
.ticket-note.warn { color: var(--red); }

.footer-desk {
  color: var(--muted); font-size: 0.75rem; line-height: 1.5;
  margin-top: 1.6rem; padding-top: 0.85rem;
  border-top: 1px solid var(--line);
}
.side-brand {
  border: 1px solid var(--line);
  background: linear-gradient(180deg, #16120a, #0c1422);
  padding: 0.7rem 0.75rem 0.65rem;
  margin-bottom: 0.85rem;
}
.side-brand .kicker { margin-bottom: 0.15rem; }
.side-brand h2 {
  font-size: 1.02rem; margin: 0; color: var(--ink); font-weight: 600;
}
.side-brand p { color: var(--muted); font-size: 0.78rem; margin: 0.35rem 0 0; line-height: 1.4; }

@media (max-width: 900px) {
  .pick-board { grid-template-columns: 1fr; }
  .pick-conf { border-left: none; border-top: 1px solid var(--line); }
  .books { grid-template-columns: 1fr; }
  .pick-symbol { font-size: 2.4rem; }
}
</style>
"""


def inject() -> None:
    st.markdown(DESK_CSS, unsafe_allow_html=True)


def tape(clock, extras: str = "") -> None:
    right = f"{clock.target_rth.strftime('%a %d %b %Y')}  ·  {clock.phase.replace('_', ' ')}  ·  {clock.now.strftime('%H:%M ET')}"
    if extras:
        right += f"  ·  {extras}"
    st.markdown(
        f"""<div class="tape">
          <div class="tape-left"><span class="pulse"></span>CPRP desk  ·  micro equity index  ·  RTH focus</div>
          <div class="tape-right">{html.escape(right)}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def masthead(protocol: str, app_name: str, tagline: str) -> None:
    st.markdown(
        f"""<div class="mast">
          <div>
            <p class="kicker">{html.escape(protocol)}  ·  micros only  ·  −$50 to −$100</p>
            <h1>{html.escape(app_name)}</h1>
            <p class="tagline">{html.escape(tagline)}</p>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )


def section(label: str) -> None:
    st.markdown(f'<div class="sec">{html.escape(label)}</div>', unsafe_allow_html=True)


def pick_board(
    *,
    pick: str,
    name: str,
    session_date: str,
    as_of: str,
    confidence: int,
    summary: str,
    chips: list[str],
    sit_out: bool,
    demo: bool,
) -> None:
    cls = "pick-board"
    if sit_out:
        cls += " warn"
    if demo:
        cls += " demo"
    conf_cls = "conf-num low" if confidence < 55 else "conf-num"
    st.markdown(
        f"""<div class="{cls}">
          <div class="pick-main">
            <p class="kicker">Session focus  ·  {html.escape(session_date)}  ·  {html.escape(as_of)}</p>
            <div class="pick-symbol">{html.escape(pick)}</div>
            <div class="pick-name">{html.escape(name)}</div>
            <div class="chips">{''.join(chips)}</div>
            <p class="pick-why">{html.escape(summary)}</p>
          </div>
          <div class="pick-conf">
            <div class="conf-label">Confidence</div>
            <div class="{conf_cls}">{confidence}<span style="font-size:1rem;color:#8B97A8"> / 100</span></div>
            <div class="conf-bar"><div style="width:{int(confidence)}%"></div></div>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )


def chip(text: str, kind: str = "") -> str:
    cls = f"chip {kind}".strip()
    return f'<span class="{cls}">{html.escape(text)}</span>'


def book_cards(scores, pick: str) -> None:
    tiles = []
    for s in scores:
        by = {f.key: f.raw for f in s.factors}
        cls = "book pick" if s.short == pick else "book"
        flag = "Focus book" if s.short == pick else s.grade
        tiles.append(
            f"""<div class="{cls}">
              <div class="sym"><span>{html.escape(s.short)}</span><span class="score">{s.composite:.1f}</span></div>
              <div class="meta">{html.escape(s.name)}  ·  {s.grade}</div>
              <div class="row"><span>Clean</span><span>{by.get('cleanliness', 0):.0f}</span></div>
              <div class="row"><span>Potential</span><span>{by.get('profit_potential', 0):.0f}</span></div>
              <div class="row"><span>Last</span><span>{s.metrics.last_price:,.2f}</span></div>
              <div class="flag">{html.escape(flag)}</div>
            </div>"""
        )
    st.markdown(f'<div class="books">{"".join(tiles)}</div>', unsafe_allow_html=True)


def risk_ticket(rows: list[tuple[str, str]], note: str, warn: bool = False) -> None:
    body = "".join(
        f'<div class="tr"><span>{html.escape(k)}</span><span>{html.escape(v)}</span></div>'
        for k, v in rows
    )
    note_cls = "ticket-note warn" if warn else "ticket-note"
    st.markdown(
        f"""<div class="ticket">
          <div class="ticket-h"><span>Risk ticket</span><span>Hard stop  −$50 to −$100</span></div>
          <div class="ticket-b">{body}<div class="{note_cls}">{html.escape(note)}</div></div>
        </div>""",
        unsafe_allow_html=True,
    )


def sidebar_brand(short: str, version: str, app_name: str, note: str) -> None:
    st.markdown(
        f"""<div class="side-brand">
          <p class="kicker">{html.escape(short)}  ·  v{html.escape(version)}</p>
          <h2>{html.escape(app_name)}</h2>
          <p>{html.escape(note)}</p>
        </div>""",
        unsafe_allow_html=True,
    )


def footer(protocol: str, short: str, version: str, creator: str) -> None:
    st.markdown(
        f"""<div class="footer-desk">
          {html.escape(protocol)} ({html.escape(short)})  ·  Rulebook {html.escape(version)}  ·  {html.escape(creator)}<br>
          Not personalized financial, investment, or trading advice. You own your decisions, risk, and results.
          Futures trading involves substantial risk of loss. Yahoo data is delayed and is not CME order flow.
        </div>""",
        unsafe_allow_html=True,
    )
