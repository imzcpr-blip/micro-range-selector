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
from selector.desk_theme import (
    book_cards,
    chip,
    footer,
    inject,
    masthead,
    pick_board,
    risk_ticket,
    section,
    sidebar_brand,
    tape,
)
from selector.history import historical_picks, log_recommendation, rec_to_markdown
from selector.models import UserOverlays
from selector.providers import SCENARIOS, load_market_bundle, session_clock
from selector.providers.base import apply_overlays
from selector.risk_calc import plan, suggested_stop_pts
from selector.scoring import analyze_session

ET = ZoneInfo(ET_TZ)

st.set_page_config(
    page_title=APP_NAME,
    page_icon="▣",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject()


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
    sidebar_brand(PROTOCOL_SHORT, RULEBOOK_VERSION, APP_NAME, clock.note)

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
tape(clock)
masthead(PROTOCOL_NAME, APP_NAME, APP_TAGLINE)

c_a, c_b, c_c, c_d = st.columns([1.5, 1, 1, 0.9])
with c_a:
    analyze = st.button("Analyze session", type="primary", width="stretch")
with c_b:
    st.caption(f"RTH  **{clock.target_rth.strftime('%a %d %b')}**")
with c_c:
    st.caption(clock.phase.replace("_", " ").upper())
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

chips = [
    chip(f"Focus {rec.pick}", "gold"),
    chip(f"Grade {pick.grade}"),
    chip(rec.mode.replace("_", " ")),
]
if rec.using_mock:
    chips.append(chip("Demo data"))
if rec.switch_from_mes:
    chips.append(chip("Switch vs MES default", "green"))
else:
    chips.append(chip("MES default holds", "gold"))
if rec.sit_out_warning:
    chips.append(chip("Sit-out warning", "red"))

pick_board(
    pick=rec.pick,
    name=rec.pick_name,
    session_date=rec.session_date,
    as_of=rec.as_of,
    confidence=rec.confidence,
    summary=rec.summary,
    chips=chips,
    sit_out=rec.sit_out_warning,
    demo=rec.using_mock,
)

# ── Comparison + risk ──────────────────────────────────────────────────────
section("Books")
book_cards(rec.scores, rec.pick)
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

section("Risk ticket")
inst = INSTRUMENTS[rec.pick]
risk_note = (
    f"Suggested max {pick.max_contracts_50} @ $50  ·  {pick.max_contracts_100} @ $100. "
    "Protocol default is 1 micro."
)
if rec.sit_out_warning:
    risk_note = "SIT OUT — do not force a limit at the node until value rebuilds. " + risk_note
risk_ticket(
    [
        ("Contract", f"{rec.pick}  ·  {pick.name}"),
        ("Tick", f"{inst.tick_size:g} pts = ${inst.tick_value:.2f}   ·   1.00 pt = ${inst.point_value:.2f}"),
        ("Typical RTH", f"{inst.typical_rth_pts[0]:.0f}–{inst.typical_rth_pts[1]:.0f} pts"),
        ("Hard stop", f"${rec.hard_stop_usd:.0f} = {rec.hard_stop_usd / inst.point_value:.2f} pts"),
        ("Structure stop", f"{pick.suggested_stop_pts:.2f} pts  (${pick.suggested_stop_usd:.0f} / contract)"),
        ("Max size", f"$50 → {pick.max_contracts_50}   ·   $100 → {pick.max_contracts_100}"),
    ],
    risk_note,
    warn=rec.sit_out_warning,
)

section("Internals")
m1, m2, m3, m4 = st.columns(4)
m1.metric("VIX", rec.internals.vix_last if rec.internals.vix_last is not None else "—", rec.internals.vix_change)
m2.metric("VIX regime", rec.internals.vix_regime)
m3.metric("Leader", rec.internals.leader)
m4.metric("QQQ−SPY pp", rec.internals.spread_qqq_spy if rec.internals.spread_qqq_spy is not None else "—")

# ── Internals / calendar strip ─────────────────────────────────────────────
hi_cal = [e for e in rec.calendar if e.impact in {"high", "medium"}][:6]
if hi_cal:
    section("Calendar")
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
        paper_bgcolor="#0e1624",
        plot_bgcolor="#0e1624",
        font=dict(color="#E8EEF6", family="IBM Plex Sans"),
        legend=dict(orientation="h", y=1.12),
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis=dict(range=[0, 100], gridcolor="#1c2a40"),
        xaxis=dict(gridcolor="#1c2a40"),
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
section("Trader blotter")
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

footer(PROTOCOL_NAME, PROTOCOL_SHORT, RULEBOOK_VERSION, CREATOR)
