"""
Wall Street market theme for CPRP Streamlit app.

Dark trading-desk aesthetic aligned to CPRP branding:
  Navy (#0A1628 / #0F1B2D) + Gold (#C9A84C / #D4AF37) + Steel silver.
Up/down panel accents stay market-readable (soft gold vs copper-rose).
"""

from __future__ import annotations

from typing import Literal

import streamlit as st
import streamlit.components.v1 as components

# Panel sides: bull = brand gold / bear = copper risk accent
CandleSide = Literal["bull", "bear"]

# CPRP brand palette (seal + candlestick logo)
# Navy: #0A1628  #0F1B2D  #1A2744
# Gold: #C9A84C  #D4AF37  #E8D5A3
# Steel: #94A3B8  #C0C5CE

WS_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0&display=swap');

/* ── Base trading-desk canvas — CPRP navy ─────────────────────────────── */
html, body, [data-testid="stAppViewContainer"], .stApp {
  background: radial-gradient(1200px 600px at 8% -8%, rgba(201,168,76,0.08) 0%, transparent 48%),
              radial-gradient(900px 500px at 100% 0%, rgba(26,39,68,0.65) 0%, transparent 50%),
              #060b16 !important;
  color: #e8edf5 !important;
  font-family: 'IBM Plex Sans', 'Segoe UI', system-ui, sans-serif !important;
}

[data-testid="stHeader"] {
  background: rgba(6, 11, 22, 0.92) !important;
  border-bottom: 1px solid rgba(201, 168, 76, 0.22);
}

/* ── Sidebar terminal — deep navy + gold edge ─────────────────────────── */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0a1628 0%, #070e1a 55%, #060b16 100%) !important;
  border-right: 1px solid rgba(201, 168, 76, 0.18) !important;
  font-family: 'IBM Plex Sans', system-ui, sans-serif !important;
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
  padding: 0.45rem 0.55rem !important;
  margin: 0.15rem 0 !important;
  border-radius: 6px !important;
  border-left: 3px solid transparent !important;
  transition: background 0.15s ease, border-color 0.15s ease;
}
[data-testid="stSidebar"] .stRadio label:hover {
  background: rgba(26, 39, 68, 0.85) !important;
}
[data-testid="stSidebar"] .stRadio > div > label:nth-child(odd) {
  border-left-color: #C9A84C !important;
}
[data-testid="stSidebar"] .stRadio > div > label:nth-child(even) {
  border-left-color: #8B9BB4 !important;
}

/* ── Typography ───────────────────────────────────────────────────────── */
h1, h2, h3 {
  font-family: 'IBM Plex Sans', system-ui, sans-serif !important;
  letter-spacing: 0.02em !important;
  color: #f4f1e8 !important;
}
h1 {
  font-weight: 700 !important;
  border-bottom: 1px solid rgba(201, 168, 76, 0.28);
  padding-bottom: 0.35rem;
}
code, .stCaption, [data-testid="stCaption"] {
  font-family: 'IBM Plex Mono', ui-monospace, monospace !important;
  color: #a8b3c7 !important;
}

/* ── Cards / containers ───────────────────────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: rgba(15, 27, 45, 0.72) !important;
  border: 1px solid rgba(201, 168, 76, 0.14) !important;
  border-radius: 10px !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}

/* ── Expanders as desk panels ─────────────────────────────────────────── */
[data-testid="stExpander"] {
  background: linear-gradient(180deg, rgba(15,27,45,0.98), rgba(8,14,26,0.99)) !important;
  border: 1px solid rgba(148, 163, 184, 0.16) !important;
  border-radius: 10px !important;
  margin-bottom: 0.65rem !important;
  overflow: visible;
  box-shadow: inset 0 1px 0 rgba(232,213,163,0.04), 0 6px 18px rgba(0,0,0,0.3);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] details summary,
[data-testid="stExpander"] > details > summary {
  font-weight: 600 !important;
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: 0.92rem !important;
  letter-spacing: 0.03em;
  padding: 0.7rem 0.9rem !important;
  cursor: pointer !important;
  color: #e8edf5 !important;
  list-style: none !important;
  display: flex !important;
  align-items: center !important;
  gap: 0.4rem !important;
}
[data-testid="stExpander"] summary:hover {
  background: rgba(26, 39, 68, 0.65) !important;
}
[data-testid="stExpander"] summary p {
  margin: 0 !important;
  color: inherit !important;
}

/* Force Streamlit expander chevron / Material arrow icons to render as icons (not text) */
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

/* Material Symbols / material icons (keyboard_double_arrow_right, etc.) */
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

/* Expander toggle specifically */
[data-testid="stExpander"] summary > div:first-child,
[data-testid="stExpander"] summary > span:first-child {
  color: #C9A84C !important;
  flex-shrink: 0 !important;
}

/* Gold accent panels (📈 / docs / primary) */
[data-testid="stExpander"].ws-candle-bull {
  border-left: 5px solid #C9A84C !important;
  border-color: rgba(201, 168, 76, 0.42) !important;
  box-shadow: inset 0 0 0 1px rgba(201,168,76,0.1), 0 6px 18px rgba(0,0,0,0.28);
}
[data-testid="stExpander"].ws-candle-bull summary {
  color: #E8D5A3 !important;
  background: linear-gradient(90deg, rgba(201,168,76,0.14), transparent 55%);
}
/* Steel / risk panels (📉 / risk / TV) */
[data-testid="stExpander"].ws-candle-bear {
  border-left: 5px solid #8B9BB4 !important;
  border-color: rgba(139, 155, 180, 0.4) !important;
  box-shadow: inset 0 0 0 1px rgba(139,155,180,0.1), 0 6px 18px rgba(0,0,0,0.28);
}
[data-testid="stExpander"].ws-candle-bear summary {
  color: #C5D0E0 !important;
  background: linear-gradient(90deg, rgba(139,155,180,0.14), transparent 55%);
}

/* ── Primary / secondary buttons — gold CTA ───────────────────────────── */
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
  background: linear-gradient(180deg, #D4AF37 0%, #A88B2E 100%) !important;
  border: 1px solid #C9A84C !important;
  color: #0A1628 !important;
  font-weight: 700 !important;
  border-radius: 6px !important;
  box-shadow: 0 0 0 1px rgba(201,168,76,0.2), 0 4px 14px rgba(201,168,76,0.22);
}
.stButton > button[kind="secondary"],
.stButton > button {
  border-radius: 6px !important;
  border: 1px solid rgba(201,168,76,0.28) !important;
  background: rgba(15, 27, 45, 0.95) !important;
  color: #e8edf5 !important;
}
.stButton > button:hover {
  border-color: rgba(201, 168, 76, 0.65) !important;
}

/* ── Metrics / tape ───────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: rgba(15, 27, 45, 0.8);
  border: 1px solid rgba(201, 168, 76, 0.14);
  border-radius: 8px;
  padding: 0.5rem 0.75rem;
}
[data-testid="stMetricValue"] {
  font-family: 'IBM Plex Mono', monospace !important;
  color: #E8D5A3 !important;
}

/* ── Tabs ─────────────────────────────────────────────────────────────── */
button[data-baseweb="tab"] {
  font-family: 'IBM Plex Mono', monospace !important;
  font-weight: 500 !important;
  color: #a8b3c7 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
  color: #E8D5A3 !important;
  border-bottom-color: #C9A84C !important;
}

/* ── Inputs ───────────────────────────────────────────────────────────── */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
  background: rgba(8, 14, 26, 0.95) !important;
  border-color: rgba(201, 168, 76, 0.22) !important;
  color: #e8edf5 !important;
  font-family: 'IBM Plex Mono', monospace !important;
}

/* ── Dataframes ───────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
  border: 1px solid rgba(201, 168, 76, 0.14);
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
  background: linear-gradient(90deg, rgba(10,22,40,0.98), rgba(15,27,45,0.95), rgba(10,22,40,0.98));
  border: 1px solid rgba(201, 168, 76, 0.22);
  border-radius: 8px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.78rem;
  letter-spacing: 0.04em;
  color: #a8b3c7;
}
.ws-tape .bull { color: #E8D5A3; font-weight: 600; }
.ws-tape .bear { color: #C5D0E0; font-weight: 600; }
.ws-tape .sym { color: #f4f1e8; font-weight: 600; }
.ws-tape .sep { opacity: 0.35; color: #C9A84C; }

.ws-page-hero {
  padding: 0.95rem 1.1rem 0.75rem 1.1rem;
  margin-bottom: 1.1rem;
  background: linear-gradient(135deg, rgba(10,22,40,0.98) 0%, rgba(15,27,45,0.96) 50%, rgba(12,18,32,0.98) 100%);
  border: 1px solid rgba(201, 168, 76, 0.28);
  border-left: 5px solid #C9A84C;
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.4), inset 0 1px 0 rgba(232,213,163,0.06);
}
.ws-page-hero.bear-edge {
  border-left-color: #8B9BB4;
  border-color: rgba(139, 155, 180, 0.28);
}
.ws-page-hero h1 {
  margin: 0 0 0.3rem 0 !important;
  border: none !important;
  padding: 0 !important;
  font-size: 1.55rem !important;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #f4f1e8 !important;
}
.ws-page-hero .sub {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.82rem;
  color: #a8b3c7;
  margin: 0;
  line-height: 1.45;
}
.ws-page-hero .desk-tag {
  display: inline-block;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #C9A84C;
  margin-bottom: 0.35rem;
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
  box-shadow: 0 -5px 0 0 #C9A84C, 0 5px 0 0 #C9A84C;
}
.ws-candle-mark.bear {
  background: #8B9BB4;
  box-shadow: 0 -5px 0 0 #8B9BB4, 0 5px 0 0 #8B9BB4;
}

.ws-section {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #8B9BB4;
  border-bottom: 1px solid rgba(201,168,76,0.16);
  padding-bottom: 0.35rem;
  margin: 1.25rem 0 0.75rem 0;
}
.ws-section .bull { color: #C9A84C; }
.ws-section .bear { color: #8B9BB4; }

/* ── Links — brand gold ───────────────────────────────────────────────── */
a { color: #D4AF37 !important; }
a:hover { color: #E8D5A3 !important; }

/* ── Divider ──────────────────────────────────────────────────────────── */
hr {
  border-color: rgba(201, 168, 76, 0.14) !important;
}

/* ── Auth / landing polish ────────────────────────────────────────────── */
[data-testid="stForm"] {
  background: rgba(15, 27, 45, 0.75);
  border: 1px solid rgba(201, 168, 76, 0.18);
  border-radius: 10px;
  padding: 0.75rem 1rem 1rem 1rem;
}

/* Progress bars / sliders pick up gold */
[data-testid="stProgress"] > div > div {
  background-color: #C9A84C !important;
}
div[data-baseweb="slider"] div[role="slider"] {
  background-color: #C9A84C !important;
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
        /* Document / link panels — soft green desk edge */
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
    """Inject global Wall Street CSS + candle expander colorizer once per run."""
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
    desk_tag: str = "CPRP TRADING DESK",
) -> None:
    """Professional market page header with bull/bear edge."""
    edge = "bear-edge" if side == "bear" else ""
    mark = "bear" if side == "bear" else "bull"
    sub_html = f'<p class="sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
<div class="ws-page-hero {edge}">
  <div class="desk-tag">{desk_tag}</div>
  <h1><span class="ws-candle-mark {mark}"></span>{title}</h1>
  {sub_html}
</div>
""",
        unsafe_allow_html=True,
    )


def desk_section(title: str, *, side: CandleSide = "bull") -> None:
    """Small mono section label between panels."""
    cls = "bull" if side == "bull" else "bear"
    glyph = "▲" if side == "bull" else "▼"
    st.markdown(
        f'<div class="ws-section"><span class="{cls}">{glyph}</span> {title}</div>',
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
