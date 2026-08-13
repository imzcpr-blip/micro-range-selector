"""
Market Deep Dive — CPRP Strategies Portfolio desk.

Google Finance private portfolios have no public API. This panel mirrors your
**CPRP Strategies Portfolio** holdings (JSON + optional secrets) and runs a
live deep dive on each asset every 60 seconds via Yahoo Finance quotes
(yfinance), with Google Finance quote links for each name.

Founder can edit holdings in-panel so the list stays aligned with Google Finance.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import yfinance as yf

from admin import is_current_user_admin
from disclosure import render_disclosure, render_third_party_disclosure
from wallstreet_ui import candle_expander, desk_section, link_label, page_hero

ET = ZoneInfo("America/New_York")

PORTFOLIO_PATH = Path(__file__).resolve().parent / "data" / "cprp_strategies_portfolio.json"
AUTO_REFRESH_SEC = 60
_KEY_LAST = "mdd_last_refresh"
_KEY_SNAPSHOT = "mdd_prev_snapshot"
_KEY_TICK = "mdd_refresh_tick"

GOOGLE_FINANCE_HOME = "https://www.google.com/finance"
GOOGLE_FINANCE_PORTFOLIO = "https://www.google.com/finance/portfolio"


# ── Portfolio I/O ─────────────────────────────────────────────────────────


def _default_portfolio() -> dict[str, Any]:
    return {
        "name": "CPRP Strategies Portfolio",
        "source": "Google Finance (mirrored holdings)",
        "google_finance_url": GOOGLE_FINANCE_PORTFOLIO,
        "notes": "",
        "updated_at": None,
        "holdings": [],
    }


def load_portfolio() -> dict[str, Any]:
    """Load portfolio JSON; merge optional st.secrets [portfolio] overrides."""
    data = _default_portfolio()
    if PORTFOLIO_PATH.is_file():
        try:
            raw = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data.update({k: v for k, v in raw.items() if k != "holdings"})
                if isinstance(raw.get("holdings"), list):
                    data["holdings"] = raw["holdings"]
        except Exception:
            pass

    # Optional Streamlit secrets override (Cloud / local secrets.toml)
    try:
        sec = st.secrets.get("portfolio", {})  # type: ignore[attr-defined]
    except Exception:
        sec = {}
    if sec:
        if sec.get("google_finance_url"):
            data["google_finance_url"] = str(sec.get("google_finance_url"))
        if sec.get("name"):
            data["name"] = str(sec.get("name"))
        holdings_sec = sec.get("holdings", None)
        if holdings_sec:
            # holdings can be list of strings or list of maps
            parsed: list[dict[str, Any]] = []
            for item in holdings_sec:
                if isinstance(item, str):
                    sym = item.strip().upper()
                    if sym:
                        parsed.append({"symbol": sym, "name": sym, "shares": None, "notes": ""})
                elif isinstance(item, dict) and item.get("symbol"):
                    parsed.append(
                        {
                            "symbol": str(item["symbol"]).strip().upper(),
                            "name": str(item.get("name") or item["symbol"]).strip(),
                            "shares": item.get("shares"),
                            "notes": str(item.get("notes") or ""),
                            "google_symbol": item.get("google_symbol"),
                        }
                    )
            if parsed:
                data["holdings"] = parsed

    # Normalize holdings
    clean: list[dict[str, Any]] = []
    for h in data.get("holdings") or []:
        if not isinstance(h, dict):
            continue
        sym = str(h.get("symbol") or "").strip().upper()
        if not sym:
            continue
        clean.append(
            {
                "symbol": sym,
                "name": str(h.get("name") or sym).strip(),
                "google_symbol": h.get("google_symbol"),
                "shares": h.get("shares"),
                "notes": str(h.get("notes") or ""),
            }
        )
    data["holdings"] = clean
    return data


def save_portfolio(data: dict[str, Any]) -> None:
    PORTFOLIO_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(data)
    payload["updated_at"] = datetime.now(tz=ET).isoformat()
    PORTFOLIO_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def google_finance_quote_url(symbol: str, google_symbol: str | None = None) -> str:
    """Best-effort Google Finance quote URL for a Yahoo-style symbol."""
    if google_symbol:
        # Accept already-formed paths like MES:CME_EMINIS or full URLs
        gs = str(google_symbol).strip()
        if gs.startswith("http"):
            return gs
        return f"https://www.google.com/finance/quote/{gs}?hl=en"

    s = symbol.strip().upper()
    # Futures: MES=F → search page (exchange codes vary on GF)
    if s.endswith("=F"):
        root = s[:-2]
        return f"https://www.google.com/finance/quote/{root}:CME_EMINIS?hl=en"
    # Crypto
    if s.endswith("-USD"):
        return f"https://www.google.com/finance/quote/{s.replace('-', '')}?hl=en"
    # Default equities — NASDAQ first; Google often redirects
    return f"https://www.google.com/finance/quote/{s}:NASDAQ?hl=en"


# ── Quote / deep dive ─────────────────────────────────────────────────────


@dataclass
class AssetDeepDive:
    symbol: str
    name: str
    price: Optional[float] = None
    prev_close: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    volume: Optional[float] = None
    avg_volume: Optional[float] = None
    change_5d_pct: Optional[float] = None
    bias: str = "—"
    flags: list[str] = field(default_factory=list)
    error: Optional[str] = None
    google_url: str = ""
    notes: str = ""
    shares: Optional[float] = None

    @property
    def market_value(self) -> Optional[float]:
        if self.price is None or self.shares is None:
            return None
        try:
            return float(self.price) * float(self.shares)
        except (TypeError, ValueError):
            return None


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def _bias_and_flags(
    *,
    price: Optional[float],
    prev_close: Optional[float],
    day_high: Optional[float],
    day_low: Optional[float],
    volume: Optional[float],
    avg_volume: Optional[float],
    change_pct: Optional[float],
    change_5d_pct: Optional[float],
) -> tuple[str, list[str]]:
    flags: list[str] = []
    bias = "FLAT"

    if change_pct is not None:
        if change_pct >= 0.35:
            bias = "BULL"
            flags.append("Strong green day")
        elif change_pct <= -0.35:
            bias = "BEAR"
            flags.append("Strong red day")
        elif change_pct > 0.05:
            bias = "BULL"
        elif change_pct < -0.05:
            bias = "BEAR"

    if price is not None and day_high is not None and day_low is not None and day_high > day_low:
        rng = day_high - day_low
        pos = (price - day_low) / rng
        if pos >= 0.9:
            flags.append("Near day high")
        elif pos <= 0.1:
            flags.append("Near day low")

    if volume is not None and avg_volume is not None and avg_volume > 0:
        ratio = volume / avg_volume
        if ratio >= 1.5:
            flags.append(f"Volume {ratio:.1f}x avg")
        elif ratio <= 0.5:
            flags.append("Light volume")

    if change_5d_pct is not None:
        if change_5d_pct >= 2.0:
            flags.append(f"5d +{change_5d_pct:.1f}%")
        elif change_5d_pct <= -2.0:
            flags.append(f"5d {change_5d_pct:.1f}%")

    if not flags:
        flags.append("No unusual flags")
    return bias, flags


def deep_dive_asset(holding: dict[str, Any]) -> AssetDeepDive:
    symbol = str(holding.get("symbol") or "").strip().upper()
    name = str(holding.get("name") or symbol)
    dive = AssetDeepDive(
        symbol=symbol,
        name=name,
        google_url=google_finance_quote_url(symbol, holding.get("google_symbol")),
        notes=str(holding.get("notes") or ""),
        shares=_safe_float(holding.get("shares")),
    )
    if not symbol:
        dive.error = "Missing symbol"
        return dive

    try:
        t = yf.Ticker(symbol)
        # Prefer 5d daily bars for prev close + 5d move
        hist = t.history(period="10d", interval="1d", auto_adjust=True)
        info_price = None
        try:
            fi = getattr(t, "fast_info", None)
            if fi is not None:
                info_price = _safe_float(getattr(fi, "last_price", None) or fi.get("lastPrice"))
        except Exception:
            info_price = None

        if hist is not None and not hist.empty:
            last = hist.iloc[-1]
            dive.price = info_price if info_price is not None else _safe_float(last.get("Close"))
            dive.day_high = _safe_float(last.get("High"))
            dive.day_low = _safe_float(last.get("Low"))
            dive.volume = _safe_float(last.get("Volume"))
            if len(hist) >= 2:
                dive.prev_close = _safe_float(hist.iloc[-2].get("Close"))
            if dive.price is not None and dive.prev_close not in (None, 0):
                dive.change = dive.price - dive.prev_close  # type: ignore[operator]
                dive.change_pct = (dive.change / dive.prev_close) * 100.0  # type: ignore[operator]
            if len(hist) >= 6:
                base = _safe_float(hist.iloc[-6].get("Close"))
                if base and dive.price is not None and base != 0:
                    dive.change_5d_pct = ((dive.price - base) / base) * 100.0
            # avg volume last up to 10 sessions
            vols = [_safe_float(v) for v in hist["Volume"].tolist()]
            vols = [v for v in vols if v is not None and v > 0]
            if vols:
                dive.avg_volume = sum(vols) / len(vols)
        elif info_price is not None:
            dive.price = info_price
        else:
            dive.error = "No quote data"
            return dive

        dive.bias, dive.flags = _bias_and_flags(
            price=dive.price,
            prev_close=dive.prev_close,
            day_high=dive.day_high,
            day_low=dive.day_low,
            volume=dive.volume,
            avg_volume=dive.avg_volume,
            change_pct=dive.change_pct,
            change_5d_pct=dive.change_5d_pct,
        )
    except Exception as exc:
        dive.error = str(exc)[:160]
    return dive


def run_portfolio_deep_dive(holdings: list[dict[str, Any]]) -> list[AssetDeepDive]:
    return [deep_dive_asset(h) for h in holdings]


# ── Formatting ────────────────────────────────────────────────────────────


def _fmt_px(v: Optional[float]) -> str:
    if v is None:
        return "—"
    if abs(v) >= 1000:
        return f"{v:,.2f}"
    if abs(v) >= 1:
        return f"{v:.2f}"
    return f"{v:.4f}"


def _fmt_chg(v: Optional[float], pct: Optional[float]) -> str:
    if v is None and pct is None:
        return "—"
    parts = []
    if v is not None:
        sign = "+" if v >= 0 else ""
        parts.append(f"{sign}{_fmt_px(v)}")
    if pct is not None:
        sign = "+" if pct >= 0 else ""
        parts.append(f"{sign}{pct:.2f}%")
    return " · ".join(parts)


def _fmt_vol(v: Optional[float]) -> str:
    if v is None:
        return "—"
    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"{v/1_000:.1f}K"
    return f"{v:.0f}"


def _dives_to_dataframe(dives: list[AssetDeepDive]) -> pd.DataFrame:
    rows = []
    for d in dives:
        rows.append(
            {
                "Symbol": d.symbol,
                "Name": d.name,
                "Last": d.price,
                "Change": d.change,
                "Change %": d.change_pct,
                "5d %": d.change_5d_pct,
                "Day low": d.day_low,
                "Day high": d.day_high,
                "Volume": d.volume,
                "Avg vol": d.avg_volume,
                "Bias": d.bias,
                "Flags": "; ".join(d.flags),
                "Shares": d.shares,
                "Mkt value": d.market_value,
                "Error": d.error or "",
            }
        )
    return pd.DataFrame(rows)


def _detect_updates(
    current: list[AssetDeepDive],
    prev: dict[str, Any] | None,
) -> list[str]:
    """Human-readable alerts when assets move or portfolio composition changes."""
    alerts: list[str] = []
    if not prev:
        return alerts
    prev_prices: dict[str, float] = prev.get("prices") or {}
    prev_syms: set[str] = set(prev.get("symbols") or [])
    cur_syms = {d.symbol for d in current}

    added = cur_syms - prev_syms
    removed = prev_syms - cur_syms
    for s in sorted(added):
        alerts.append(f"NEW holding in deep dive list: **{s}**")
    for s in sorted(removed):
        alerts.append(f"REMOVED from deep dive list: **{s}**")

    for d in current:
        if d.price is None or d.symbol not in prev_prices:
            continue
        old = prev_prices[d.symbol]
        if old == 0:
            continue
        move_pct = ((d.price - old) / old) * 100.0
        if abs(move_pct) >= 0.15:  # ~15 bps since last refresh
            sign = "+" if move_pct >= 0 else ""
            alerts.append(
                f"**{d.symbol}** moved {sign}{move_pct:.2f}% since last refresh "
                f"({_fmt_px(old)} → {_fmt_px(d.price)})"
            )
    return alerts


# ── UI ────────────────────────────────────────────────────────────────────


def _render_holdings_editor(portfolio: dict[str, Any]) -> None:
    if not is_current_user_admin():
        with candle_expander("Portfolio source notes", side="bull", expanded=False, kind="doc"):
            st.markdown(
                """
Google Finance **private portfolios are not publicly readable** (no official API).

This desk keeps a **mirrored list** of the CPRP Strategies Portfolio holdings so
we can deep-dive them live. Founder can edit symbols below so the list matches
your Google Finance portfolio.

Each asset still links out to its **Google Finance** quote page.
"""
            )
        return

    with candle_expander("Edit CPRP Strategies Portfolio (Founder)", side="bear", expanded=False, kind="folder"):
        st.caption(
            "Mirror your Google Finance portfolio here. Yahoo symbols for futures use the `=F` suffix "
            "(e.g. `MES=F`, `MNQ=F`, `MYM=F`). Equities: `AAPL`, `SPY`."
        )
        gf_url = st.text_input(
            "Google Finance portfolio / home URL",
            value=str(portfolio.get("google_finance_url") or GOOGLE_FINANCE_PORTFOLIO),
            key="mdd_gf_url",
        )
        notes = st.text_area(
            "Portfolio notes",
            value=str(portfolio.get("notes") or ""),
            key="mdd_notes",
            height=80,
        )
        # Editable table of holdings
        base_rows = portfolio.get("holdings") or []
        edit_df = pd.DataFrame(base_rows) if base_rows else pd.DataFrame(
            columns=["symbol", "name", "shares", "notes", "google_symbol"]
        )
        for col in ("symbol", "name", "shares", "notes", "google_symbol"):
            if col not in edit_df.columns:
                edit_df[col] = None
        edit_df = edit_df[["symbol", "name", "shares", "notes", "google_symbol"]]
        edited = st.data_editor(
            edit_df,
            num_rows="dynamic",
            use_container_width=True,
            key="mdd_holdings_editor",
            column_config={
                "symbol": st.column_config.TextColumn("Yahoo symbol", required=True),
                "name": st.column_config.TextColumn("Name"),
                "shares": st.column_config.NumberColumn("Shares / contracts", format="%.4f"),
                "notes": st.column_config.TextColumn("Notes"),
                "google_symbol": st.column_config.TextColumn("Google symbol (optional)"),
            },
        )
        bulk = st.text_area(
            "Or paste symbols (one per line or comma-separated) to replace list",
            value="",
            key="mdd_bulk",
            height=80,
            placeholder="MES=F\nMNQ=F\nMYM=F\nSPY",
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Save portfolio", type="primary", use_container_width=True, key="mdd_save"):
                holdings: list[dict[str, Any]] = []
                if bulk.strip():
                    raw = bulk.replace(",", "\n").splitlines()
                    for line in raw:
                        sym = line.strip().upper()
                        if not sym:
                            continue
                        holdings.append({"symbol": sym, "name": sym, "shares": None, "notes": ""})
                else:
                    for _, row in edited.iterrows():
                        sym = str(row.get("symbol") or "").strip().upper()
                        if not sym or sym == "NAN":
                            continue
                        shares = row.get("shares")
                        try:
                            shares_f = float(shares) if shares is not None and str(shares) not in ("", "nan", "None") else None
                        except (TypeError, ValueError):
                            shares_f = None
                        holdings.append(
                            {
                                "symbol": sym,
                                "name": str(row.get("name") or sym).strip(),
                                "shares": shares_f,
                                "notes": str(row.get("notes") or ""),
                                "google_symbol": (
                                    str(row.get("google_symbol")).strip()
                                    if row.get("google_symbol") not in (None, "", "nan")
                                    else None
                                ),
                            }
                        )
                payload = {
                    "name": portfolio.get("name") or "CPRP Strategies Portfolio",
                    "source": "Google Finance (mirrored holdings)",
                    "google_finance_url": gf_url.strip() or GOOGLE_FINANCE_PORTFOLIO,
                    "notes": notes,
                    "holdings": holdings,
                }
                save_portfolio(payload)
                st.success(f"Saved {len(holdings)} holdings to {PORTFOLIO_PATH.name}")
                st.rerun()
        with c2:
            st.caption(f"File: `{PORTFOLIO_PATH}`")


def _render_dive_cards(dives: list[AssetDeepDive]) -> None:
    if not dives:
        st.info("No holdings configured yet. Founder: open **Edit CPRP Strategies Portfolio**.")
        return

    # Summary metrics
    ok = [d for d in dives if d.error is None and d.price is not None]
    up = sum(1 for d in ok if (d.change_pct or 0) > 0)
    down = sum(1 for d in ok if (d.change_pct or 0) < 0)
    flat = len(ok) - up - down
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Assets deep-dived", f"{len(ok)}/{len(dives)}")
    m2.metric("Green", str(up))
    m3.metric("Red", str(down))
    m4.metric("Flat", str(flat))

    # Table first for scannability
    df = _dives_to_dataframe(dives)
    show = df.drop(columns=["Error"], errors="ignore")
    st.dataframe(
        show,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Last": st.column_config.NumberColumn(format="%.2f"),
            "Change": st.column_config.NumberColumn(format="%+.2f"),
            "Change %": st.column_config.NumberColumn(format="%+.2f%%"),
            "5d %": st.column_config.NumberColumn(format="%+.2f%%"),
            "Day low": st.column_config.NumberColumn(format="%.2f"),
            "Day high": st.column_config.NumberColumn(format="%.2f"),
            "Volume": st.column_config.NumberColumn(format="%.0f"),
            "Avg vol": st.column_config.NumberColumn(format="%.0f"),
            "Shares": st.column_config.NumberColumn(format="%.4f"),
            "Mkt value": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    desk_section("Per-asset deep dive", side="bull")
    cols = st.columns(2)
    for i, d in enumerate(dives):
        with cols[i % 2]:
            side = "bull" if d.bias == "BULL" else ("bear" if d.bias == "BEAR" else "bull")
            with candle_expander(f"{d.symbol} · {d.name}", side=side, expanded=False, kind="page"):
                if d.error:
                    st.error(d.error)
                else:
                    st.markdown(
                        f"**Last** `{_fmt_px(d.price)}` · **Day** `{_fmt_chg(d.change, d.change_pct)}`  \n"
                        f"**Range** `{_fmt_px(d.day_low)}` – `{_fmt_px(d.day_high)}` · "
                        f"**5d** `{_fmt_chg(None, d.change_5d_pct)}`  \n"
                        f"**Vol** `{_fmt_vol(d.volume)}` (avg `{_fmt_vol(d.avg_volume)}`) · "
                        f"**Bias** `{d.bias}`"
                    )
                    st.markdown("**Flags:** " + " · ".join(f"`{f}`" for f in d.flags))
                    if d.shares is not None:
                        st.caption(f"Position size: {d.shares} · Mkt value ≈ {_fmt_px(d.market_value)}")
                    if d.notes:
                        st.caption(d.notes)
                st.link_button(
                    link_label(f"Google Finance · {d.symbol}"),
                    d.google_url or GOOGLE_FINANCE_HOME,
                    use_container_width=True,
                    type="secondary",
                    key=f"mdd_gf_{d.symbol}_{i}",
                )


@st.fragment(run_every=timedelta(seconds=AUTO_REFRESH_SEC))
def _auto_deep_dive_fragment() -> None:
    """Re-runs every 60s: re-load holdings + live quote deep dive."""
    now = datetime.now(tz=ET)
    portfolio = load_portfolio()
    holdings = portfolio.get("holdings") or []

    with st.spinner("Running portfolio deep dive…"):
        dives = run_portfolio_deep_dive(holdings)

    prev = st.session_state.get(_KEY_SNAPSHOT)
    alerts = _detect_updates(dives, prev if isinstance(prev, dict) else None)

    st.session_state[_KEY_LAST] = now.isoformat()
    st.session_state[_KEY_TICK] = int(st.session_state.get(_KEY_TICK, 0)) + 1
    st.session_state[_KEY_SNAPSHOT] = {
        "symbols": [d.symbol for d in dives],
        "prices": {d.symbol: d.price for d in dives if d.price is not None},
        "at": now.isoformat(),
    }

    st.caption(
        f"Deep dive refresh **#{int(st.session_state.get(_KEY_TICK, 0))}** · "
        f"{now.strftime('%H:%M:%S ET')} · auto every **{AUTO_REFRESH_SEC}s** · "
        f"{len(holdings)} holdings"
    )

    if alerts:
        desk_section("Updates since last refresh", side="bear")
        for a in alerts:
            st.markdown(f"- {a}")
    else:
        st.caption("No material price or holdings changes since last refresh.")

    _render_dive_cards(dives)


def render_market_deep_dive_panel() -> None:
    """Full Market Deep Dive page for the CPRP Strategies Portfolio."""
    portfolio = load_portfolio()
    name = str(portfolio.get("name") or "CPRP Strategies Portfolio")
    gf_url = str(portfolio.get("google_finance_url") or GOOGLE_FINANCE_PORTFOLIO)

    page_hero(
        "Market Deep Dive",
        f"**{name}** · mirrored from Google Finance · live quote deep dive every {AUTO_REFRESH_SEC}s",
        side="bull",
        desk_tag="MARKET DESK · PORTFOLIO DEEP DIVE",
    )

    st.markdown(
        f"""
Stay on the pulse of the **CPRP Strategies** book. Holdings mirror your Google Finance
portfolio (private books can't be scraped). Every **{AUTO_REFRESH_SEC} seconds** the desk
re-quotes each asset and flags day structure, volume, and multi-day moves.
"""
    )

    b1, b2, b3 = st.columns(3)
    with b1:
        st.link_button(
            link_label("Open Google Finance portfolio"),
            gf_url,
            use_container_width=True,
            type="primary",
        )
    with b2:
        st.link_button(
            link_label("Google Finance home"),
            GOOGLE_FINANCE_HOME,
            use_container_width=True,
            type="secondary",
        )
    with b3:
        if st.button("Deep dive now", use_container_width=True, type="secondary", key="mdd_force"):
            # Force fragment remount by clearing last snapshot time
            st.session_state.pop(_KEY_LAST, None)
            st.rerun()

    if portfolio.get("notes"):
        st.info(str(portfolio["notes"]))

    _render_holdings_editor(portfolio)

    desk_section("Live portfolio deep dive", side="bull")
    _auto_deep_dive_fragment()

    render_third_party_disclosure(expanded=False)
    render_disclosure(expanded=False)
    st.caption(
        "Quotes via Yahoo Finance (delayed). Google Finance links are third-party; "
        "not affiliated. Not financial advice — educational desk tool only."
    )
