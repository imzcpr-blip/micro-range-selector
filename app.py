"""CPRP Micro Selector — single-page Streamlit desk.

Run:
    python -m streamlit run app.py
"""

from __future__ import annotations

import copy
import json
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from selector.config import (
    APP_NAME,
    APP_TAGLINE,
    CREATOR,
    DEFAULT_WEIGHTS,
    ET_TZ,
    HARD_STOP_DEFAULT_USD,
    HARD_STOP_MAX_USD,
    HARD_STOP_MIN_USD,
    INSTRUMENTS,
    MES_BIAS_POINTS,
    MIN_SCORE_TO_TRADE,
    ORDERED_BOOKS,
    PROTOCOL_NAME,
    PROTOCOL_SHORT,
    RULEBOOK_VERSION,
    SWITCH_MARGIN,
    WEIGHT_HELP,
    WEIGHT_LABELS,
)
from selector.history import historical_picks, log_recommendation, rec_to_markdown
from selector.models import UserOverlays
from selector.providers import SCENARIOS, load_market_bundle, session_clock
from selector.providers.base import apply_overlays
from selector.risk_calc import plan, sizing_notes, suggested_stop_pts, usd_for_stop_pts
from selector.scoring import analyze_session

ET = ZoneInfo(ET_TZ)

st.set_page_config(
    page_title=APP_NAME,
    page_icon="▣",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
  background: #0A0C10 !important;
  color: #E8E0CC !important;
  font-family: 'IBM Plex Sans', system-ui, sans-serif !important;
}
[data-testid="stHeader"] { background: #0A0C10 !important; }
[data-testid="stSidebar"] {
  background: #0d1117 !important;
  border-right: 1px solid #2a2418 !important;
}
[data-testid="stSidebar"] * { font-size: 0.92rem; }

.hero {
  border: 1px solid #3a3120;
  background: linear-gradient(180deg, #16120c 0%, #0e1014 100%);
  padding: 1.25rem 1.4rem 1.1rem;
  margin-bottom: 0.85rem;
}
.kicker {
  font-family: 'IBM Plex Mono', monospace;
  letter-spacing: 0.18em;
  font-size: 0.72rem;
  color: #C9A84C;
  text-transform: uppercase;
}
h1.app-title {
  font-size: 1.65rem;
  font-weight: 600;
  margin: 0.15rem 0 0.2rem;
  color: #F3EBD4;
}
.tagline { color: #9aa3b2; font-size: 0.95rem; margin: 0; }

.pick-card {
  border: 1px solid #C9A84C;
  background: linear-gradient(165deg, #1a160e 0%, #0c0e12 55%, #10140f 100%);
  padding: 1.4rem 1.5rem 1.2rem;
  box-shadow: 0 0 0 1px rgba(201,168,76,0.18), 0 12px 40px rgba(0,0,0,0.45);
}
.pick-card.warn { border-color: #c47a3a; }
.pick-card.demo { border-color: #5b6b88; }
.pick-symbol {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 3.1rem;
  font-weight: 600;
  line-height: 1;
  color: #F3EBD4;
  letter-spacing: 0.04em;
}
.pick-name { color: #C9A84C; font-size: 1rem; margin-top: 0.2rem; }
.pick-why { color: #d5d0c4; font-size: 1.02rem; margin-top: 0.85rem; line-height: 1.45; }
.conf-wrap { margin-top: 0.85rem; }
.conf-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  color: #8b93a7;
}
.conf-num { font-family: 'IBM Plex Mono', monospace; font-size: 1.8rem; color: #7dcea0; }
.conf-num.low { color: #e06c75; }
.conf-bar { height: 6px; background: #1c2230; margin-top: 0.35rem; }
.conf-bar > div { height: 6px; background: #C9A84C; }

.meta-row {
  display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.6rem 0 0.9rem;
}
.chip {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  border: 1px solid #2e3544;
  padding: 0.22rem 0.55rem;
  color: #c5cdd8;
  background: #12161c;
}
.chip.gold { border-color: #C9A84C; color: #C9A84C; }
.chip.red { border-color: #e06c75; color: #e06c75; }
.chip.green { border-color: #7dcea0; color: #7dcea0; }

.risk-box {
  border: 1px solid #2a2418;
  background: #12161c;
  padding: 0.9rem 1rem;
  font-size: 0.92rem;
  line-height: 1.5;
}
.risk-box b { color: #C9A84C; }

div[data-testid="stMetric"] {
  background: #12161c;
  border: 1px solid #2a2418;
  padding: 0.6rem 0.75rem;
}
[data-testid="stExpander"] {
  background: #10141a;
  border: 1px solid #242a36;
}
.stDataFrame { font-family: 'IBM Plex Mono', monospace; }

.footer {
  color: #6b7382;
  font-size: 0.8rem;
  margin-top: 1.4rem;
  border-top: 1px solid #242a36;
  padding-top: 0.8rem;
}
@media (max-width: 640px) {
  .pick-symbol { font-size: 2.3rem; }
  h1.app-title { font-size: 1.3rem; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def _clock():
    return session_clock()


def _overlays_from_ui() -> UserOverlays:
    o = UserOverlays()
    for short in ORDERED_BOOKS:
        o.on_high[short] = st.session_state.get(f"on_hi_{short}") or None
        o.on_low[short] = st.session_state.get(f"on_lo_{short}") or None
        o.poc[short] = st.session_state.get(f"poc_{short}") or None
        o.vah[short] = st.session_state.get(f"vah_{short}") or None
        o.val[short] = st.session_state.get(f"val_{short}") or None
        o.delta_lean[short] = st.session_state.get(f"delta_{short}", "unknown")
        o.profile_shape[short] = st.session_state.get(f"shape_{short}", "auto")
        o.notes[short] = st.session_state.get(f"vpnote_{short}", "") or ""
        # Treat 0.0 as empty — number_input min is 0
        for attr in ("on_high", "on_low", "poc", "vah", "val"):
            val = getattr(o, attr)[short]
            if val is not None and float(val) == 0.0:
                getattr(o, attr)[short] = None
    flag = st.session_state.get("high_impact_flag", "auto")
    o.high_impact_override = True if flag == "yes" else False if flag == "no" else None
    return o


@st.cache_data(ttl=300, show_spinner=False)
def _fetch(force_mock: bool, scenario: str, nonce: int):
    return load_market_bundle(
        force_mock=force_mock,
        scenario=scenario,
        overlays=None,
        use_disk_cache=True,
    )


def _run(force_mock: bool, scenario: str, nonce: int, overlays: UserOverlays, weights, bias, margin, mode, hard_stop, notes: str):
    bundle = copy.deepcopy(_fetch(force_mock, scenario, nonce))
    apply_overlays(bundle, overlays)
    return analyze_session(
        bundle,
        weights=weights,
        mes_bias=bias,
        switch_margin=margin,
        mode=mode,
        hard_stop_usd=hard_stop,
        overlays=overlays,
        override_notes=notes,
    )


# ── Sidebar ────────────────────────────────────────────────────────────────
clock = _clock()
with st.sidebar:
    st.markdown(f"<div class='kicker'>{PROTOCOL_SHORT} · v{RULEBOOK_VERSION}</div>", unsafe_allow_html=True)
    st.markdown(f"**{APP_NAME}**")
    st.caption(clock.note)
    st.caption("This replaced the old full desk as the default Streamlit app. Old desk: `python -m streamlit run desk_app.py`")

    data_mode = st.radio(
        "Data",
        ["Live (Yahoo)", "Demo"],
        index=0,
        help="Live pulls delayed Yahoo futures/ETFs/VIX. Demo uses bundled sample sessions.",
    )
    scenario = "mes_default"
    if data_mode == "Demo":
        scenario = st.selectbox(
            "Sample session",
            list(SCENARIOS.keys()),
            format_func=lambda k: SCENARIOS[k],
        )
    force_mock = data_mode == "Demo"

    mode = st.radio(
        "Protocol mode",
        ["strict_mr", "allow_mild_momentum"],
        format_func=lambda m: "Strict mean-reversion only" if m == "strict_mr" else "Allow mild momentum / channel days",
        help="Strict penalizes directional efficiency and event days. Mild momentum allows channel fades.",
    )
    hard_stop = st.slider("Hard stop ($)", int(HARD_STOP_MIN_USD), int(HARD_STOP_MAX_USD), int(HARD_STOP_DEFAULT_USD), 5)
    mes_bias = st.slider("MES default bias (pts)", 0.0, 12.0, float(MES_BIAS_POINTS), 0.5)
    switch_margin = st.slider("Switch margin (pts)", 3.0, 15.0, float(SWITCH_MARGIN), 0.5)

    st.markdown("**Weights** (auto-normalized)")
    w = {}
    for key in DEFAULT_WEIGHTS:
        w[key] = st.slider(
            WEIGHT_LABELS[key],
            0.0, 0.50, float(DEFAULT_WEIGHTS[key]), 0.01,
            help=WEIGHT_HELP[key],
        )

    st.markdown("**Event day**")
    st.selectbox("Treat session as high-impact?", ["auto", "yes", "no"], key="high_impact_flag")

    st.markdown("**Overnight / VP overlay**")
    st.caption("Paste platform numbers to replace the Yahoo VAP proxy. Leave at 0 to ignore.")
    tab_mes, tab_mnq, tab_mym = st.tabs(["MES", "MNQ", "MYM"])
    for tab, short in zip((tab_mes, tab_mnq, tab_mym), ORDERED_BOOKS):
        with tab:
            c1, c2 = st.columns(2)
            c1.number_input("ON high", min_value=0.0, step=0.25, key=f"on_hi_{short}")
            c2.number_input("ON low", min_value=0.0, step=0.25, key=f"on_lo_{short}")
            c3, c4, c5 = st.columns(3)
            c3.number_input("POC", min_value=0.0, step=0.25, key=f"poc_{short}")
            c4.number_input("VAH", min_value=0.0, step=0.25, key=f"vah_{short}")
            c5.number_input("VAL", min_value=0.0, step=0.25, key=f"val_{short}")
            st.selectbox("Delta lean", ["unknown", "bid", "ask", "mixed"], key=f"delta_{short}")
            st.selectbox("Profile shape", ["auto", "balanced", "unbalanced", "trend"], key=f"shape_{short}")
            st.text_input("VP notes", key=f"vpnote_{short}", placeholder="e.g. HVN 5640–5648, LVN 5628")

    if st.button("Clear cached Yahoo pull"):
        _fetch.clear()
        st.session_state["nonce"] = st.session_state.get("nonce", 0) + 1


# ── Header ─────────────────────────────────────────────────────────────────
st.markdown(
    f"""
<div class="hero">
  <div class="kicker">{PROTOCOL_NAME} · micros only · −$50 to −$100</div>
  <h1 class="app-title">{APP_NAME}</h1>
  <p class="tagline">{APP_TAGLINE}</p>
</div>
""",
    unsafe_allow_html=True,
)

c_a, c_b, c_c, c_d = st.columns([1.4, 1, 1, 1])
with c_a:
    analyze = st.button("Refresh / Analyze Today", type="primary", width="stretch")
with c_b:
    st.caption(f"Target RTH **{clock.target_rth.strftime('%a %Y-%m-%d')}**")
with c_c:
    st.caption(f"Phase **{clock.phase.replace('_', ' ')}**")
with c_d:
    st.caption(clock.now.strftime("%H:%M ET"))

if "nonce" not in st.session_state:
    st.session_state.nonce = 0
if analyze:
    st.session_state.nonce += 1
    _fetch.clear()

overlays = _overlays_from_ui()
notes_seed = st.session_state.get("override_notes", "")

with st.spinner("Scoring MES / MNQ / MYM…"):
    try:
        rec = _run(
            force_mock,
            scenario,
            st.session_state.nonce,
            overlays,
            w,
            mes_bias,
            switch_margin,
            mode,
            float(hard_stop),
            notes_seed,
        )
    except Exception as exc:
        st.error(f"Selector failed: {exc}")
        rec = _run(True, "mes_default", st.session_state.nonce, overlays, w, mes_bias, switch_margin, mode, float(hard_stop), notes_seed)
        rec.summary = "Fell back to demo after an unexpected error. " + rec.summary

st.session_state["rec"] = rec
pick = next(s for s in rec.scores if s.short == rec.pick)
card_cls = "pick-card"
if rec.using_mock:
    card_cls += " demo"
if rec.sit_out_warning:
    card_cls += " warn"
conf_cls = "conf-num low" if rec.confidence < 55 else "conf-num"

chips = [
    f"<span class='chip gold'>FOCUS {rec.pick}</span>",
    f"<span class='chip'>GRADE {pick.grade}</span>",
    f"<span class='chip'>{rec.mode.replace('_', ' ')}</span>",
]
if rec.using_mock:
    chips.append("<span class='chip'>DEMO DATA</span>")
if rec.switch_from_mes:
    chips.append("<span class='chip green'>SWITCH vs MES DEFAULT</span>")
else:
    chips.append("<span class='chip gold'>MES DEFAULT HOLDS</span>")
if rec.sit_out_warning:
    chips.append("<span class='chip red'>SIT-OUT WARNING</span>")

st.markdown(
    f"""
<div class="{card_cls}">
  <div class="kicker">Top recommendation · {rec.session_date} · {rec.as_of}</div>
  <div class="pick-symbol">{rec.pick}</div>
  <div class="pick-name">{rec.pick_name}</div>
  <div class="meta-row">{''.join(chips)}</div>
  <div class="conf-wrap">
    <div class="conf-label">CONFIDENCE</div>
    <div class="{conf_cls}">{rec.confidence}<span style="font-size:1rem;color:#8b93a7"> / 100</span></div>
    <div class="conf-bar"><div style="width:{rec.confidence}%"></div></div>
  </div>
  <p class="pick-why">{rec.summary}</p>
</div>
""",
    unsafe_allow_html=True,
)

# ── Comparison + risk ──────────────────────────────────────────────────────
st.markdown("##### Comparison")
rows = []
for s in rec.scores:
    by = {f.key: f.raw for f in s.factors}
    flag = "◀ PICK" if s.short == rec.pick else ""
    rows.append(
        {
            " ": flag,
            "Book": s.short,
            "Composite": s.composite,
            "Pre-bias": s.composite_pre_bias,
            "Grade": s.grade,
            "Clean": by.get("cleanliness"),
            "Potential": by.get("profit_potential"),
            "Liquidity": by.get("liquidity"),
            "CPRP": by.get("cprp_alignment"),
            "Lead": by.get("leadership"),
            "Exp. RTH $": round(s.metrics.expected_rth_usd, 0),
            "ATR $": round(s.metrics.atr14_usd, 0),
            "ON range $": round(s.metrics.overnight.range_usd, 0),
            "Last": s.metrics.last_price,
        }
    )
cmp_df = pd.DataFrame(rows)
st.dataframe(
    cmp_df,
    width="stretch",
    hide_index=True,
    column_config={
        "Composite": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
        "Clean": st.column_config.NumberColumn(format="%.0f"),
        "Potential": st.column_config.NumberColumn(format="%.0f"),
        "Liquidity": st.column_config.NumberColumn(format="%.0f"),
        "CPRP": st.column_config.NumberColumn(format="%.0f"),
        "Lead": st.column_config.NumberColumn(format="%.0f"),
    },
)
st.caption(
    f"`{rec.formula}`  ·  MES bias +{rec.mes_bias_points:.0f}  ·  "
    f"challenger must beat MES by {rec.switch_margin:.0f} after bias  ·  "
    f"trade threshold {MIN_SCORE_TO_TRADE:.0f}"
)

st.markdown("##### Risk & sizing")
notes = sizing_notes(rec.pick, rec.hard_stop_usd, pick.suggested_stop_pts)
risk_html = "<div class='risk-box'>" + "<br>".join(f"• {n}" for n in notes)
risk_html += (
    f"<br><br><b>Suggested max:</b> "
    f"{pick.max_contracts_50} contract @ $50  ·  {pick.max_contracts_100} contract @ $100  "
    f"(protocol default is <b>1 micro</b>)."
)
if rec.sit_out_warning:
    risk_html += "<br><br><b>Sit-out:</b> do not force a limit at the node until value rebuilds."
risk_html += "</div>"
st.markdown(risk_html, unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("VIX", rec.internals.vix_last if rec.internals.vix_last is not None else "—", rec.internals.vix_change)
m2.metric("VIX regime", rec.internals.vix_regime)
m3.metric("Leader", rec.internals.leader)
m4.metric("QQQ−SPY pp", rec.internals.spread_qqq_spy if rec.internals.spread_qqq_spy is not None else "—")

# ── Internals / calendar strip ─────────────────────────────────────────────
hi_cal = [e for e in rec.calendar if e.impact in {"high", "medium"}][:6]
if hi_cal:
    st.markdown("##### Calendar (near session)")
    st.dataframe(
        pd.DataFrame(
            [
                {"Date": e.date, "ET": e.time, "Event": e.title, "Impact": e.impact, "Src": e.source}
                for e in hi_cal
            ]
        ),
        width="stretch",
        hide_index=True,
    )

# ── Expandable sections ────────────────────────────────────────────────────
with st.expander("Full score breakdown", expanded=False):
    fig = go.Figure()
    cats = [WEIGHT_LABELS[k] for k in DEFAULT_WEIGHTS]
    for s in rec.scores:
        by = {f.key: f.raw for f in s.factors}
        fig.add_trace(
            go.Bar(
                name=s.short,
                x=cats,
                y=[by[k] for k in DEFAULT_WEIGHTS],
                marker_color={"MES": "#C9A84C", "MNQ": "#5b9fd6", "MYM": "#8e7cc3"}[s.short],
            )
        )
    fig.update_layout(
        barmode="group",
        template="plotly_dark",
        paper_bgcolor="#0A0C10",
        plot_bgcolor="#0A0C10",
        font=dict(color="#E8E0CC", family="IBM Plex Sans"),
        legend=dict(orientation="h", y=1.12),
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis=dict(range=[0, 100], gridcolor="#222"),
        height=340,
    )
    st.plotly_chart(fig, width="stretch")
    for s in rec.scores:
        st.markdown(f"**{s.short} · {s.composite:.1f} ({s.grade})**  ·  pre-bias {s.composite_pre_bias:.1f}  ·  bias +{s.mes_bias:.0f}")
        for f in s.factors:
            st.caption(f"{f.label}  {f.raw:.0f}  ×  {f.weight:.0%}  =  {f.weighted:.1f}")
            for b in f.bullets:
                st.write(f"- {b}")
        if s.warnings:
            for wmsg in s.warnings:
                st.warning(wmsg)

with st.expander("Data sources used & missing-data haircuts", expanded=False):
    src_df = pd.DataFrame(rec.sources_used)
    if not src_df.empty:
        st.dataframe(src_df, width="stretch", hide_index=True)
    st.markdown(
        """
**How the score degrades when depth is missing**

| Gap | Effect |
|-----|--------|
| Volume profile is Yahoo VAP only (no NT/CME nodes) | Cleanliness × 0.88 · confidence −8 |
| VIX missing | Alignment uses a neutral vol · confidence −3 |
| Calendar live fetch fails | Static FOMC/CPI/NFP list · confidence −4 |
| Live Yahoo fails | Entire run is DEMO · confidence −6 · do not trade the print |
| TICK / ADD / VOLD missing | Leadership uses SPY / QQQ / DIA only |
| Overnight not open yet (weekend / 16:00–18:00) | Uses last completed Globex as a proxy |

Paid hooks later: drop a Databento / CME / NinjaTrader exporter into `providers/` implementing the same `MarketBundle` shape.
"""
    )
    if rec.gaps:
        st.markdown("**Gaps this run**")
        st.dataframe(
            pd.DataFrame([{"key": g.key, "detail": g.detail, "effect": g.score_effect} for g in rec.gaps]),
            width="stretch",
            hide_index=True,
        )

with st.expander("Raw metrics table", expanded=False):
    raw_rows = []
    for s in rec.scores:
        m = s.metrics
        raw_rows.append(
            {
                "Book": s.short,
                "Last": m.last_price,
                "Price src": m.price_source,
                "ON high": m.overnight.high,
                "ON low": m.overnight.low,
                "ON last": m.overnight.last,
                "ON pts": m.overnight.range_pts,
                "ON ER": m.overnight.efficiency,
                "ON pos": m.overnight.position,
                "1H bias": m.htf.bias,
                "1H ER": m.htf.efficiency,
                "POC": m.profile.poc,
                "VAH": m.profile.vah,
                "VAL": m.profile.val,
                "VP clarity": m.profile.clarity,
                "VP balance": m.profile.balance_label,
                "VP proxy": m.profile.is_proxy,
                "ATR14 pts": m.atr14_pts,
                "ATR14 $": m.atr14_usd,
                "Exp RTH pts": m.expected_rth_pts,
                "Exp RTH $": m.expected_rth_usd,
                "Vol vs 20d": m.volume_vs_20d,
                "H tests": m.dual_side_high_tests,
                "L tests": m.dual_side_low_tests,
                "ER": m.path_efficiency,
                "RSI14": m.rsi14,
            }
        )
    st.dataframe(pd.DataFrame(raw_rows), width="stretch", hide_index=True)
    st.caption("Overnight / 1H / VP are the inputs the factors actually used (including any sidebar overlay).")

with st.expander("Risk calculator", expanded=False):
    rc1, rc2, rc3 = st.columns(3)
    book = rc1.selectbox("Instrument", ORDERED_BOOKS, index=ORDERED_BOOKS.index(rec.pick))
    risk_usd = rc2.slider("Risk budget $", 50, 200, int(rec.hard_stop_usd), 5, key="calc_risk")
    inst_m = next(s.metrics for s in rec.scores if s.short == book)
    auto_stop = suggested_stop_pts(book, inst_m.overnight.range_pts, inst_m.atr14_pts, float(risk_usd))
    stop_pts = rc3.number_input("Stop distance (pts)", min_value=float(INSTRUMENTS[book].tick_size), value=float(round(auto_stop, 2)), step=float(INSTRUMENTS[book].tick_size))
    p = plan(book, stop_pts, float(risk_usd))
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Ticks", f"{p.stop_ticks:.0f}")
    k2.metric("$ / contract", f"${p.usd_per_contract:.0f}")
    k3.metric("Contracts", p.contracts)
    k4.metric("Actual $ risk", f"${p.actual_risk_usd:.0f}")
    st.info(p.note)
    st.caption(
        f"1 {book} pt = ${INSTRUMENTS[book].point_value:.2f}  ·  "
        f"tick {INSTRUMENTS[book].tick_size:g} = ${INSTRUMENTS[book].tick_value:.2f}  ·  "
        f"${risk_usd:.0f} hard stop = {risk_usd / INSTRUMENTS[book].point_value:.2f} pts"
    )

with st.expander("Historical (what the simplified model would have picked)", expanded=False):
    st.caption("Daily ES/NQ/YM + SPY/QQQ/DIA only. No session volume profile. Treat as a sanity check, not a backtest.")
    if st.button("Build last ~12 sessions"):
        with st.spinner("Downloading daily bars…"):
            hist = historical_picks(12)
        st.session_state["hist"] = hist
    hist = st.session_state.get("hist")
    if hist is not None and not getattr(hist, "empty", True):
        st.dataframe(hist, width="stretch", hide_index=True)
        counts = hist["pick"].value_counts()
        st.caption("Pick counts: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    elif hist is not None:
        st.warning("No historical rows (Yahoo daily download empty).")

# ── Notes + export ─────────────────────────────────────────────────────────
st.markdown("##### Trader notes (override log)")
override = st.text_area(
    "Why you took a different book — saved with the daily log if you click Log.",
    key="override_notes",
    placeholder="e.g. Took MNQ anyway — ES profile was a messy P, NQ had a clean HVN at 20105 with bid delta.",
    height=80,
)
b1, b2, b3, b4 = st.columns(4)
with b1:
    if st.button("Log today's pick", width="stretch"):
        rec.override_notes = override
        path = log_recommendation(rec, override)
        st.success(f"Appended to {path}")
with b2:
    rec.override_notes = override
    st.download_button(
        "Export markdown",
        rec_to_markdown(rec),
        file_name=f"cprp_selector_{rec.session_date}_{rec.pick}.md",
        mime="text/markdown",
        width="stretch",
    )
with b3:
    st.download_button(
        "Export JSON",
        json.dumps(rec.to_dict(), indent=2),
        file_name=f"cprp_selector_{rec.session_date}_{rec.pick}.json",
        mime="application/json",
        width="stretch",
    )
with b4:
    st.caption(f"Logged picks live in `logs/recommendations.jsonl`")

st.markdown(
    f"""
<div class="footer">
  {PROTOCOL_NAME} ({PROTOCOL_SHORT}) · Rulebook {RULEBOOK_VERSION} · {CREATOR}<br>
  Not personalized financial, investment, or trading advice. You own your decisions, risk, and results.
  Futures trading involves substantial risk of loss. Yahoo data is delayed and is not CME order flow.
  Limit entries at HVN/LVN edges still require live delta on your platform.
</div>
""",
    unsafe_allow_html=True,
)
