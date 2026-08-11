"""
Micro Futures News panel — Yahoo Finance headlines for MES / MNQ / MYM.

Yahoo rarely attaches a dedicated news stream to micro continuous tickers
(MES=F, MNQ=F, MYM=F). When a micro symbol has no articles, we fall back to
the related full-size continuous futures (ES=F, NQ=F, YM=F) and equity
proxies (SPY, QQQ, DIA) that drive the same underlyings — labeled clearly
so members know the source symbol.

No partnership with Yahoo Finance. Headlines link out to Yahoo; we do not
republish full article text.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

import streamlit as st
import yfinance as yf

from config import INSTRUMENTS, PROTOCOL_SHORT
from disclosure import render_disclosure, render_third_party_disclosure
from wallstreet_ui import candle_expander, desk_section, link_label, page_hero

ET = ZoneInfo("America/New_York")

# Micro → Yahoo symbols to query (primary first, then related market news)
MICRO_NEWS_QUERIES: dict[str, dict[str, Any]] = {
    "MES": {
        "primary": "MES=F",
        "related": ["ES=F", "SPY"],  # full-size S&P + ETF proxy
        "label": "Micro E-mini S&P 500",
        "index": "S&P 500",
    },
    "MNQ": {
        "primary": "MNQ=F",
        "related": ["NQ=F", "QQQ"],
        "label": "Micro E-mini Nasdaq-100",
        "index": "Nasdaq-100",
    },
    "MYM": {
        "primary": "MYM=F",
        "related": ["YM=F", "DIA"],
        "label": "Micro E-mini Dow",
        "index": "Dow Jones",
    },
}

YAHOO_QUOTE_URL = "https://finance.yahoo.com/quote/{symbol}"
NEWS_PER_SYMBOL = 12
CACHE_TTL_SEC = 180  # 3 minutes


@dataclass
class NewsArticle:
    id: str
    title: str
    summary: str
    url: str
    publisher: str
    published: Optional[datetime]
    thumbnail: str
    source_symbol: str  # Yahoo ticker that returned this item
    micro: str  # MES / MNQ / MYM tab
    related_via: str = ""  # e.g. "via ES=F" when micro had no feed


def _parse_pub(raw: Any) -> Optional[datetime]:
    if not raw:
        return None
    if isinstance(raw, (int, float)):
        # some older payloads use epoch seconds
        try:
            return datetime.fromtimestamp(int(raw), tz=timezone.utc)
        except Exception:
            return None
    s = str(raw).strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _url_from_content(content: dict) -> str:
    for key in ("clickThroughUrl", "canonicalUrl"):
        node = content.get(key)
        if isinstance(node, dict) and node.get("url"):
            return str(node["url"])
        if isinstance(node, str) and node.startswith("http"):
            return node
    preview = content.get("previewUrl")
    if isinstance(preview, str) and preview.startswith("http"):
        return preview
    return ""


def _thumb_from_content(content: dict) -> str:
    thumb = content.get("thumbnail") or {}
    if isinstance(thumb, dict):
        if thumb.get("originalUrl"):
            return str(thumb["originalUrl"])
        res = thumb.get("resolutions") or []
        if res and isinstance(res[0], dict) and res[0].get("url"):
            return str(res[0]["url"])
    return ""


def _normalize_item(raw: dict, *, micro: str, source_symbol: str, related_via: str) -> Optional[NewsArticle]:
    """Map yfinance news payload (new nested or legacy flat) to NewsArticle."""
    if not isinstance(raw, dict):
        return None

    # New yfinance shape: { id, content: { title, summary, ... } }
    content = raw.get("content") if isinstance(raw.get("content"), dict) else raw
    title = (content.get("title") or raw.get("title") or "").strip()
    if not title:
        return None

    url = _url_from_content(content) if content is not raw else ""
    if not url:
        url = (
            content.get("link")
            or raw.get("link")
            or content.get("url")
            or ""
        )
    url = str(url).strip()
    if not url:
        # Still show headline with Yahoo quote page as destination
        url = YAHOO_QUOTE_URL.format(symbol=source_symbol)

    summary = (
        content.get("summary")
        or content.get("description")
        or raw.get("summary")
        or ""
    )
    summary = str(summary).strip()

    publisher = ""
    prov = content.get("provider") or raw.get("publisher")
    if isinstance(prov, dict):
        publisher = str(prov.get("displayName") or prov.get("name") or "")
    elif isinstance(prov, str):
        publisher = prov

    pub = _parse_pub(
        content.get("pubDate")
        or content.get("displayTime")
        or raw.get("providerPublishTime")
        or raw.get("pubDate")
    )

    aid = str(
        content.get("id")
        or raw.get("id")
        or raw.get("uuid")
        or url
        or title
    )

    return NewsArticle(
        id=aid,
        title=title,
        summary=summary,
        url=url,
        publisher=publisher or "Yahoo Finance",
        published=pub,
        thumbnail=_thumb_from_content(content) if content is not raw else str(raw.get("thumbnail") or ""),
        source_symbol=source_symbol,
        micro=micro,
        related_via=related_via,
    )


@st.cache_data(ttl=CACHE_TTL_SEC, show_spinner=False)
def _fetch_yahoo_news(symbol: str, count: int = NEWS_PER_SYMBOL) -> list[dict]:
    """Raw news list for a Yahoo symbol (cached)."""
    ticker = yf.Ticker(symbol)
    try:
        items = ticker.get_news(count=count)
    except TypeError:
        items = ticker.get_news()
    except Exception:
        items = None
    if not items:
        items = ticker.news or []
    return list(items) if items else []


def fetch_micro_news(micro: str, *, max_articles: int = 15) -> list[NewsArticle]:
    """
    Collect Yahoo Finance news for one micro.
    Prefer MES=F / MNQ=F / MYM=F; if empty, use related full-size / ETF feeds.
    """
    cfg = MICRO_NEWS_QUERIES.get(micro)
    if not cfg:
        return []

    collected: list[NewsArticle] = []
    seen: set[str] = set()

    def _ingest(symbol: str, related_via: str = "") -> int:
        added = 0
        for raw in _fetch_yahoo_news(symbol):
            art = _normalize_item(
                raw,
                micro=micro,
                source_symbol=symbol,
                related_via=related_via,
            )
            if not art:
                continue
            key = art.url or art.id or art.title
            if key in seen:
                continue
            seen.add(key)
            collected.append(art)
            added += 1
            if len(collected) >= max_articles:
                break
        return added

    primary = cfg["primary"]
    n_primary = _ingest(primary, related_via="")
    # Always enrich with related market news (same underlying) when primary is thin
    if n_primary < 4:
        for rel in cfg["related"]:
            if len(collected) >= max_articles:
                break
            via = f"related · {rel} (same underlying as {primary})"
            _ingest(rel, related_via=via)
    else:
        # Light related fill for broader tape (deduped)
        for rel in cfg["related"][:1]:
            if len(collected) >= max_articles:
                break
            _ingest(rel, related_via=f"related · {rel}")

    # Newest first
    collected.sort(
        key=lambda a: a.published or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return collected[:max_articles]


def fetch_all_micro_news(*, max_per: int = 12) -> dict[str, list[NewsArticle]]:
    return {m: fetch_micro_news(m, max_articles=max_per) for m in ("MES", "MNQ", "MYM")}


def _fmt_when(dt: Optional[datetime]) -> str:
    if not dt:
        return "—"
    try:
        local = dt.astimezone(ET)
        return local.strftime("%b %d, %Y  %H:%M ET")
    except Exception:
        return str(dt)[:16]


def _render_article_card(art: NewsArticle, *, key: str) -> None:
    via = f" · {art.related_via}" if art.related_via else ""
    with st.container(border=True):
        c_img, c_body = st.columns([1, 4], gap="medium")
        with c_img:
            if art.thumbnail:
                try:
                    st.image(art.thumbnail, use_container_width=True)
                except Exception:
                    st.caption("📰")
            else:
                st.markdown(
                    "<div style='height:72px;display:flex;align-items:center;justify-content:center;"
                    "background:rgba(201,168,76,0.08);border:1px solid rgba(201,168,76,0.2);"
                    "color:#C9A84C;font-size:1.6rem;'>📰</div>",
                    unsafe_allow_html=True,
                )
        with c_body:
            st.markdown(f"**{art.title}**")
            meta = (
                f"`{art.source_symbol}` · {art.publisher} · {_fmt_when(art.published)}{via}"
            )
            st.caption(meta)
            if art.summary:
                st.write(art.summary[:420] + ("…" if len(art.summary) > 420 else ""))
            st.link_button(
                link_label("Read on Yahoo Finance"),
                art.url,
                use_container_width=True,
                key=key,
            )


def render_micro_futures_news_panel() -> None:
    """Full-page Micro Futures News desk (Yahoo Finance)."""
    page_hero(
        "Micro Futures News",
        "Yahoo Finance headlines for MES=F · MNQ=F · MYM=F and related market tape",
        side="bull",
        desk_tag="NEWS DESK · YAHOO FINANCE · MICROS",
    )

    st.caption(
        "Headlines from **Yahoo Finance** for CPRP micros. "
        "Yahoo often has little/no dedicated news on micro tickers — when that happens we show "
        "**related full-size futures** (ES=F / NQ=F / YM=F) and liquid ETFs (SPY / QQQ / DIA) "
        "that move the same indexes. Open any story on Yahoo for the full article."
    )

    render_disclosure(expanded=False)
    render_third_party_disclosure(expanded=False)

    desk_section("Yahoo quote pages", side="bull")
    q1, q2, q3 = st.columns(3)
    for col, short in zip((q1, q2, q3), ("MES", "MNQ", "MYM")):
        inst = INSTRUMENTS[short]
        with col:
            st.link_button(
                link_label(f"{short} · {inst.symbol}"),
                YAHOO_QUOTE_URL.format(symbol=inst.symbol),
                use_container_width=True,
                type="primary" if short == "MES" else "secondary",
            )

    desk_section("Live headlines", side="bear")
    c_ref, c_n = st.columns([1, 3])
    with c_ref:
        if st.button("Refresh news", use_container_width=True, key="mfn_refresh"):
            _fetch_yahoo_news.clear()
            st.rerun()
    with c_n:
        st.caption(f"Cache ~{CACHE_TTL_SEC // 60} min · {PROTOCOL_SHORT} desk display only · not a broker feed")

    with st.spinner("Pulling Yahoo Finance news for MES / MNQ / MYM…"):
        all_news = fetch_all_micro_news(max_per=12)

    tabs = st.tabs(
        [
            f"● MES (MES=F)",
            f"● MNQ (MNQ=F)",
            f"● MYM (MYM=F)",
            "● Combined tape",
        ]
    )

    for tab, short in zip(tabs[:3], ("MES", "MNQ", "MYM")):
        with tab:
            cfg = MICRO_NEWS_QUERIES[short]
            inst = INSTRUMENTS[short]
            st.markdown(
                f"**{short}** · `{cfg['primary']}` · {cfg['label']} · {cfg['index']}  \n"
                f"Related feeds if micro is empty: "
                + " · ".join(f"`{r}`" for r in cfg["related"])
            )
            articles = all_news.get(short) or []
            if not articles:
                st.warning(
                    f"No Yahoo headlines available right now for **{cfg['primary']}** "
                    f"or related symbols. Try **Refresh news**, or open the Yahoo quote page."
                )
                st.link_button(
                    link_label(f"Open {cfg['primary']} on Yahoo"),
                    YAHOO_QUOTE_URL.format(symbol=cfg["primary"]),
                    use_container_width=True,
                    key=f"mfn_empty_{short}",
                )
            else:
                primary_n = sum(1 for a in articles if a.source_symbol == cfg["primary"])
                if primary_n == 0:
                    st.info(
                        f"Yahoo has **no dedicated news stream on `{cfg['primary']}`** right now. "
                        f"Showing **related {cfg['index']}** market news "
                        f"({', '.join(cfg['related'])}) — same underlying risk as {short}."
                    )
                st.caption(f"{len(articles)} articles · newest first")
                for i, art in enumerate(articles):
                    _render_article_card(art, key=f"mfn_{short}_{i}_{art.id[:24]}")

    with tabs[3]:
        st.markdown(
            "**Combined** MES · MNQ · MYM tape (deduped by URL, newest first)."
        )
        combined: list[NewsArticle] = []
        seen_u: set[str] = set()
        for short in ("MES", "MNQ", "MYM"):
            for art in all_news.get(short) or []:
                u = art.url or art.id
                if u in seen_u:
                    continue
                seen_u.add(u)
                combined.append(art)
        combined.sort(
            key=lambda a: a.published or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        if not combined:
            st.warning("No combined headlines available. Try Refresh news.")
        else:
            st.caption(f"{len(combined)} unique articles")
            for i, art in enumerate(combined[:24]):
                st.caption(f"Tagged · **{art.micro}**")
                _render_article_card(art, key=f"mfn_all_{i}_{art.id[:24]}")

    with candle_expander("How this feed works", side="bull", expanded=False, kind="doc"):
        st.markdown(
            """
| Micro | Yahoo primary | Related market news |
|-------|---------------|---------------------|
| **MES** | `MES=F` | `ES=F` (E-mini S&P), `SPY` |
| **MNQ** | `MNQ=F` | `NQ=F` (E-mini Nasdaq), `QQQ` |
| **MYM** | `MYM=F` | `YM=F` (E-mini Dow), `DIA` |

- Data: **Yahoo Finance** via `yfinance` (same stack as Session Selector quotes).  
- We show **title, summary, publisher, time** and a **Read on Yahoo Finance** link.  
- Full article text stays on Yahoo (we do not scrape/republish bodies).  
- **CPRP Strategies is not affiliated with Yahoo Finance.**
"""
        )
