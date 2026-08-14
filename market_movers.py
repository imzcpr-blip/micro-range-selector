"""
What's Moving the Market? — high-impact Business / Politics / Macro / Micro topics.

Pulls free public headlines (Yahoo Finance news + public RSS), filters for
market-moving themes that matter to US equity-index micros (MES / MNQ / MYM),
and assigns:
  • Category  — Business · Politics · Macro · Micro
  • Sentiment — BULL / BEAR / MIXED  (potential risk tone for US equities)
  • Influence — HIGH / ELEVATED / WATCH  (how much it can move the tape)

Heuristic keyword scoring only — educational desk context, not signals.
No partnership with Yahoo, Reuters, CNBC, or any feed source.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any, Optional
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import streamlit as st
import yfinance as yf

from disclosure import render_disclosure, render_third_party_disclosure
from wallstreet_ui import candle_expander, desk_section, link_label, page_hero

ET_TZ = ZoneInfo("America/New_York")

AUTO_REFRESH_SEC = 60
CACHE_TTL_SEC = 90
_KEY_TICK = "wmm_refresh_tick"
_KEY_LAST = "wmm_last_refresh"

# Public RSS sources (best-effort; failures are skipped)
RSS_FEEDS: list[tuple[str, str]] = [
    ("CNBC Top News", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"),
    ("CNBC Economy", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258"),
    ("CNBC Politics", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000113"),
    ("MarketWatch Top", "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("MarketWatch Markets", "https://feeds.marketwatch.com/marketwatch/marketpulse/"),
]

# Yahoo symbols whose related news often moves equity-index futures
YF_NEWS_SYMBOLS = ("SPY", "QQQ", "ES=F", "NQ=F", "^VIX", "TLT", "DX-Y.NYB")

# ── Keyword maps (lowercase) ──────────────────────────────────────────────

HIGH_INFLUENCE = (
    "fomc", "federal reserve", "fed chair", "powell", "rate decision", "rate cut",
    "rate hike", "interest rate", "cpi", "pce", "inflation report", "nonfarm",
    "non-farm", "payrolls", "jobs report", "unemployment", "gdp", "recession",
    "tariff", "trade war", "sanctions", "war ", "invasion", "geopolit",
    "debt ceiling", "government shutdown", "default", "bank failure",
    "emergency rate", "black swan", "circuit breaker",
)

ELEVATED_INFLUENCE = (
    "retail sales", "ism ", "pmi", "consumer confidence", "housing starts",
    "bea ", "treasury yield", "10-year", "bond yield", "oil price", "opec",
    "earnings", "mega-cap", "magnificent", "nvidia", "apple", "microsoft",
    "amazon", "alphabet", "tesla", "meta ", "guidance", "layoffs",
    "bank stress", "credit", "liquidity", "dollar index", "dxy",
)

MACRO_KW = (
    "fed", "fomc", "inflation", "cpi", "pce", "gdp", "recession", "rate cut",
    "rate hike", "interest rate", "jobs", "payroll", "unemployment", "yield",
    "treasury", "macro", "economy", "economic", "soft landing", "hard landing",
    "stimulus", "quantitative",
)

POLITICS_KW = (
    "white house", "congress", "senate", "house ", "election", "president",
    "trump", "biden", "harris", "tariff", "trade war", "sanctions", "regulation",
    "antitrust", "shutdown", "debt ceiling", "bill ", "legislation", "policy",
    "geopolit", "war ", "nato", "china", "beijing", "moscow", "ukraine", "israel",
)

BUSINESS_KW = (
    "earnings", "revenue", "profit", "ceo", "ipo", "merger", "acquisition",
    "bankruptcy", "layoff", "guidance", "stock ", "shares", "buyback",
    "dividend", "sec ", "lawsuit", "settlement", "bank ", "tech ",
)

MICRO_KW = (
    "futures", "s&p", "s&p 500", "nasdaq", "dow ", "e-mini", "emini",
    "micro e-mini", "vix", "options", "volatility", "index futures",
    "equity futures", "wall street", "session", "premarket", "after-hours",
)

BULL_KW = (
    "rate cut", "cuts rates", "dovish", "soft landing", "cooling inflation",
    "disinflation", "stronger than expected earnings", "beats estimates",
    "beat expectations", "record high", "all-time high", "risk-on", "rally",
    "surge", "soar", "jumps", "gains", "optimism", "stimulus", "ceasefire",
    "peace deal", "trade deal", "deal reached", "better-than-expected",
    "cooling cpi", "below expectations inflation", "labor market cools",
    "earnings beat", "beat lifts", "futures rise", "futures jump", "stocks rise",
)

BEAR_KW = (
    "rate hike", "hikes rates", "hawkish", "recession", "stagflation",
    "hotter inflation", "higher than expected inflation", "misses estimates",
    "miss expectations", "risk-off", "selloff", "sell-off", "plunge",
    "tumble", "slump", "crash", "default", "shutdown", "war ", "escalat",
    "tariff", "sanctions", "bank failure", "layoffs", "weaker than expected",
    "worse than expected", "fear", "panic", "volatility spike", "vix spike",
    "yields jump", "dollar surge", "lost jobs", "jobs lost", "job losses",
    "disappointing jobs", "disappointing cpi", "unexpectedly lost",
    "cuts forecast", "downgrade", "contraction",
)


@dataclass
class MarketTopic:
    title: str
    summary: str
    link: str
    source: str
    published: Optional[datetime]
    category: str  # Business | Politics | Macro | Micro
    sentiment: str  # BULL | BEAR | MIXED
    influence: str  # HIGH | ELEVATED | WATCH
    influence_score: float
    sentiment_score: float  # -1..+1
    why: str
    tags: list[str] = field(default_factory=list)


def _now_et() -> datetime:
    return datetime.now(tz=ET_TZ)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _contains_any(text: str, words: tuple[str, ...]) -> list[str]:
    hits = []
    for w in words:
        if w.strip() and w in text:
            hits.append(w.strip())
    return hits


def _parse_rss_date(raw: str | None) -> Optional[datetime]:
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ET_TZ)
        return dt.astimezone(ET_TZ)
    except Exception:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt.astimezone(ET_TZ)
        except Exception:
            return None


def _fetch_url(url: str, timeout: int = 8) -> bytes:
    req = Request(
        url,
        headers={
            "User-Agent": "CPRP-Strategies-Desk/1.0 (+educational; local Streamlit)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
        method="GET",
    )
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — public RSS only
        return resp.read()


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _parse_rss_items(xml_bytes: bytes, source: str, limit: int = 25) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return items

    # RSS 2.0 channel/item or Atom entry
    candidates = []
    for el in root.iter():
        name = _local(el.tag).lower()
        if name in {"item", "entry"}:
            candidates.append(el)

    for el in candidates[:limit]:
        title = ""
        link = ""
        summary = ""
        published_raw = None
        for child in el:
            n = _local(child.tag).lower()
            if n == "title" and child.text:
                title = child.text.strip()
            elif n == "link":
                if child.text and child.text.strip():
                    link = child.text.strip()
                elif child.attrib.get("href"):
                    link = child.attrib["href"].strip()
            elif n in {"description", "summary", "content"} and (child.text or len(child)):
                summary = (child.text or "").strip()
                if not summary and len(list(child)):
                    summary = "".join(child.itertext()).strip()
            elif n in {"pubdate", "published", "updated", "date"} and child.text:
                published_raw = child.text.strip()
        if not title:
            continue
        # Strip simple HTML
        summary = re.sub(r"<[^>]+>", " ", summary)
        summary = re.sub(r"\s+", " ", summary).strip()
        items.append(
            {
                "title": title,
                "link": link,
                "summary": summary[:400],
                "source": source,
                "published": _parse_rss_date(published_raw),
            }
        )
    return items


def _yahoo_news_items(symbol: str, limit: int = 12) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        t = yf.Ticker(symbol)
        news = getattr(t, "news", None) or []
    except Exception:
        return out
    for n in news[:limit]:
        # yfinance shapes vary (content dict vs flat)
        content = n.get("content") if isinstance(n.get("content"), dict) else None
        if content:
            title = str(content.get("title") or "").strip()
            summary = str(content.get("summary") or content.get("description") or "").strip()
            link = ""
            cu = content.get("canonicalUrl") or content.get("clickThroughUrl") or {}
            if isinstance(cu, dict):
                link = str(cu.get("url") or "")
            provider = content.get("provider") or {}
            source = str(provider.get("displayName") or f"Yahoo · {symbol}")
            pub = None
            pub_raw = content.get("pubDate") or content.get("displayTime")
            if pub_raw:
                pub = _parse_rss_date(str(pub_raw))
        else:
            title = str(n.get("title") or "").strip()
            summary = str(n.get("summary") or n.get("publisher") or "").strip()
            link = str(n.get("link") or "")
            source = str(n.get("publisher") or f"Yahoo · {symbol}")
            pub = None
            if n.get("providerPublishTime"):
                try:
                    pub = datetime.fromtimestamp(int(n["providerPublishTime"]), tz=ET_TZ)
                except Exception:
                    pub = None
        if not title:
            continue
        out.append(
            {
                "title": title,
                "link": link,
                "summary": summary[:400],
                "source": source,
                "published": pub,
            }
        )
    return out


def classify_and_score(item: dict[str, Any]) -> Optional[MarketTopic]:
    title = str(item.get("title") or "")
    summary = str(item.get("summary") or "")
    blob = _norm(f"{title}. {summary}")
    if len(blob) < 12:
        return None

    high_hits = _contains_any(blob, HIGH_INFLUENCE)
    elev_hits = _contains_any(blob, ELEVATED_INFLUENCE)
    macro_hits = _contains_any(blob, MACRO_KW)
    pol_hits = _contains_any(blob, POLITICS_KW)
    biz_hits = _contains_any(blob, BUSINESS_KW)
    micro_hits = _contains_any(blob, MICRO_KW)
    bull_hits = _contains_any(blob, BULL_KW)
    bear_hits = _contains_any(blob, BEAR_KW)

    # Influence
    if high_hits:
        influence = "HIGH"
        influence_score = 0.85 + min(0.15, 0.03 * len(high_hits))
    elif elev_hits:
        influence = "ELEVATED"
        influence_score = 0.55 + min(0.2, 0.04 * len(elev_hits))
    elif macro_hits or pol_hits:
        influence = "WATCH"
        influence_score = 0.35 + min(0.15, 0.03 * (len(macro_hits) + len(pol_hits)))
    else:
        # Low market relevance — drop unless micro/business with some signal
        if not (biz_hits or micro_hits):
            return None
        if not (bull_hits or bear_hits):
            return None
        influence = "WATCH"
        influence_score = 0.28

    # Category by strongest signal
    scores = {
        "Macro": len(macro_hits) * 2 + (2 if high_hits and any(h in MACRO_KW for h in high_hits) else 0),
        "Politics": len(pol_hits) * 2,
        "Business": len(biz_hits) * 2,
        "Micro": len(micro_hits) * 2 + 1,  # slight tilt for futures/index tape
    }
    # Boost Macro for classic high-impact data
    if any(k in blob for k in ("fomc", "cpi", "pce", "nonfarm", "payroll", "gdp", "fed ")):
        scores["Macro"] += 3
    if any(k in blob for k in ("tariff", "election", "congress", "shutdown", "sanctions", "war ")):
        scores["Politics"] += 3
    category = max(scores, key=scores.get)  # type: ignore[arg-type]
    if scores[category] == 0:
        category = "Business"

    # Sentiment
    bull_s = float(len(bull_hits))
    bear_s = float(len(bear_hits))
    # Soft adjustments for classic phrases
    if "rate cut" in blob or "dovish" in blob:
        bull_s += 1.5
    if "rate hike" in blob or "hawkish" in blob:
        bear_s += 1.5
    if "tariff" in blob or "trade war" in blob:
        bear_s += 1.2
    if "ceasefire" in blob or "peace" in blob:
        bull_s += 1.0

    if bull_s <= 0 and bear_s <= 0:
        sentiment = "MIXED"
        sentiment_score = 0.0
    elif bull_s > bear_s * 1.15:
        sentiment = "BULL"
        sentiment_score = min(1.0, (bull_s - bear_s) / max(bull_s + bear_s, 1.0))
    elif bear_s > bull_s * 1.15:
        sentiment = "BEAR"
        sentiment_score = -min(1.0, (bear_s - bull_s) / max(bull_s + bear_s, 1.0))
    else:
        sentiment = "MIXED"
        sentiment_score = (bull_s - bear_s) / max(bull_s + bear_s, 1.0)

    why_bits = []
    if high_hits:
        why_bits.append("high-impact macro/policy keywords: " + ", ".join(high_hits[:4]))
    elif elev_hits:
        why_bits.append("elevated market drivers: " + ", ".join(elev_hits[:4]))
    if bull_hits:
        why_bits.append("bullish tone: " + ", ".join(bull_hits[:3]))
    if bear_hits:
        why_bits.append("bearish tone: " + ", ".join(bear_hits[:3]))
    if not why_bits:
        why_bits.append("contextual business/market coverage")

    tags = list(dict.fromkeys(high_hits + elev_hits + macro_hits[:2] + pol_hits[:2]))[:8]

    return MarketTopic(
        title=title.strip(),
        summary=summary.strip(),
        link=str(item.get("link") or ""),
        source=str(item.get("source") or "Wire"),
        published=item.get("published"),
        category=category,
        sentiment=sentiment,
        influence=influence,
        influence_score=float(influence_score),
        sentiment_score=float(sentiment_score),
        why="; ".join(why_bits),
        tags=tags,
    )


@st.cache_data(ttl=CACHE_TTL_SEC, show_spinner=False)
def collect_market_topics(max_topics: int = 18) -> list[dict[str, Any]]:
    """Fetch + score topics; return serializable dicts for Streamlit cache."""
    raw_items: list[dict[str, Any]] = []

    for name, url in RSS_FEEDS:
        try:
            xml_bytes = _fetch_url(url)
            raw_items.extend(_parse_rss_items(xml_bytes, source=name, limit=20))
        except Exception:
            continue

    for sym in YF_NEWS_SYMBOLS:
        try:
            raw_items.extend(_yahoo_news_items(sym, limit=10))
        except Exception:
            continue

    # Dedupe by normalized title
    seen: set[str] = set()
    topics: list[MarketTopic] = []
    for item in raw_items:
        key = _norm(str(item.get("title") or ""))[:160]
        if not key or key in seen:
            continue
        seen.add(key)
        topic = classify_and_score(item)
        if topic is None:
            continue
        # Keep only material influence for the desk board
        if topic.influence_score < 0.28:
            continue
        topics.append(topic)

    # Rank: influence first, then |sentiment|, then recency
    def sort_key(t: MarketTopic) -> tuple:
        pub = t.published.timestamp() if t.published else 0.0
        return (t.influence_score, abs(t.sentiment_score), pub)

    topics.sort(key=sort_key, reverse=True)
    topics = topics[:max_topics]

    return [
        {
            "title": t.title,
            "summary": t.summary,
            "link": t.link,
            "source": t.source,
            "published": t.published.isoformat() if t.published else None,
            "category": t.category,
            "sentiment": t.sentiment,
            "influence": t.influence,
            "influence_score": t.influence_score,
            "sentiment_score": t.sentiment_score,
            "why": t.why,
            "tags": t.tags,
        }
        for t in topics
    ]


def _overall_board_sentiment(topics: list[dict[str, Any]]) -> tuple[str, float, str]:
    """Weighted board lean from high-influence topics."""
    if not topics:
        return "MIXED", 0.0, "No high-impact topics loaded yet."
    num = 0.0
    den = 0.0
    for t in topics:
        w = float(t.get("influence_score") or 0.3)
        # Emphasize HIGH influence
        if t.get("influence") == "HIGH":
            w *= 1.5
        elif t.get("influence") == "ELEVATED":
            w *= 1.15
        s = float(t.get("sentiment_score") or 0.0)
        num += w * s
        den += w
    score = num / den if den else 0.0
    if score >= 0.12:
        label = "BULL"
        note = "Weighted headline tone leans risk-on for US equity-index futures."
    elif score <= -0.12:
        label = "BEAR"
        note = "Weighted headline tone leans risk-off for US equity-index futures."
    else:
        label = "MIXED"
        note = "Headlines are mixed — no clean risk-on/off lean. Trade structure, not the tape narrative."
    return label, score, note


def _fmt_when(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ET_TZ)
        return dt.astimezone(ET_TZ).strftime("%b %d %H:%M ET")
    except Exception:
        return str(iso)[:16]


def _sentiment_badge(sentiment: str) -> str:
    s = (sentiment or "MIXED").upper()
    if s == "BULL":
        return "🟢 BULL"
    if s == "BEAR":
        return "🔴 BEAR"
    return "🟡 MIXED"


def _influence_badge(influence: str) -> str:
    inv = (influence or "WATCH").upper()
    if inv == "HIGH":
        return "⚡ HIGH"
    if inv == "ELEVATED":
        return "▲ ELEVATED"
    return "· WATCH"


def render_topic_cards(topics: list[dict[str, Any]], *, compact: bool = False) -> None:
    if not topics:
        st.info(
            "No high-impact topics matched right now. Feeds may be delayed or quiet — "
            "check Economic Calendar and Bloomberg Live."
        )
        return

    for i, t in enumerate(topics):
        side = "bull" if t.get("sentiment") == "BULL" else ("bear" if t.get("sentiment") == "BEAR" else "bull")
        header = (
            f"{_sentiment_badge(str(t.get('sentiment')))} · "
            f"{_influence_badge(str(t.get('influence')))} · "
            f"{t.get('category')} · {t.get('title')}"
        )
        with candle_expander(header[:140], side=side, expanded=(not compact and i < 3), kind="page"):
            st.markdown(f"**{t.get('title')}**")
            meta = (
                f"`{t.get('category')}` · `{_sentiment_badge(str(t.get('sentiment')))}` · "
                f"`{_influence_badge(str(t.get('influence')))}` · "
                f"influence score **{float(t.get('influence_score') or 0):.0%}** · "
                f"{t.get('source')} · {_fmt_when(t.get('published'))}"
            )
            st.caption(meta)
            if t.get("summary"):
                st.write(t["summary"])
            st.markdown(f"**Why it matters:** {t.get('why')}")
            if t.get("tags"):
                st.caption("Tags: " + " · ".join(f"`{x}`" for x in t["tags"][:8]))
            if t.get("link"):
                st.link_button(
                    link_label("Open source article"),
                    str(t["link"]),
                    use_container_width=True,
                    type="secondary",
                    key=f"wmm_link_{i}_{hash(t.get('title')) % 10_000}",
                )


@st.fragment(run_every=timedelta(seconds=AUTO_REFRESH_SEC))
def _auto_refresh_board(*, compact: bool = False, max_topics: int = 14) -> None:
    now = _now_et()
    st.session_state[_KEY_LAST] = now.isoformat()
    st.session_state[_KEY_TICK] = int(st.session_state.get(_KEY_TICK, 0)) + 1

    with st.spinner("Scanning high-impact Business · Politics · Macro · Micro topics…"):
        topics = collect_market_topics(max_topics=max_topics)

    board_label, board_score, board_note = _overall_board_sentiment(topics)

    st.caption(
        f"Scan **#{int(st.session_state.get(_KEY_TICK, 0))}** · {now.strftime('%H:%M:%S ET')} · "
        f"auto every **{AUTO_REFRESH_SEC}s** · {len(topics)} topics"
    )

    # Overall desk lean
    c1, c2, c3, c4 = st.columns(4)
    bulls = sum(1 for t in topics if t.get("sentiment") == "BULL")
    bears = sum(1 for t in topics if t.get("sentiment") == "BEAR")
    highs = sum(1 for t in topics if t.get("influence") == "HIGH")
    c1.metric("Board lean", _sentiment_badge(board_label), f"score {board_score:+.2f}")
    c2.metric("Bull topics", str(bulls))
    c3.metric("Bear topics", str(bears))
    c4.metric("HIGH influence", str(highs))
    if board_label == "BULL":
        st.success(board_note)
    elif board_label == "BEAR":
        st.error(board_note)
    else:
        st.warning(board_note)

    # Category breakdown
    cats = {"Macro": 0, "Politics": 0, "Business": 0, "Micro": 0}
    for t in topics:
        cats[str(t.get("category") or "Business")] = cats.get(str(t.get("category") or "Business"), 0) + 1
    st.caption(
        "Mix: "
        + " · ".join(f"**{k}** {v}" for k, v in cats.items() if v)
    )

    # Filter chips
    filt = st.multiselect(
        "Show categories",
        options=["Macro", "Politics", "Business", "Micro"],
        default=["Macro", "Politics", "Business", "Micro"],
        key="wmm_cat_filter",
    )
    min_inf = st.select_slider(
        "Minimum influence",
        options=["WATCH", "ELEVATED", "HIGH"],
        value="WATCH",
        key="wmm_min_inf",
    )
    rank = {"WATCH": 0, "ELEVATED": 1, "HIGH": 2}
    filtered = [
        t
        for t in topics
        if t.get("category") in filt and rank.get(str(t.get("influence")), 0) >= rank.get(min_inf, 0)
    ]

    desk_section("High-impact topics", side="bear")
    render_topic_cards(filtered, compact=compact)


def render_whats_moving_section(*, compact: bool = False, max_topics: int = 10) -> None:
    """Embeddable section (Session Selector / other pages)."""
    desk_section("What's moving the Market?", side="bear")
    st.caption(
        "High-item **Business · Politics · Macro · Micro** topics that can move "
        "US equity-index futures. Heuristic **Bull / Bear** tone + **influence** — "
        "context for the desk, not trade signals."
    )
    _auto_refresh_board(compact=compact, max_topics=max_topics)


def render_whats_moving_panel() -> None:
    """Full navigation page."""
    page_hero(
        "What's moving the Market?",
        "High-impact Business · Politics · Macro · Micro · Bull/Bear tone · influence on the tape",
        side="bear",
        desk_tag="TAPE DESK · NARRATIVE & INFLUENCE",
    )
    st.markdown(
        """
Before you size a micro, know **what is actually moving the room**.

This board scans free public headlines, keeps **high-impact** items in  
**Business · Politics · Macro · Micro**, and labels each with:

- **Sentiment** — potential **BULL** / **BEAR** / **MIXED** lean for US index risk  
- **Influence** — **HIGH** / **ELEVATED** / **WATCH** for MES · MNQ · MYM tape  

Educational context only. Structure and risk rules still run the protocol.
"""
    )
    b1, b2 = st.columns(2)
    with b1:
        if st.button("Rescan now", type="primary", use_container_width=True, key="wmm_force"):
            collect_market_topics.clear()
            st.session_state.pop(_KEY_LAST, None)
            st.rerun()
    with b2:
        st.link_button(
            link_label("Economic Calendar (high-impact US)"),
            "https://www.tradingview.com/economic-calendar/",
            use_container_width=True,
            type="secondary",
        )

    with candle_expander("How to read this board", side="bull", expanded=False, kind="doc"):
        st.markdown(
            """
| Badge | Meaning |
|-------|---------|
| 🟢 **BULL** | Headline tone historically associated with risk-on / supportive for equities |
| 🔴 **BEAR** | Headline tone associated with risk-off / pressure on equities |
| 🟡 **MIXED** | Conflicted or insufficient tone words |
| ⚡ **HIGH** | Classic market movers (Fed, CPI, NFP, war, tariffs, systemic stress) |
| ▲ **ELEVATED** | Secondary data, mega-cap earnings, yields/oil that can swing futures |
| · **WATCH** | Worth awareness; less likely to dominate the session alone |

**Board lean** weights **HIGH** influence topics more than routine business news.
"""
        )

    _auto_refresh_board(compact=False, max_topics=18)

    render_third_party_disclosure(expanded=False)
    render_disclosure(expanded=False)
    st.caption(
        "Headlines from free public RSS / Yahoo Finance. Delayed and incomplete. "
        "Not affiliated with any publisher. Not financial advice — educational desk tool only."
    )
