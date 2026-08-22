"""Daily recommendation log + a simplified historical 'what would have been picked' view."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from selector.config import ET_TZ, INSTRUMENTS, LOG_DIR, MES_BIAS_POINTS, ORDERED_BOOKS, SWITCH_MARGIN
from selector.models import Recommendation

ET = ZoneInfo(ET_TZ)
LOG_PATH = LOG_DIR / "recommendations.jsonl"


def log_recommendation(rec: Recommendation, notes: str = "") -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    row = rec.to_dict()
    row["logged_at"] = datetime.now(ET).isoformat()
    if notes:
        row["override_notes"] = notes
    # Keep the jsonl line compact: drop nested metrics OHLC-ish bulk if any
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")
    return LOG_PATH


def load_log(limit: int = 30) -> list[dict]:
    if not LOG_PATH.is_file():
        return []
    rows = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def rec_to_markdown(rec: Recommendation) -> str:
    lines = [
        f"# CPRP Micro Selector — {rec.session_date}",
        "",
        f"**Pick:** {rec.pick} ({rec.pick_name})  ",
        f"**Confidence:** {rec.confidence}/100  ",
        f"**Mode:** {rec.mode}  ",
        f"**Hard stop:** ${rec.hard_stop_usd:.0f}  ",
        f"**As of:** {rec.as_of}  ",
        f"**Demo:** {'yes' if rec.using_mock else 'no'}",
        "",
        rec.summary,
        "",
        "## Scores",
        "",
        "| Book | Composite | Pre-bias | Grade | Clean | Potential | Liquidity | CPRP | Lead |",
        "|------|-----------|----------|-------|-------|-----------|-----------|------|------|",
    ]
    for s in rec.scores:
        by = {f.key: f.raw for f in s.factors}
        lines.append(
            f"| {s.short} | {s.composite:.1f} | {s.composite_pre_bias:.1f} | {s.grade} "
            f"| {by.get('cleanliness', 0):.0f} | {by.get('profit_potential', 0):.0f} "
            f"| {by.get('liquidity', 0):.0f} | {by.get('cprp_alignment', 0):.0f} "
            f"| {by.get('leadership', 0):.0f} |"
        )
    lines += [
        "",
        f"Formula: `{rec.formula}`",
        "",
        "## Risk",
        "",
    ]
    pick = next(s for s in rec.scores if s.short == rec.pick)
    lines.append(
        f"{pick.short}: suggested stop {pick.suggested_stop_pts:.2f} pts "
        f"(${pick.suggested_stop_usd:.0f}) · max contracts $50={pick.max_contracts_50} "
        f"$100={pick.max_contracts_100}"
    )
    if rec.sit_out_warning:
        lines.append("\n**Sit-out warning is ON.** Do not force HVN-edge limits today.")
    if rec.override_notes:
        lines += ["", "## Trader notes", "", rec.override_notes]
    lines += ["", "## Gaps", ""]
    for g in rec.gaps:
        lines.append(f"- **{g.key}:** {g.detail} _{g.score_effect}_")
    lines += [
        "",
        "---",
        "Not personalized trading advice. You own your decisions, risk, and results.",
    ]
    return "\n".join(lines)


def historical_picks(days: int = 12) -> pd.DataFrame:
    """Back-of-envelope: daily range vs ATR + ETF relative performance. No VP."""
    try:
        import yfinance as yf
    except Exception:
        return pd.DataFrame()

    tickers = {
        "MES": "ES=F",
        "MNQ": "NQ=F",
        "MYM": "YM=F",
        "SPY": "SPY",
        "QQQ": "QQQ",
        "DIA": "DIA",
        "VIX": "^VIX",
    }
    try:
        raw = yf.download(
            list(tickers.values()),
            period="40d",
            interval="1d",
            auto_adjust=True,
            group_by="ticker",
            threads=True,
            progress=False,
        )
    except Exception:
        return pd.DataFrame()
    if raw is None or raw.empty:
        return pd.DataFrame()

    rows = []
    # Align on ES dates
    es = _one(raw, "ES=F")
    if es.empty:
        return pd.DataFrame()
    idx = es.dropna(subset=["Close"]).index[-days:]
    for ts in idx:
        day = ts.date().isoformat() if hasattr(ts, "date") else str(ts)[:10]
        parts = {}
        for short, ysym in (("MES", "ES=F"), ("MNQ", "NQ=F"), ("MYM", "YM=F")):
            df = _one(raw, ysym)
            if df.empty or ts not in df.index:
                continue
            parts[short] = _day_score(df, ts, short)
        if len(parts) < 3:
            continue
        spy = _ret(_one(raw, "SPY"), ts)
        qqq = _ret(_one(raw, "QQQ"), ts)
        dia = _ret(_one(raw, "DIA"), ts)
        vix = _last(_one(raw, "^VIX"), ts)
        # Leadership tweak
        leader = _argmax({"MES": spy, "MNQ": qqq, "MYM": dia})
        for short in ORDERED_BOOKS:
            if short not in parts:
                continue
            if leader == short and parts[short]["er_proxy"] > 0.62:
                parts[short]["score"] -= 8  # runaway
            elif leader == short and parts[short]["er_proxy"] < 0.45:
                parts[short]["score"] += 5
            if short == "MES":
                parts[short]["score"] += MES_BIAS_POINTS
        mes = parts["MES"]["score"]
        best = max(ORDERED_BOOKS, key=lambda s: parts[s]["score"])
        pick = best if parts[best]["score"] >= mes + SWITCH_MARGIN else "MES"
        rows.append(
            {
                "date": day,
                "pick": pick,
                "MES": round(parts["MES"]["score"], 1),
                "MNQ": round(parts["MNQ"]["score"], 1),
                "MYM": round(parts["MYM"]["score"], 1),
                "SPY %": spy,
                "QQQ %": qqq,
                "DIA %": dia,
                "VIX": vix,
                "note": "Simplified daily model — no session VP / order flow.",
            }
        )
    return pd.DataFrame(rows)


def _one(raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
    try:
        if isinstance(raw.columns, pd.MultiIndex):
            df = raw[symbol].copy()
        else:
            df = raw.copy()
        df.columns = [str(c).title() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()


def _day_score(df: pd.DataFrame, ts, short: str) -> dict:
    loc = df.index.get_loc(ts)
    window = df.iloc[max(0, loc - 14) : loc + 1]
    row = df.loc[ts]
    rng = float(row["High"] - row["Low"])
    atr = float((window["High"] - window["Low"]).mean())
    close = float(row["Close"])
    prev = float(df.iloc[loc - 1]["Close"]) if loc > 0 else close
    ret = (close / prev - 1.0) if prev else 0.0
    # ER proxy: |ret| / (range/close)
    er = abs(ret) / max(rng / max(close, 1e-9), 1e-6)
    er = float(np.clip(er, 0, 1.5)) / 1.5
    # Cleanliness: low ER, range not exploding vs ATR
    clean = 80.0 - er * 50
    if atr > 0:
        if 0.7 * atr <= rng <= 1.3 * atr:
            clean += 8
        elif rng > 1.8 * atr:
            clean -= 12
    inst = INSTRUMENTS[short]
    expected_usd = atr * inst.point_value
    rm = expected_usd / 75.0 if expected_usd else 0
    if 2.5 <= rm <= 5.5:
        pot = 82.0
    elif 1.5 <= rm < 2.5:
        pot = 60.0
    else:
        pot = 48.0
    liq = inst.liquidity_base
    aln = 75.0 if er < 0.4 else (55.0 if er < 0.6 else 35.0)
    score = 0.32 * clean + 0.22 * pot + 0.18 * liq + 0.18 * aln + 0.10 * 55.0
    return {"score": float(np.clip(score, 0, 100)), "er_proxy": er, "range": rng, "atr": atr}


def _ret(df: pd.DataFrame, ts) -> Optional[float]:
    if df.empty or ts not in df.index:
        return None
    loc = df.index.get_loc(ts)
    if loc == 0:
        return None
    prev = float(df.iloc[loc - 1]["Close"])
    last = float(df.loc[ts]["Close"])
    if prev == 0:
        return None
    return round(100.0 * (last / prev - 1.0), 2)


def _last(df: pd.DataFrame, ts) -> Optional[float]:
    if df.empty or ts not in df.index:
        return None
    return round(float(df.loc[ts]["Close"]), 2)


def _argmax(d: dict) -> Optional[str]:
    valid = {k: v for k, v in d.items() if v is not None}
    if not valid:
        return None
    # highest absolute move is the "leader" for this simplified view
    return max(valid, key=lambda k: abs(valid[k]))
