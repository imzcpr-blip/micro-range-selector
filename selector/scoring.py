"""Transparent CPRP scoring engine.

composite = Σ (weight_i × factor_i) + MES_bias
Recommend MNQ/MYM only if challenger >= MES + SWITCH_MARGIN after bias.

Factors (default weights):
  cleanliness        28%  HTF range, dual-side tests, HVN/LVN, overnight two-sidedness
  profit_potential   22%  expected RTH $ vs $50–$100 stop (sweet spot 2.5×–5.5×)
  liquidity          18%  structural depth + relative volume
  cprp_alignment     18%  mean-reversion friendliness (VIX, news, balance, ER)
  leadership         14%  rotation opportunity without being the runaway vehicle

Missing volume-profile depth: cleanliness × 0.88 and confidence −8.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from selector.config import (
    DEFAULT_WEIGHTS,
    ER_MIXED_MAX,
    ER_RANGE_MAX,
    ER_TREND_MAX,
    HARD_STOP_DEFAULT_USD,
    INSTRUMENTS,
    MES_BIAS_POINTS,
    MIN_SCORE_TO_TRADE,
    MISSING_CALENDAR_HAIRCUT,
    MISSING_VIX_HAIRCUT,
    MOCK_OR_PARTIAL_HAIRCUT,
    ORDERED_BOOKS,
    SWITCH_MARGIN,
    VP_PROXY_CLEANLINESS_MULT,
    VP_PROXY_CONFIDENCE_HAIRCUT,
    WEIGHT_LABELS,
)
from selector.models import (
    FactorScore,
    InternalsSnapshot,
    MarketBundle,
    Recommendation,
    ScoredInstrument,
    UserOverlays,
)
from selector.providers.calendar_provider import session_impact
from selector.risk_calc import max_contracts, suggested_stop_pts


FORMULA = (
    "composite = 0.28·cleanliness + 0.22·profit_potential + 0.18·liquidity "
    "+ 0.18·cprp_alignment + 0.14·leadership  +  MES_bias(6)  |  "
    "switch if challenger ≥ MES + 8 after bias"
)


def analyze_session(
    bundle: MarketBundle,
    *,
    weights: Optional[dict[str, float]] = None,
    mes_bias: float = MES_BIAS_POINTS,
    switch_margin: float = SWITCH_MARGIN,
    mode: str = "strict_mr",
    hard_stop_usd: float = HARD_STOP_DEFAULT_USD,
    overlays: Optional[UserOverlays] = None,
    override_notes: str = "",
) -> Recommendation:
    weights = _normalize(weights or DEFAULT_WEIGHTS)
    overlays = overlays or UserOverlays()
    impact = session_impact(
        bundle.calendar,
        _parse_date(bundle.session_date),
        overlays.high_impact_override,
    )

    scored: list[ScoredInstrument] = []
    for short in ORDERED_BOOKS:
        scored.append(
            _score_one(
                bundle,
                short,
                weights,
                mes_bias if short == "MES" else 0.0,
                mode,
                hard_stop_usd,
                impact,
                overlays,
            )
        )

    pick, switch = _choose(scored, switch_margin)
    winner = next(s for s in scored if s.short == pick)
    runner = max((s for s in scored if s.short != pick), key=lambda s: s.composite)
    confidence = _confidence(bundle, winner, runner, overlays)
    sit_out = winner.composite < MIN_SCORE_TO_TRADE or (
        bundle.internals.vix_regime in {"event", "elevated"} and impact == "high"
    )
    if mode == "strict_mr" and winner.metrics.path_efficiency > ER_TREND_MAX:
        sit_out = True

    summary = _summary(winner, scored, switch, sit_out, bundle, mode, impact)

    return Recommendation(
        pick=pick,
        pick_name=winner.name,
        confidence=confidence,
        summary=summary,
        sit_out_warning=sit_out,
        switch_from_mes=switch,
        mode=mode,
        hard_stop_usd=hard_stop_usd,
        session_date=bundle.session_date,
        session_phase=bundle.session_phase,
        as_of=bundle.as_of,
        using_mock=bundle.using_mock,
        scores=scored,
        weights=weights,
        mes_bias_points=mes_bias,
        switch_margin=switch_margin,
        internals=bundle.internals,
        calendar=bundle.calendar,
        gaps=bundle.gaps,
        sources_used=bundle.sources_used,
        formula=_formula_text(weights, mes_bias, switch_margin),
        override_notes=override_notes,
    )


def _score_one(
    bundle: MarketBundle,
    short: str,
    weights: dict[str, float],
    bias: float,
    mode: str,
    hard_stop: float,
    impact: str,
    overlays: UserOverlays,
) -> ScoredInstrument:
    m = bundle.metrics[short]
    internals = bundle.internals
    lean = (overlays.delta_lean.get(short) or "unknown").lower()

    clean, clean_notes = _cleanliness(m, overlays)
    pot, pot_notes = _profit(m, hard_stop)
    liq, liq_notes = _liquidity(m)
    aln, aln_notes = _alignment(m, internals, impact, mode, lean)
    lead, lead_notes = _leadership(m, internals)

    raws = {
        "cleanliness": clean,
        "profit_potential": pot,
        "liquidity": liq,
        "cprp_alignment": aln,
        "leadership": lead,
    }
    notes = {
        "cleanliness": clean_notes,
        "profit_potential": pot_notes,
        "liquidity": liq_notes,
        "cprp_alignment": aln_notes,
        "leadership": lead_notes,
    }
    factors = []
    pre = 0.0
    for key in DEFAULT_WEIGHTS:
        w = weights[key]
        r = float(np.clip(raws[key], 0, 100))
        factors.append(
            FactorScore(
                key=key,
                label=WEIGHT_LABELS[key],
                weight=w,
                raw=round(r, 1),
                weighted=round(w * r, 2),
                bullets=notes[key],
            )
        )
        pre += w * r
    composite = float(np.clip(pre + bias, 0, 100))

    stop_pts = suggested_stop_pts(short, m.overnight.range_pts, m.atr14_pts, hard_stop)
    stop_usd = stop_pts * m.point_value
    c50 = max_contracts(short, stop_pts, 50)
    c100 = max_contracts(short, stop_pts, 100)

    reasons = []
    warnings = list(m.warnings)
    for f in factors:
        reasons.extend(f.bullets[:2])
    if bias:
        reasons.insert(0, f"MES default bias +{bias:.0f} (liquidity, smoother tape, protocol familiarity).")
    if m.profile.is_proxy:
        warnings.append("VP is a proxy — confirm POC/HVN on the platform before working limits.")

    grade = _grade(composite)
    return ScoredInstrument(
        short=short,
        name=m.name,
        composite=round(composite, 1),
        composite_pre_bias=round(pre, 1),
        mes_bias=bias,
        confidence_contrib=round(composite, 1),
        grade=grade,
        factors=factors,
        metrics=m,
        reasons=reasons[:8],
        warnings=warnings,
        max_contracts_50=c50,
        max_contracts_100=c100,
        stop_pts_at_default=round(hard_stop / m.point_value, 2),
        suggested_stop_pts=round(stop_pts, 2),
        suggested_stop_usd=round(stop_usd, 2),
    )


def _cleanliness(m, overlays: UserOverlays) -> tuple[float, list[str]]:
    notes = []
    # Higher-TF range definition (low ER = cleaner for CPRP).
    er = m.htf.efficiency
    if er <= ER_RANGE_MAX:
        htf_s, htf_n = 88.0, f"1H is ranging (ER {er:.2f}) — clean map for fades."
    elif er <= ER_MIXED_MAX:
        htf_s, htf_n = 68.0, f"1H mixed (ER {er:.2f}) — usable but wait for dual-side tests."
    elif er <= ER_TREND_MAX:
        htf_s, htf_n = 42.0, f"1H is directional (ER {er:.2f}) — structure not a clean range."
    else:
        htf_s, htf_n = 22.0, f"1H trending hard (ER {er:.2f}) — do not force HVN fades."
    notes.append(htf_n)

    hi, lo = m.dual_side_high_tests, m.dual_side_low_tests
    if hi >= 2 and lo >= 2:
        test_s = 92.0
        notes.append(f"Boundaries retested both sides (H:{hi} / L:{lo}).")
    elif hi >= 1 and lo >= 1:
        test_s = 68.0
        notes.append(f"Single test each side (H:{hi} / L:{lo}) — wait for a second touch.")
    elif hi + lo >= 2:
        test_s = 45.0
        notes.append("Tests are one-sided — not yet a confirmed range.")
    else:
        test_s = 28.0
        notes.append("No clear boundary tests in the window.")

    vp = m.profile
    vp_s = float(np.clip(vp.clarity, 0, 100))
    if vp.balance_label == "balanced":
        vp_s = min(100.0, vp_s + 8)
        notes.append(f"Profile {vp.balance_label} · POC {vp.poc:.2f} · VA {vp.val:.2f}–{vp.vah:.2f} (clarity {vp.clarity:.0f}).")
    else:
        vp_s = max(0.0, vp_s - 10)
        notes.append(f"Profile {vp.balance_label} — HVN edges are less trustworthy for limits.")
    user_poc = overlays.poc.get(m.short)
    if user_poc is not None or (overlays.profile_shape.get(m.short) or "auto") != "auto":
        notes.append("Trader-supplied profile overlay is boosting cleanliness vs the Yahoo proxy.")

    on = m.overnight
    # Two-sided overnight: ER low and last not glued to an extreme.
    extreme = on.position <= 0.12 or on.position >= 0.88
    if on.efficiency <= ER_RANGE_MAX and not extreme:
        on_s = 86.0
        notes.append(f"Overnight two-sided ({on.range_pts:.1f} pts, ER {on.efficiency:.2f}).")
    elif on.efficiency <= ER_MIXED_MAX and not extreme:
        on_s = 64.0
        notes.append(f"Overnight mixed ({on.range_pts:.1f} pts). Tradable if RTH rebuilds value.")
    elif extreme:
        on_s = 36.0
        notes.append(f"Overnight close is at the extreme ({on.position:.0%} of the range).")
    else:
        on_s = 40.0
        notes.append(f"Overnight looks one-way (ER {on.efficiency:.2f}).")

    raw = 0.30 * htf_s + 0.25 * test_s + 0.25 * vp_s + 0.20 * on_s
    if vp.is_proxy:
        raw *= VP_PROXY_CLEANLINESS_MULT
        notes.append("VP depth missing — cleanliness × 0.88 (Yahoo VAP proxy only).")
    return float(np.clip(raw, 0, 100)), notes


def _profit(m, hard_stop: float) -> tuple[float, list[str]]:
    notes = []
    expected_usd = m.expected_rth_usd or (m.atr14_usd * 0.7)
    rm = expected_usd / hard_stop if hard_stop else 0.0
    # Sweet spot 2.5×–5.5× the hard stop. Too tight = no R. Too wild = $75 is noise.
    if rm < 1.2:
        score = 22.0 + rm * 8
        notes.append(f"Expected RTH ~${expected_usd:.0f} is tight versus a ${hard_stop:.0f} stop ({rm:.1f}R).")
    elif rm < 2.5:
        score = 50.0 + (rm - 1.2) * 18
        notes.append(f"Expected RTH ~${expected_usd:.0f} ({rm:.1f}R) — modest but usable.")
    elif rm <= 5.5:
        score = 78.0 + (rm - 2.5) * 5.5  # peaks near 4–5R
        notes.append(f"Expected RTH ~${expected_usd:.0f} ({rm:.1f}R vs ${hard_stop:.0f}) — CPRP sweet spot.")
    else:
        score = 88.0 - min((rm - 5.5) * 7.0, 40)
        notes.append(
            f"Expected RTH ~${expected_usd:.0f} ({rm:.1f}R) is wide — a ${hard_stop:.0f} stop is inside noise unless the node is tight."
        )

    # Tick practicality: can you work a limit at a node without the stop being a few ticks?
    inst = INSTRUMENTS[m.short]
    ticks_in_stop = hard_stop / inst.tick_value
    if ticks_in_stop < 40:
        score -= 6
        notes.append(f"Only {ticks_in_stop:.0f} ticks in the hard stop — fills need to be precise.")
    else:
        notes.append(f"{ticks_in_stop:.0f} ticks in a ${hard_stop:.0f} stop (tick ${inst.tick_value:.2f}).")

    # ATR vs typical band
    lo, hi = m.typical_rth_pts
    if m.atr14_pts and hi:
        if m.atr14_pts > hi * 1.35:
            score -= 8
            notes.append("ATR is stretched vs this micro's typical RTH band.")
        elif lo <= m.atr14_pts <= hi:
            score += 4
            notes.append(f"ATR {m.atr14_pts:.0f} pts sits inside the typical {lo:.0f}–{hi:.0f} band.")
    # Trend expansion is not mean-reversion R — don't let a blow-off look like "high potential".
    if m.path_efficiency > ER_TREND_MAX:
        score *= 0.65
        notes.append("Potential discounted — the range is trend expansion, not mean-reversion R.")
    return float(np.clip(score, 0, 100)), notes


def _liquidity(m) -> tuple[float, list[str]]:
    inst = INSTRUMENTS[m.short]
    base = inst.liquidity_base
    notes = [f"Structural liquidity base {base:.0f}/100 ({inst.notes})"]
    adj = 0.0
    if m.volume_vs_20d:
        # 0.7× → −8, 1.0× → 0, 1.4× → +8
        adj += float(np.clip((m.volume_vs_20d - 1.0) * 20, -12, 10))
        notes.append(f"Prior-day volume {m.volume_vs_20d:.2f}× the 20-session average (Yahoo).")
    if m.open_interest:
        notes.append(f"Open interest {m.open_interest:,.0f} (Yahoo, if populated).")
        adj += 3
    if m.price_source.endswith("=F") and "E" in m.price_source:
        notes.append(f"Price path from {m.price_source} — volume is an E-mini proxy, not micro prints.")
    score = float(np.clip(base + adj, 0, 100))
    return score, notes


def _alignment(m, internals: InternalsSnapshot, impact: str, mode: str, lean: str) -> tuple[float, list[str]]:
    notes = []
    score = 70.0

    er = m.path_efficiency
    if er <= ER_RANGE_MAX:
        score += 12
        notes.append(f"Path efficiency {er:.2f} — two-sided tape, protocol-friendly.")
    elif er <= ER_MIXED_MAX:
        score += 2
        notes.append(f"Path efficiency {er:.2f} — mixed. Strict mode stays selective.")
    else:
        penalty = 18 if mode == "strict_mr" else 8
        score -= penalty
        notes.append(f"Path efficiency {er:.2f} — momentum day. Strict CPRP penalizes this.")

    if m.profile.balance_label == "balanced":
        score += 8
        notes.append("Balanced profile — limits at HVN edges are the A+ location.")
    else:
        score -= 10
        notes.append("Unbalanced / trend profile — mean-reversion is the underdog.")

    regime = internals.vix_regime
    if regime == "fadeable":
        score += 8
        notes.append(f"VIX {internals.vix_last} ({regime}) — good regime for node fades.")
    elif regime == "grind":
        score += 1
        notes.append(f"VIX {internals.vix_last} grind — ranges may be too tight for $50–$100.")
    elif regime == "elevated":
        score -= 10
        notes.append(f"VIX {internals.vix_last} elevated — widen selectivity, not size.")
    elif regime == "event":
        score -= 22
        notes.append(f"VIX {internals.vix_last} event-like — CPRP sit-out until value rebuilds.")
    else:
        notes.append("VIX unavailable — alignment uses a neutral vol assumption.")

    if impact == "high":
        extra = 16 if m.short == "MNQ" else 12
        score -= extra
        notes.append(f"High-impact US print on the session — {m.short} alignment cut {extra}.")
    elif impact == "medium":
        score -= 6
        notes.append("Medium-impact print on the card — stay two-sided, skip the spike.")

    if lean in {"bid", "ask"}:
        score += 6
        notes.append(f"Trader delta lean: {lean} — only work the aligned edge of the node.")
    elif lean == "mixed":
        notes.append("Delta mixed — wait for dominance at the node.")

    if mode == "allow_mild_momentum" and ER_RANGE_MAX < er <= ER_MIXED_MAX and m.profile.balance_label != "unbalanced":
        score += 6
        notes.append("Mild-momentum toggle: channel fades allowed when 1H is not a blow-off.")

    return float(np.clip(score, 0, 100)), notes


def _leadership(m, internals: InternalsSnapshot) -> tuple[float, list[str]]:
    notes = list(internals.notes[:2])
    score = 55.0
    mapping = {"MES": "SPY", "MNQ": "QQQ", "MYM": "DIA"}
    etf = mapping[m.short]
    leader = internals.leader
    # Runaway leader is BAD for mean reversion. Quiet laggard with a clean range is OK.
    # Moderate leadership WITH a balanced profile is the opportunity.
    pct = {"MES": internals.spy_pct, "MNQ": internals.qqq_pct, "MYM": internals.dia_pct}[m.short]
    abs_pct = abs(pct) if pct is not None else 0.0

    if leader == "unknown":
        notes.append("No ETF leadership print — factor stays near neutral.")
        return 55.0, notes

    if leader == "mixed":
        score = 72.0 if m.short == "MES" else 64.0
        notes.append("Broad market moving as a package — MES is the lowest-opportunity-cost book.")
    elif etf == leader:
        if abs_pct >= 1.2 or m.path_efficiency > ER_MIXED_MAX:
            score = 40.0
            notes.append(f"{etf} is the runaway leader ({pct:+.2f}%) — poor fade vehicle today.")
        elif m.profile.balance_label == "balanced" and m.path_efficiency <= ER_MIXED_MAX:
            score = 86.0
            notes.append(f"{etf} leads but {m.short} is still rotating in value — real opportunity.")
        else:
            score = 62.0
            notes.append(f"{etf} leads ({pct:+.2f}%). Opportunity only if the profile stays two-sided.")
    elif etf == internals.laggard:
        if m.profile.balance_label == "balanced":
            score = 70.0
            notes.append(f"{etf} is lagging but the book is clean — possible quieter MES/MYM fade.")
        else:
            score = 48.0
            notes.append(f"{etf} is the laggard and the profile is messy — opportunity cost of sitting here is high.")
    else:
        score = 60.0
        notes.append(f"{etf} is mid-pack. Let cleanliness and R decide, not the headline leader.")

    # Sector-rotation proxy: QQQ–SPY spread.
    if internals.spread_qqq_spy is not None:
        if m.short == "MNQ" and abs(internals.spread_qqq_spy) >= 0.35 and m.profile.balance_label == "balanced":
            score += 6
            notes.append("QQQ/SPY spread is open and MNQ value is defined — rotation signal.")
        if m.short == "MES" and abs(internals.spread_qqq_spy) < 0.15:
            score += 4
            notes.append("No tech divergence — MES tracks the package with less basis risk.")
    return float(np.clip(score, 0, 100)), notes


def _opportunity(s: ScoredInstrument) -> float:
    """Cleanliness + profit potential — the two things that must beat MES to switch."""
    by = {f.key: f.raw for f in s.factors}
    return by.get("cleanliness", 0.0) + by.get("profit_potential", 0.0)


def _choose(scored: list[ScoredInstrument], margin: float) -> tuple[str, bool]:
    by = {s.short: s for s in scored}
    mes = by["MES"]
    best = max(scored, key=lambda s: (s.composite, -INSTRUMENTS[s.short].priority))
    if best.short == "MES":
        return "MES", False
    # Switch only when the challenger wins the composite *and* is actually
    # cleaner + higher-potential — not merely more volatile or more headline.
    opp_edge = _opportunity(best) - _opportunity(mes)
    if best.composite >= mes.composite + margin and opp_edge >= 6.0:
        return best.short, True
    return "MES", False


def _confidence(
    bundle: MarketBundle,
    winner: ScoredInstrument,
    runner: ScoredInstrument,
    overlays: UserOverlays,
) -> int:
    gap = winner.composite - runner.composite
    conf = winner.composite
    conf += float(np.clip(gap, 0, 10)) * 0.4  # separation bonus, small
    vp_proxy = winner.metrics.profile.is_proxy and not overlays.poc.get(winner.short)
    if vp_proxy:
        conf -= VP_PROXY_CONFIDENCE_HAIRCUT
    if any(g.key == "vix" for g in bundle.gaps):
        conf -= MISSING_VIX_HAIRCUT
    if bundle.calendar_source == "static" or any(g.key.startswith("calendar") for g in bundle.gaps):
        conf -= MISSING_CALENDAR_HAIRCUT
    if bundle.using_mock:
        conf -= MOCK_OR_PARTIAL_HAIRCUT
    if any(g.key.startswith("price_") for g in bundle.gaps):
        conf -= 5
    return int(np.clip(round(conf), 0, 100))


def _summary(winner, scored, switch, sit_out, bundle, mode, impact) -> str:
    others = [s for s in scored if s.short != winner.short]
    others_txt = ", ".join(f"{s.short} {s.composite:.0f}" for s in others)
    clean_f = next((f for f in winner.factors if f.key == "cleanliness"), None)
    pot_f = next((f for f in winner.factors if f.key == "profit_potential"), None)
    why = (clean_f.bullets[0] if clean_f and clean_f.bullets else (winner.reasons[0] if winner.reasons else ""))
    r_note = pot_f.bullets[0] if pot_f and pot_f.bullets else ""
    mes = next(s for s in scored if s.short == "MES")
    prefix = "DEMO — " if bundle.using_mock else ""

    if sit_out:
        return (
            f"{prefix}{winner.short} is still the named book ({winner.composite:.0f} vs {others_txt}), "
            f"but conviction is low: trending/event structure does not fit CPRP HVN-edge limits "
            f"on a ${winner.suggested_stop_usd:.0f} node. Default is sit out or wait for value to rebuild. {why}"
        )
    if switch:
        return (
            f"{prefix}{winner.short} scores meaningfully above MES "
            f"({winner.composite:.0f} vs MES {mes.composite:.0f} after the +{mes.mes_bias:.0f} MES bias). "
            f"{why} {r_note}"
        )
    return (
        f"{prefix}{winner.short} is the cleanest CPRP book today "
        f"({winner.composite:.0f} vs {others_txt}). {why} {r_note} "
        f"Neither challenger clears the switch margin, so the MES default holds."
    )


def _grade(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    if score >= 50:
        return "D"
    return "F"


def _normalize(weights: dict[str, float]) -> dict[str, float]:
    keys = list(DEFAULT_WEIGHTS)
    raw = {k: max(float(weights.get(k, DEFAULT_WEIGHTS[k])), 0.0) for k in keys}
    total = sum(raw.values()) or 1.0
    return {k: raw[k] / total for k in keys}


def _formula_text(weights: dict[str, float], bias: float, margin: float) -> str:
    parts = " + ".join(f"{weights[k]:.2f}·{k}" for k in DEFAULT_WEIGHTS)
    return f"composite = {parts}  +  MES_bias({bias:.0f})  |  switch if challenger ≥ MES + {margin:.0f}"


def _parse_date(iso: str):
    from datetime import date

    try:
        return date.fromisoformat(iso)
    except Exception:
        return date.today()
