"""
Cooper Precision Reversion Protocol (CPRP) — Session Micro Selector
Official Rulebook v1.5 (Final)

Run:
  streamlit run app.py
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from alerts import RecommendationTracker
from analyzer import analyze_all, fetch_bars
from admin import is_current_user_admin, render_admin_panel
from auth import (
    current_display_name,
    current_user_email,
    render_account_sidebar,
    require_display_name,
    require_login,
)
from chat import heartbeat, render_active_users_badge, render_member_chat
from journal import render_journal_page, render_reference_and_journal_side_by_side
from community import render_community_panel
from economic_calendar import render_economic_calendar_panel
from live_news import render_bloomberg_audio_option, render_bloomberg_panel
from micros_guide import render_micros_guide_panel
from platforms_brokers import render_platforms_brokers_panel
from session_stats import render_session_wl_panel
from config import (
    ADMIN_ROLE_LABEL,
    APP_NAME,
    BRANDING_DIR,
    BRANDING_LOGO_ICON,
    BRANDING_LOGO_IMAGE,
    BRANDING_LOGO_VIDEO,
    BRANDING_LOGO_VIDEO_ALT,
    SIDEBAR_VIDEO,
    SIDEBAR_VIDEO_BRAND,
    SIDEBAR_VIDEO_BRAND_GIF,
    SIDEBAR_VIDEO_GIF,
    SESSION_SELECTOR_VIDEO,
    SESSION_SELECTOR_VIDEO_BRAND,
    SESSION_SELECTOR_VIDEO_BRAND_GIF,
    SESSION_SELECTOR_VIDEO_GIF,
    SESSION_SELECTOR_VARIANT_GIF,
    BRANDING_OFFICIAL_SEAL,
    BRANDING_OFFICIAL_SEAL_ANIM,
    BRANDING_OFFICIAL_SEAL_ANIM_BRAND,
    BRANDING_OFFICIAL_SEAL_BRAND,
    BRANDING_OFFICIAL_SEAL_BRAND_JPG,
    BRANDING_OFFICIAL_SEAL_JPG,
    CREATOR,
    MEMBER_CHAT_HERO_IMAGE,
    MEMBER_CHAT_HERO_VIDEO,
    FOUNDER_BIO,
    FOUNDER_NAME,
    FOUNDER_TAGLINE,
    FOUNDER_TITLE,
    HARD_STOP_DEFAULT_USD,
    HARD_STOP_MAX_USD,
    HARD_STOP_MIN_USD,
    INSTRUMENTS,
    MIN_SCORE_TO_TRADE,
    PROTOCOL_NAME,
    PROTOCOL_SHORT,
    QUICK_REFERENCE_DOWNLOAD_NAME,
    QUICK_REFERENCE_IMAGE,
    QUICK_REFERENCE_PDF,
    RULEBOOK_BASE_DOWNLOAD_NAME,
    RULEBOOK_BASE_PDF,
    RULEBOOK_BASE_VERSION,
    RULEBOOK_UPDATE_DOWNLOAD_NAME,
    RULEBOOK_UPDATE_PDF,
    RULEBOOK_VERSION,
    STRUCTURE_BREAK_PAUSE_MINUTES,
)
from loop_media import render_loop_media
from sync_cprp_assets import (
    list_branding_images,
    list_branding_videos,
    list_official_brand_animated,
    list_official_brand_suite,
    sync_cprp_assets,
)
from wallstreet_ui import (
    candle_expander,
    desk_section,
    inject_wallstreet_theme,
    market_tape,
    nav_candle_pages,
    page_hero,
    strip_candle_prefix,
)

_page_icon = str(BRANDING_LOGO_ICON) if Path(BRANDING_LOGO_ICON).is_file() else "📊"

st.set_page_config(
    page_title=APP_NAME,
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Wall Street / trading-desk visual system (all pages)
inject_wallstreet_theme()

# ── Auth gate (email + password, then public username) ────────────────────
# Public visitors must sign up / log in before using the tool.
if not require_login():
    st.stop()
if not require_display_name():
    st.stop()

# Presence heartbeat (active member count)
_email = current_user_email() or ""
_display = current_display_name() or "Member"
if _email:
    try:
        heartbeat(_email, _display)
    except Exception:
        pass

# Session state (only after login)
if "tracker" not in st.session_state:
    st.session_state.tracker = RecommendationTracker()
if "last_rec" not in st.session_state:
    st.session_state.last_rec = None
if "history" not in st.session_state:
    st.session_state.history = []
if "doc_sync_report" not in st.session_state:
    st.session_state.doc_sync_report = None
if "doc_sync_done" not in st.session_state:
    st.session_state.doc_sync_done = False

# Auto-sync local CPRP Trading docs/branding once per session (desktop only).
# On Streamlit Community Cloud there is no local CPRP Trading folder — skip silently.
if not st.session_state.doc_sync_done:
    try:
        if Path(r"C:\Users\imzcp\OneDrive\Desktop\CPRP Trading").is_dir():
            st.session_state.doc_sync_report = sync_cprp_assets()
        else:
            st.session_state.doc_sync_report = None
    except Exception as _sync_exc:  # noqa: BLE001
        st.session_state.doc_sync_report = None
        st.session_state.doc_sync_error = str(_sync_exc)
    st.session_state.doc_sync_done = True

def _play_logo_video(*candidates: Path, caption: str | None = None, height: int = 360) -> bool:
    """Show clean autoplay looping GIF/video (no play button) or still image."""
    return render_loop_media(*candidates, caption=caption, height=height, sidebar=False)


# ══════════════════════════════════════════════════════════════════════════
# SIDEBAR — navigation + brand
# ══════════════════════════════════════════════════════════════════════════
# Sidebar: clean looping brand media (GIF preferred; silent autoplay MP4 fallback)
if not render_loop_media(
    Path(SIDEBAR_VIDEO_GIF),
    Path(SIDEBAR_VIDEO_BRAND_GIF),
    Path(BRANDING_LOGO_VIDEO_ALT),
    Path(SIDEBAR_VIDEO),
    Path(SIDEBAR_VIDEO_BRAND),
    Path(BRANDING_DIR) / "cprp_logo_video_alt.mp4",
    Path(BRANDING_LOGO_ICON),
    height=200,
    sidebar=True,
):
    pass
st.sidebar.markdown("### CPRP Strategies")
st.sidebar.caption(f"Rulebook v{RULEBOOK_VERSION} · {CREATOR}")
st.sidebar.markdown(
    '<p style="font-family:IBM Plex Mono,monospace;font-size:0.72rem;color:#64748b;">'
    "📈 green · 📉 red · 📂 docs · 📺 news · 🔗 links — expand panels for detail</p>",
    unsafe_allow_html=True,
)
render_account_sidebar()
st.sidebar.markdown("##### Live now")
try:
    render_active_users_badge()
except Exception:
    st.sidebar.caption("Online count unavailable")

PAGE_SELECTOR = "Session Selector"
PAGE_JOURNAL = "Trading Journal"
PAGE_SESSION_WL = "CPRP Session Statistics"
PAGE_COMMUNITY = "Community"
PAGE_CHAT = "Member Chat"
PAGE_CALENDAR = "Economic Calendar"
PAGE_NEWS = "Bloomberg Live"
PAGE_PLATFORMS = "Platforms & Brokers"
PAGE_MICROS = "Micro E-mini Futures"
PAGE_BRANDING = "Company Branding"
PAGE_ABOUT = "About the Founder"
PAGE_ADMIN = "Admin / Founder"

# Member nav order: intro → brand → education → tools → trade → news → log → community
# Admin / Founder page is NEVER listed for non-admins
_nav_pages_clean = [
    PAGE_ABOUT,          # 1. Who built CPRP
    PAGE_BRANDING,       # 2. Brand identity
    PAGE_MICROS,         # 3. Instrument education
    PAGE_PLATFORMS,      # 4. Charting / broker links
    PAGE_SELECTOR,       # 5. Main session tool
    PAGE_CALENDAR,       # 6. Event risk filter
    PAGE_NEWS,           # 7. Live news
    PAGE_JOURNAL,        # 8. Private session notes
    PAGE_SESSION_WL,     # 9. Shared session stats
    PAGE_COMMUNITY,      # 10. Ideas board
    PAGE_CHAT,           # 11. Live member chat
]
_is_founder = is_current_user_admin()
if _is_founder:
    _nav_pages_clean = _nav_pages_clean + [PAGE_ADMIN]

# Candle-styled nav labels (bullish / bearish alternating)
_nav_pages = nav_candle_pages(_nav_pages_clean)

# Clear stale Streamlit radio state if a non-admin still has Admin selected
_nav_raw = st.session_state.get("nav_page", "")
if not _is_founder and PAGE_ADMIN in str(_nav_raw):
    st.session_state["nav_page"] = nav_candle_pages([PAGE_ABOUT])[0]

page_label = st.sidebar.radio(
    "Trading desk",
    _nav_pages,
    key="nav_page",
)
page = strip_candle_prefix(page_label)
st.sidebar.markdown("---")

# Desk tape under nav
market_tape(version=RULEBOOK_VERSION)

# ── Admin / Founder only (hard gate — not visible or usable by members) ───
if page == PAGE_ADMIN:
    if not _is_founder:
        st.session_state["nav_page"] = nav_candle_pages([PAGE_SELECTOR])[0]
        st.warning("The Admin / Founder panel is only available to the founder account.")
        st.rerun()
    render_admin_panel()
    st.stop()

# ── Bloomberg Live dedicated panel ────────────────────────────────────────
if page == PAGE_NEWS:
    render_bloomberg_panel()
    st.stop()

# ── Economic Calendar (Forex Factory — free third-party) ──────────────────
if page == PAGE_CALENDAR:
    render_economic_calendar_panel()
    st.stop()

# ── Platforms & Brokers (popular w/ micro traders — no partnership) ───────
if page == PAGE_PLATFORMS:
    render_platforms_brokers_panel()
    st.stop()

# ── Micro E-mini Futures education (ticks + sizing) ───────────────────────
if page == PAGE_MICROS:
    render_micros_guide_panel()
    st.stop()

# ── CPRP Session Statistics (W/L image uploads) ───────────────────────────
if page == PAGE_SESSION_WL:
    render_session_wl_panel()
    st.stop()

# ── Community board (posts + images) ──────────────────────────────────────
if page == PAGE_COMMUNITY:
    render_community_panel()
    st.stop()

# ── Trading Journal page (full history + side-by-side reference) ───────────
if page == PAGE_JOURNAL:
    _pick_for_journal = ""
    if st.session_state.get("last_rec") is not None:
        _lr = st.session_state.last_rec
        if getattr(_lr, "recommended", None) and not getattr(_lr, "sit_out", True):
            _pick_for_journal = _lr.recommended
    render_bloomberg_audio_option(key_prefix="jr_bb", height=260)
    render_journal_page(default_micro=_pick_for_journal)
    st.stop()

# ── Member Chat page ──────────────────────────────────────────────────────
if page == PAGE_CHAT:
    # Larger player on Member Chat so news is easy to watch while chatting
    render_bloomberg_audio_option(key_prefix="chat_bb", height=520)
    # No hero video/image on Member Chat — desk header only
    render_member_chat()
    st.stop()

# ── Company Branding page ─────────────────────────────────────────────────
if page == PAGE_BRANDING:
    page_hero(
        "CPRP Company Branding",
        f"Official brand suite for **{PROTOCOL_NAME}** · seal · logos · banners · animated media",
        side="bull",
        desk_tag="BRAND DESK · CORPORATE IDENTITY",
    )

    # Official Seal hero (transparent PNG preferred)
    desk_section("Official Seal", side="bull")
    seal_cols = st.columns([1, 1.4, 1])
    with seal_cols[1]:
        seal_shown = False
        for p in (
            Path(BRANDING_OFFICIAL_SEAL),           # transparent PNG
            Path(BRANDING_OFFICIAL_SEAL_BRAND),
            Path(BRANDING_OFFICIAL_SEAL_ANIM),
            Path(BRANDING_OFFICIAL_SEAL_ANIM_BRAND),
            Path(BRANDING_OFFICIAL_SEAL_JPG),
            Path(BRANDING_OFFICIAL_SEAL_BRAND_JPG),
        ):
            if p.is_file():
                st.image(str(p), use_container_width=True, caption="CPRP Official Seal")
                mime = {
                    ".gif": "image/gif",
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                }.get(p.suffix.lower(), "application/octet-stream")
                st.download_button(
                    label=f"📁 Download {p.name}",
                    data=p.read_bytes(),
                    file_name=p.name,
                    mime=mime,
                    key=f"dl_seal_{p.name}",
                    use_container_width=True,
                )
                seal_shown = True
                break
        if not seal_shown:
            st.warning("Official Seal not found — run branding sync.")

    # Official numbered suite stills
    desk_section("Official brand suite (stills)", side="bull")
    suite = list_official_brand_suite()
    if suite:
        cols = st.columns(min(3, len(suite)))
        for i, (label, img) in enumerate(suite):
            with cols[i % len(cols)]:
                st.markdown(f"**{label}**")
                st.image(str(img), use_container_width=True)
                st.download_button(
                    label=f"📄 Download",
                    data=img.read_bytes(),
                    file_name=img.name,
                    mime="image/jpeg",
                    key=f"dl_suite_{img.name}",
                    use_container_width=True,
                )
    else:
        st.info("Official suite stills not found. Click **Sync branding & documents now**.")

    # Official animated suite
    desk_section("Official brand suite (animated)", side="bear")
    anim_suite = list_official_brand_animated()
    if anim_suite:
        cols = st.columns(2)
        for i, (label, media) in enumerate(anim_suite):
            with cols[i % 2]:
                st.markdown(f"**{label}**")
                render_loop_media(media, height=280)
                if media.suffix.lower() == ".gif":
                    st.download_button(
                        label="📁 Download GIF",
                        data=media.read_bytes(),
                        file_name=media.name,
                        mime="image/gif",
                        key=f"dl_anim_{media.name}",
                        use_container_width=True,
                    )
                elif media.suffix.lower() == ".mp4":
                    st.download_button(
                        label="📁 Download MP4",
                        data=media.read_bytes(),
                        file_name=media.name,
                        mime="video/mp4",
                        key=f"dl_anim_{media.name}",
                        use_container_width=True,
                    )
    else:
        st.caption("No official animated brand media found yet.")

    # Legacy / primary looping logo
    desk_section("Primary logo motion (app chrome)", side="bull")
    _play_logo_video(
        Path(BRANDING_LOGO_VIDEO),
        Path(BRANDING_DIR) / "cprp_brand_logo_candlestick_anim.gif",
        Path(BRANDING_DIR) / "cprp_logo_video_main.gif",
        Path(BRANDING_DIR) / "cprp_logo_video_main.mp4",
        caption="Primary logo motion (looping)",
    )

    with candle_expander("Brand sync & access control", side="bear", expanded=False, kind="folder"):
        col_sync, col_info = st.columns([1, 2])
        with col_sync:
            if is_current_user_admin():
                if st.button(
                    "Sync branding & documents now",
                    type="primary",
                    use_container_width=True,
                ):
                    with st.spinner("Scanning CPRP Trading and related folders…"):
                        st.session_state.doc_sync_report = sync_cprp_assets()
                        st.session_state.doc_sync_done = True
                    st.rerun()
            else:
                st.caption(
                    f"Brand media is view-only for members. "
                    f"Only **{ADMIN_ROLE_LABEL}** can sync or edit application assets."
                )
        with col_info:
            if is_current_user_admin():
                rep = st.session_state.doc_sync_report
                if rep is not None:
                    for line in rep.summary_lines():
                        st.markdown(f"- {line}")
                    if rep.copied:
                        with candle_expander("Files updated this session", side="bull", expanded=False, kind="doc"):
                            for c in rep.copied:
                                st.markdown(f"- `{c}`")
                else:
                    st.info("No sync report yet. Click **Sync branding & documents now**.")
            else:
                st.info(
                    f"You are browsing as a **member**. Application edits are reserved for "
                    f"**{ADMIN_ROLE_LABEL}** ({CREATOR})."
                )

    desk_section("Logo GIFs (primary brand media — looping)", side="bull")
    gifs = list_branding_videos()  # now returns .gif (and leftover .mp4)
    ordered: list[Path] = []
    for p in (
        Path(BRANDING_LOGO_VIDEO),
        Path(BRANDING_LOGO_VIDEO_ALT),
        Path(BRANDING_DIR) / "cprp_logo_video_main.gif",
        Path(BRANDING_DIR) / "cprp_logo_video_alt.gif",
        Path(MEMBER_CHAT_HERO_VIDEO),
    ):
        if p.is_file() and p not in ordered:
            ordered.append(p)
    for v in gifs:
        if v not in ordered and v.suffix.lower() == ".gif":
            ordered.append(v)

    video_labels = {
        "cprp_logo_video": "Primary logo GIF",
        "cprp_logo_video_main": "Main CPRP logo GIF",
        "cprp_logo_video_alt": "Alternate logo GIF",
        "cprp_logo_video_variant_1": "Logo motion GIF 1",
        "cprp_logo_video_variant_2": "Logo motion GIF 2",
        "cprp_logo_video_variant_3": "Logo motion GIF 3",
        "cprp_logo_video_variant_4": "Logo motion GIF 4",
        "cprp_member_chat_hero": "Member Chat hero GIF",
        "cprp_brand_logo_candlestick_anim": "Candlestick brand (animated)",
        "cprp_brand_logo_support_resistance_anim": "Support / Resistance brand (animated)",
        "cprp_icon_minimal_anim": "Minimal icon (animated)",
        "cprp_banner_horizontal_anim": "Horizontal banner (animated)",
        "cprp_official_seal_anim": "Official Seal (animated)",
    }

    if ordered:
        cols = st.columns(2)
        for i, v in enumerate(ordered):
            with cols[i % 2]:
                title = video_labels.get(v.stem.lower(), v.stem.replace("_", " ").title())
                st.markdown(f"**{title}**")
                render_loop_media(v, height=280)
                if v.suffix.lower() == ".gif":
                    st.download_button(
                        label="📁 Download GIF",
                        data=v.read_bytes(),
                        file_name=v.name,
                        mime="image/gif",
                        key=f"dl_brand_gif_{v.name}",
                        use_container_width=True,
                    )
                elif v.suffix.lower() == ".mp4":
                    st.download_button(
                        label="📁 Download MP4",
                        data=v.read_bytes(),
                        file_name=v.name,
                        mime="video/mp4",
                        key=f"dl_brand_mp4_{v.name}",
                        use_container_width=True,
                    )
    else:
        st.warning("No logo GIFs found. Run `python scripts/convert_videos_to_gifs.py`.")

    desk_section("Still logo suite (fallback / download)", side="bear")
    imgs = list_branding_images()
    if not imgs:
        for name in (
            BRANDING_LOGO_ICON,
            BRANDING_LOGO_IMAGE,
            Path(BRANDING_DIR) / "cprp_logo_light.jpg",
            Path(BRANDING_DIR) / "cprp_logo_minimal_dark.jpg",
        ):
            p = Path(name)
            if p.is_file() and p not in imgs:
                imgs.append(p)

    if imgs:
        label_map = {
            "cprp_brand_logo_candlestick": "Candlestick brand logo",
            "cprp_brand_logo_support_resistance": "Support / Resistance brand logo",
            "cprp_icon_minimal": "Minimal icon",
            "cprp_banner_horizontal": "Horizontal banner",
            "cprp_official_seal": "Official Seal",
            "cprp_logo_square_monogram": "Square monogram",
            "cprp_logo_primary_chart": "Primary chart logo",
            "cprp_logo_minimal_dark": "Minimal dark",
            "cprp_logo_light": "Light logo",
            "cprp_logo_classic": "Classic wordmark",
            "cprp_logo_icon": "App icon",
            "cprp_logo_primary": "Primary logo",
            "cprp_member_chat_poster": "Member Chat poster",
        }
        cols = st.columns(3)
        for i, img in enumerate(imgs):
            with cols[i % 3]:
                stem = img.stem.lower()
                title = label_map.get(stem, stem.replace("_", " ").title())
                st.markdown(f"**{title}**")
                st.image(str(img), use_container_width=True)
                st.download_button(
                    label=f"📄 Download {img.suffix.upper().lstrip('.')}",
                    data=img.read_bytes(),
                    file_name=img.name,
                    mime="image/jpeg" if img.suffix.lower() in {".jpg", ".jpeg"} else "image/png",
                    key=f"dl_brand_{img.name}",
                    use_container_width=True,
                )
    else:
        st.caption("No still images found.")

    with candle_expander("Brand usage notes", side="bull", expanded=False, kind="page"):
        st.markdown(
            f"""
- Prefer **looping logo GIFs** for headers, branding, and Member Chat.
- Still images remain available for favicon, downloads, and offline use.
- Brand name: **{PROTOCOL_NAME} ({PROTOCOL_SHORT})**
- Founder: **{FOUNDER_NAME}**
- Rulebook: **Official Rulebook v{RULEBOOK_VERSION} (Final)**
- Tagline: *Trade the boundaries. Respect the structure. Control the risk.*
"""
        )
    st.caption(f"© 2026 {CREATOR}. Personal branding for CPRP.")
    st.stop()

# ── About the Founder page ────────────────────────────────────────────────
if page == PAGE_ABOUT:
    page_hero(
        "About the Founder",
        f"{FOUNDER_NAME} · {FOUNDER_TITLE} · {FOUNDER_TAGLINE}",
        side="bull",
        desk_tag="FOUNDER PROFILE · CPRP",
    )
    head_l, head_r = st.columns([1, 2])
    with head_l:
        if not _play_logo_video(
            Path(BRANDING_LOGO_VIDEO),
            Path(BRANDING_LOGO_VIDEO_ALT),
            Path(BRANDING_LOGO_IMAGE),
            Path(BRANDING_LOGO_ICON),
            caption="CPRP brand",
        ):
            st.caption("Brand media not found.")
    with head_r:
        st.markdown(f"## {FOUNDER_NAME}")
        st.markdown(f"**{FOUNDER_TITLE}**")
        st.markdown(f"*{FOUNDER_TAGLINE}*")
        st.markdown(
            f"""
**Protocol:** {PROTOCOL_NAME} ({PROTOCOL_SHORT})  
**Rulebook:** Official Rulebook v{RULEBOOK_VERSION} (Final)  
**Focus:** Range / channel reversion on Micro futures (MES · MNQ · MYM)
"""
        )

    with candle_expander("My story", side="bull", expanded=True, kind="page"):
        st.markdown(FOUNDER_BIO)

    with candle_expander("What drives CPRP", side="bear", expanded=True, icon="📄"):
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(
            """
**Family**  
Father first — grounded by responsibility at home.
"""
        )
        c2.markdown(
            """
**Research & data**  
Patterns, structure, and probability — applied to the markets.
"""
        )
        c3.markdown(
            """
**Structure**  
Confirmed range/channel S/R, multi-TF confluence, strict risk.
"""
        )
        c4.markdown(
            """
**Ownership**  
A craft built, tested, and refined — not copied.
"""
        )

    st.info(
        "This application is a personal session-selection tool for CPRP. "
        "It does not place orders and is not financial advice. "
        "Futures trading involves substantial risk of loss."
    )
    from disclosure import render_disclosure_footer

    render_disclosure_footer()
    st.caption(f"© 2026 {FOUNDER_NAME}. All rights reserved.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════
# SESSION SELECTOR — sidebar help + controls
# ══════════════════════════════════════════════════════════════════════════
st.sidebar.header("📖 Help & navigation")
with st.sidebar.expander("How to use this app (start here)", expanded=True):
    st.markdown(
        f"""
**Intended use:** Before (and during) a trading session, open this app to
decide **which micro** — MES, MNQ, or MYM — currently fits the
**{PROTOCOL_NAME}** best. It is a **session selector**,
not an auto-trader and not a broker.

**Typical flow**
1. Set your **hard dollar stop** ($50–$100).
2. Read the **green/red banner** at the top — that is your session pick (or sit out).
3. Compare the **three micro cards** (scores, structure, extreme vs mid, 1H bias).
4. Open **Score breakdown** on a card for why/warnings.
5. Use **Head-to-head** + **candlestick chart** to confirm range/channel structure.
6. Keep a **static 1-Hour chart** open for long-term trend context (Quick Reference).
7. Operate the strategy using **How to operate the strategy (official Quick Reference)**.
8. Complete the **pre-trade checklist** (all 7 gates) before entering on Ironbeam / NinjaTrader.
9. Leave **Auto-refresh** on so the pick updates as conditions change.

**What it will *not* do**
- Place orders or manage positions  
- Replace your visual S/R judgment on NinjaTrader  
- Use live CME tick data (Yahoo is delayed)
"""
    )

with st.sidebar.expander("What each screen section means"):
    st.markdown(
        f"""
| Area | What it tells you |
|------|-------------------|
| **Top banner** | Final recommendation: trade **MES / MNQ / MYM** or **SIT OUT** |
| **Metrics row** | Time (ET), session phase, chart pair, static 1H context, min score ({MIN_SCORE_TO_TRADE:.0f}+) |
| **Three cards** | Per-micro score, last price, structure high/low, $ width, stop pts, boundary position, 1H bias |
| **Score breakdown** | Structure, risk fit, 1H context, volume, volatility, reasons (+), warnings (!) |
| **Head-to-head table** | Side-by-side numbers sorted by score |
| **Bar chart** | Visual score race; orange line = trade threshold |
| **Price structure** | 5m candles with session high/low (proxy S/R zone lines) |
| **Strategy ops expander** | Full CPRP process from the Official Quick Reference |
| **Pre-trade checklist** | All 7 Quick Reference entry confirmations |
| **Exits expander** | Profit targets + structure-break rules |
| **Quick Reference card** | Downloadable official one-page card |
"""
    )

with st.sidebar.expander("Sidebar controls explained"):
    st.markdown(
        """
- **Hard dollar stop** — Rulebook §5 risk cap for a single trade (−$50 to −$100).
  Changes how “structure fit” is scored (does the visible range/channel match that stop size?).
- **Auto-refresh** — Re-pulls data and re-scores on a timer.
- **Refresh every (sec)** — How often to re-run (30–300s). Longer = fewer Yahoo calls.
- **Desktop alerts on change** — Windows notification when the recommended micro
  (or sit-out) **changes**.
- **Analyze now** — Forces an immediate re-run (also happens on refresh).
"""
    )

with st.sidebar.expander("How scores are built (rulebook map)"):
    st.markdown(
        f"""
Scores (0–100) blend CPRP Official Rulebook v{RULEBOOK_VERSION}:

| Weight theme | Rulebook | Idea |
|--------------|----------|------|
| Structure (range/channel) | §3 | Confirmed S/R or channel; ≥2 touches each boundary |
| Risk fit | §5 | Structure width vs your hard stop in dollars |
| At boundaries | §4 | Near Support/Resistance beats mid-structure |
| Static 1H context | §2 | Filter quality when fading against HTF trend |
| Volume | §4 | Elevated volume as rejection/absorption confirm |
| Rejection / RSI | §4 / v1.5 | Wick rejection; RSI is last confirm (prefer divergence) |
| Volatility | §5 | Quiet enough for a micro hard stop |

**Near ties:** prefer **MES → MNQ → MYM** (§7). **Quality over frequency** (v1.5).

**Grades**
- **A** 75+ strong candidate  
- **B** 65+ tradeable with full confluence  
- **C** 55+ marginal — wait for boundary + confirm  
- **D** below threshold — prefer sit-out / other micro  
"""
    )

with st.sidebar.expander("Reading a recommendation"):
    st.markdown(
        f"""
- **TRADE MES/MNQ/MYM** — Focus that contract for range/channel reversion setups.
  Still wait for **full confluence** at **boundaries** on your charts.
- **SIT OUT** — No micro cleared the trade threshold. Capital preservation wins.
- **AT BOUNDARY** — Price near support or resistance (valid entry zone).
- **mid** — Do **not** fade the middle; wait (even if RSI is extreme — v1.5).
- **1H bias** — Static higher-TF filter only (not entries):
  - *ranging* — standard setups generally higher quality  
  - *uptrend / downtrend* — more selective fading **against** that trend  
- **Chart pair** (approved pairs only):
  - *15m + 5m* — **default** for most sessions  
  - *30m + 15m* — larger / slower / lower volume  
- **Static HTF** — Always keep **1-Hour** open (4-Hour acceptable). Context only.
- **Structure break** — New session high/low that breaks prior range → flatten + pause
  **{STRUCTURE_BREAK_PAUSE_MINUTES} minutes** (or until new clear range forms). Do not hunt lower-TF bounces.
"""
    )

with st.sidebar.expander("How to operate the strategy (official Quick Reference)", expanded=False):
    st.markdown(
        f"""
Source: **CPRP Official Quick Reference v{RULEBOOK_VERSION}**  
(Official Rulebook v{RULEBOOK_VERSION} (Final) is authoritative).

*“Trade the boundaries. Respect the structure. Control the risk.”*

### 1. Strategy identity
Range-bound mean-reversion on **MES** (primary), **MNQ**, **MYM**.  
**Sell confirmed resistance · Buy confirmed support.**  
Hard risk **−${HARD_STOP_MIN_USD:.0f} to −${HARD_STOP_MAX_USD:.0f}** max per trade.  
Pause **{STRUCTURE_BREAK_PAUSE_MINUTES} minutes** (or until a new clear range forms) after any S/R break.  
Static **1-Hour (or 4H)** is context only — never generates entries.

### 2. Chart pair hierarchy (approved pairs only)
| Situation | Structure | Execution | Notes |
|-----------|-----------|-----------|-------|
| **Default / most sessions** | **15-minute** | **5-minute** | Cleaner RSI, better range definition, still responsive |
| Larger / slower / lower volume | **30-minute** | **15-minute** | Highest quality S/R, least noise |

When in doubt, use **15m + 5m**. 

### 3. RSI rules (v1.5)
- Prefer **divergence at the actual S/R level** over absolute **70/30** extremes.
- On **15m and 30m**, RSI extremes are useful as **alerts / preparation only**. If price is still mid-range, do **not** enter — wait for the confirmed boundary + price action + volume.
- RSI is **secondary** confirmation. Full entry stack: **confirmed S/R + price action + volume**.
- Optional: faster RSI (**7 or 9**) on the execution chart for divergence visualization only. Keep standard **14** on the structure chart.

### 4. Confirmation hierarchy (v1.5)
1. Confirmed Support / Resistance of the active range (**structure chart**)
2. Price action at the level (rejection, absorption, engulfs)
3. Volume confirmation
4. RSI (secondary — mainly divergence at S/R; absolute levels more useful on 15m/30m as alerts)

### 5. Key operating rules
- New session lows / highs that **break the prior range** → **pause**. Do not hunt lower-TF bounces.
- 1-Hour (or 4H) window is a **mandatory context filter only**.
- Hard dollar risk remains **−${HARD_STOP_MIN_USD:.0f} to −${HARD_STOP_MAX_USD:.0f}**. Stay on micros.
- **Fewer, higher-quality trades** preferred over high-frequency noise trades.
- Prefer **MES** unless MNQ/MYM is clearly superior.
- Platform preference: **NinjaTrader Web** (high/low display).

### 6. Using *this selector* with the Protocol
1. Let the app pick the **session micro** (or sit out).
2. Open the suggested chart pair + static 1H on NinjaTrader.
3. Confirm structure and the confirmation hierarchy before ordering.
4. Re-check after structure breaks or major session shifts.
"""
    )

with st.sidebar.expander("Strategy hard rules (always)"):
    st.markdown(
        f"""
**Core philosophy**
- Trade only **confirmed** structure — never anticipate  
- Fade the **extremes** of the range/channel until structure fails  
- Confirmation order: **S/R → price action → volume → RSI** (v1.5)  
- Hard dollar risk limit on every trade — **no exceptions**  
- When structure breaks, **step aside** — do not force trades  

**Operational rules (Quick Reference v{RULEBOOK_VERSION})**
- **Instruments:** MES, MNQ, MYM only — no other contracts  
- **Default charts:** **15m + 5m** (or **30m + 15m** when structure is larger/slower)  
- **Risk:** Hard stop **−${HARD_STOP_MIN_USD:.0f} to −${HARD_STOP_MAX_USD:.0f}** per trade  
- **Target:** Opposite boundary; partials at mid-range  
- **No averaging down.** Exit immediately at the hard limit  
- **After structure break:** Flat + **{STRUCTURE_BREAK_PAUSE_MINUTES}-min** pause (or until new clear range)  
- **Prefer MES**; quality over frequency  
- Protocol is complete as written — no discretionary overrides  
"""
    )

with st.sidebar.expander("Troubleshooting"):
    st.markdown(
        """
- **No data / empty scores** — Check internet; Yahoo may be slow after hours. Wait and hit **Analyze now**.
- **Browser didn’t open** — Go to [http://localhost:8501](http://localhost:8501)
- **Alerts not showing** — Enable Windows notifications; keep the terminal window open.
- **Scores feel “off”** — Data is **delayed**; treat this as session focus, not tick entry timing.
- **Stop the app** — Close the terminal or press `Ctrl+C` in the window that launched it.
"""
    )

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Session settings")

hard_stop = st.sidebar.slider(
    "Hard dollar stop ($)",
    min_value=int(HARD_STOP_MIN_USD),
    max_value=int(HARD_STOP_MAX_USD),
    value=int(HARD_STOP_DEFAULT_USD),
    step=5,
    help="Rulebook §5: exit any single trade at −$50 to −$100. No exceptions.",
)

auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
refresh_sec = st.sidebar.slider("Refresh every (sec)", 30, 300, 60, 15)
desktop_alerts = st.sidebar.checkbox("Desktop alerts on change", value=True)
st.sidebar.button("Analyze now", type="primary", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
**Approved micros only (§2)**

| Priority | Symbol | Role |
|---|---|---|
| 1 | **MES** | Primary default |
| 2 | **MNQ** | Higher volatility |
| 3 | **MYM** | Lower volatility |
"""
)

st.sidebar.markdown("---")
st.sidebar.subheader("Official documents")
st.sidebar.caption("Synced from CPRP Trading · download for offline use.")

if is_current_user_admin():
    if st.sidebar.button("Sync docs from CPRP Trading", use_container_width=True):
        with st.spinner("Scanning CPRP files…"):
            st.session_state.doc_sync_report = sync_cprp_assets()
            st.session_state.doc_sync_done = True
        st.sidebar.success("Sync complete")
        st.rerun()
    _rep = st.session_state.doc_sync_report
    if _rep is not None and _rep.detected_version:
        st.sidebar.caption(f"Latest scanned doc version: v{_rep.detected_version}")
else:
    st.sidebar.caption(f"Doc sync: {ADMIN_ROLE_LABEL} only")

_qr_sidebar = Path(QUICK_REFERENCE_IMAGE)
if _qr_sidebar.is_file():
    st.sidebar.download_button(
        label="📄 Download QR card (JPG)",
        data=_qr_sidebar.read_bytes(),
        file_name=QUICK_REFERENCE_DOWNLOAD_NAME,
        mime="image/jpeg",
        use_container_width=True,
        key="sidebar_qr_jpg",
    )
    _qr_pdf_side = Path(QUICK_REFERENCE_PDF)
    if _qr_pdf_side.is_file():
        st.sidebar.download_button(
            label="📃 Download QR card (PDF)",
            data=_qr_pdf_side.read_bytes(),
            file_name=f"CPRP_Quick_Reference_v{RULEBOOK_VERSION}.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="sidebar_qr_pdf",
        )
else:
    st.sidebar.caption("Quick Reference image missing — run Sync.")

_rb_side = Path(RULEBOOK_UPDATE_PDF)
if _rb_side.is_file():
    st.sidebar.download_button(
        label="📂 Download Rulebook Update (PDF)",
        data=_rb_side.read_bytes(),
        file_name=RULEBOOK_UPDATE_DOWNLOAD_NAME,
        mime="application/pdf",
        use_container_width=True,
        key="sidebar_rulebook_pdf",
    )

_rb_base = Path(RULEBOOK_BASE_PDF)
if _rb_base.is_file():
    st.sidebar.download_button(
        label="📁 Download Official Rulebook base (PDF)",
        data=_rb_base.read_bytes(),
        file_name=RULEBOOK_BASE_DOWNLOAD_NAME,
        mime="application/pdf",
        use_container_width=True,
        key="sidebar_rulebook_base_pdf",
    )

st.sidebar.markdown("---")
st.sidebar.caption(f"Pages: Selector · Branding · About · © {CREATOR}")

# ══════════════════════════════════════════════════════════════════════════
# MAIN — Session Selector header video + description + analysis
# ══════════════════════════════════════════════════════════════════════════
# Session Selector banner: clean looping GIF/video (no play button chrome)
if not render_loop_media(
    Path(SESSION_SELECTOR_VIDEO_GIF),
    Path(SESSION_SELECTOR_VIDEO_BRAND_GIF),
    Path(SESSION_SELECTOR_VARIANT_GIF),
    Path(SESSION_SELECTOR_VIDEO),
    Path(SESSION_SELECTOR_VIDEO_BRAND),
    Path(BRANDING_DIR) / "cprp_logo_video_variant_2.mp4",
    Path(BRANDING_LOGO_IMAGE),
    Path(BRANDING_LOGO_ICON),
    caption="CPRP Session Selector",
    height=380,
):
    st.warning("CPRP Session Selector media not found in assets/.")

# Bloomberg Live audio/video option on main Session Selector page
render_bloomberg_audio_option(key_prefix="main_bb", height=280)

page_hero(
    f"{PROTOCOL_NAME} — Session Micro Selector",
    f"Official Rulebook v{RULEBOOK_VERSION} (Final) · rank MES · MNQ · MYM for range/channel reversion — or sit out",
    side="bull",
    desk_tag="SESSION DESK · MICRO SELECTOR",
)

st.markdown(
    f"""
> *“Which micro should I focus on for range/channel reversion right now — or should I sit out?”*  
> *Trade the boundaries. Respect the structure. Control the risk.*
"""
)

with candle_expander("Purpose, who it is for, and how it fits your process", side="bull", expanded=True, kind="up"):
    st.markdown(
        f"""
**Purpose**
- Rank the three micros for **support/resistance range or channel reversion** conditions.
- Flag whether price is at a **structure boundary** (valid) or **mid-structure** (avoid).
- Check whether the current **structure size fits your hard dollar stop** (${HARD_STOP_MIN_USD:.0f}–${HARD_STOP_MAX_USD:.0f}).
- Apply **static 1-Hour trend context**: be more selective when fading against the HTF trend.
- Suggest the **active chart pair** from approved pairs only (**15m+5m** default · **30m+15m** slow).
- Surface **desktop alerts** when the recommended micro changes.

**Who it is for**
- You, trading **only** MES / MNQ / MYM under the CPRP rulebook.
- Traders who want a mechanical pre-session and in-session **focus** tool.

**How it is intended to be used**
1. Run this app **before** you trade (and leave it open while you trade).
2. Take the **recommended micro** as your focus market for the session.
3. Open the suggested chart pair (**15m+5m** or **30m+15m**) plus a static **1-Hour** chart on **NinjaTrader Web**.
4. Build entries only with full confluence: **S/R → price action → volume → RSI**.
5. Route orders through **Ironbeam**.
6. Prefer **quality over frequency** (v1.5). Never override the hard stop or micros-only rule.

**What this is *not***
- Not a signal bot that tells you exact fill prices every tick.
- Not brokerage software; it **does not place or cancel orders**.
- Not live CME data — quotes are from **Yahoo Finance (delayed)**.
- Not financial advice. Futures trading involves substantial risk of loss.
"""
    )

st.info(
    "💡 **New here?** Open the left sidebar → **Help & navigation** for section-by-section "
    "app instructions, and the 📈 / 📉 / 📂 panels for full CPRP operating steps."
)

# ── Strategy operating instructions (Official Quick Reference v1.5) ──────
with candle_expander(
    "How to properly operate the strategy (CPRP Official Quick Reference v1.5)",
    side="bear",
    expanded=False,
    kind="doc",
):
    st.markdown(
        f"""
Official operating instructions for the **{PROTOCOL_NAME}**, distilled from the
**Official Quick Reference v{RULEBOOK_VERSION}** and **Rulebook Update v{RULEBOOK_VERSION}**
(the Official Rulebook v{RULEBOOK_VERSION} (Final) is authoritative).  
This selector chooses *which micro* to focus on; **you** still operate the Protocol on the charts.

> *Trade the boundaries. Respect the structure. Control the risk.*

---

### Step A — Session setup
1. Open this selector and note the **recommended micro** (or **SIT OUT**).
2. Trade **only** approved micros: **MES** (primary), **MNQ**, **MYM**. No other contracts.
3. Open the suggested **chart pair** on **NinjaTrader Web** (approved pairs only):

| Situation | Structure | Execution | Role |
|-----------|-----------|-----------|------|
| **Default / most sessions** | **15-minute** | **5-minute** | Cleaner RSI, better range definition, still responsive |
| Larger / slower / lower volume | **30-minute** | **15-minute** | Highest quality S/R, least noise |

4. Keep a **static 1-Hour** chart in a separate window (4-Hour acceptable).  
   *Mandatory context filter only — never generates entries.*
5. Prefer **MES** unless MNQ or MYM is **clearly** superior. Prefer **quality over frequency**.

**Chart roles:** Structure chart = S/R · Execution chart = entry timing.  


---

### Step B — Build structure (do not trade until confirmed)
Identify a **confirmed** Support/Resistance **range** (range-bound mean-reversion edge).

| Requirement | Rule |
|-------------|------|
| Zones | **Sell confirmed resistance · Buy confirmed support** |
| Clarity | Structure must be unambiguous — if unclear, **stand aside** |
| Break rule | New session highs/lows that **break the prior range** → **pause** (do not hunt lower-TF bounces) |

---

### Step C — Confirmation hierarchy (v1.5 — in this order)
1. **Confirmed S/R** level of the active range (structure chart)
2. **Price action** at the level (rejection, absorption, engulfs)
3. **Volume** confirmation
4. **RSI** (mainly divergence on execution TF; absolute levels more useful on 15m/30m)

**RSI rules (v1.5)**
- Prefer **divergence at S/R** over absolute 70/30 extremes
- On 15m/30m: RSI extremes are **alerts / preparation only** — mid-range → wait
- RSI is **secondary**; entry still requires confirmed S/R + price action + volume
- Optional: RSI **7 or 9** on execution chart for divergence only; keep **14** on structure chart

Also confirm hard stop fits **−${HARD_STOP_MIN_USD:.0f} to −${HARD_STOP_MAX_USD:.0f}** and that no structure-break pause is active.

If **any** required item fails → **no trade**.

---

### Step D — Hard risk rule (non-negotiable)
- Maximum loss per trade: **−${HARD_STOP_MIN_USD:.0f} to −${HARD_STOP_MAX_USD:.0f}**
- Exit **immediately** when the hard limit is hit
- **No averaging down** · stay on micros only

---

### Step E — Structure break & pause
- After any S/R break: **flatten** and pause **{STRUCTURE_BREAK_PAUSE_MINUTES} minutes**
  **or until a new clear range forms** on the higher structure chart
- Do **not** chase lower-TF bounces after a break
- Wait for new clear structure before taking setups again

---

### Step F — Operational discipline
- **Fewer, higher-quality trades** preferred over high-frequency noise trades
- Prefer **MES**; journal and review vs these rules
- **No discretionary overrides** — the Protocol is complete as written
- Platform preference: **NinjaTrader Web** (high/low display)

---

### How the selector fits (do not reverse these roles)
| This app does | You still do on the platform |
|---------------|------------------------------|
| Rank MES / MNQ / MYM for session suitability | Confirm real S/R structure visually |
| Flag boundary vs mid-structure (proxy) | Apply confirmation hierarchy before entry |
| Check structure width vs hard dollar stop | Place / manage / exit orders |
| Suggest chart pair (v1.5 defaults) + 1H context | Enforce hard stop and structure-break pause |
| Alert when the pick changes | Prefer quality over frequency |

Futures trading involves substantial risk of loss. Official documents are personal trading aids, not investment advice.
"""
    )

# ── Run analysis ─────────────────────────────────────────────────────────
with st.spinner("Pulling MES / MNQ / MYM data and scoring structure (incl. 1H context)…"):
    rec = analyze_all(hard_stop_usd=float(hard_stop))
    st.session_state.last_rec = rec
    st.session_state.history.append(
        {
            "time": rec.as_of,
            "pick": rec.recommended or "SIT OUT",
            "scores": {s.short: s.score for s in rec.scores},
        }
    )

if desktop_alerts:
    st.session_state.tracker.maybe_alert(rec.recommended, rec.sit_out, rec.alert_message)

# ── Big recommendation banner ────────────────────────────────────────────
st.markdown("### Current session recommendation")
if rec.sit_out or not rec.recommended:
    st.error(f"### 🛑 {rec.alert_message}")
else:
    color = {"MES": "🟢", "MNQ": "🔵", "MYM": "🟣"}.get(rec.recommended, "⚪")
    st.success(f"### {color} Recommended session micro: **{rec.recommended}**")
    st.info(rec.summary)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("As of (ET)", rec.as_of)
c2.metric("Session phase", rec.session_phase.replace("_", " ").title())
c3.metric("Chart pair", rec.chart_pair_global.split("(")[0].strip())
c4.metric("Static HTF", rec.static_htf_global.split("(")[0].strip() if rec.static_htf_global else "1-Hour")
c5.metric("Trade threshold", f"{MIN_SCORE_TO_TRADE:.0f}+")

st.markdown("---")

# ── Per-instrument cards ─────────────────────────────────────────────────
desk_section("Micro comparison cards", side="bull")
st.caption("⭐ marks the current pick. Expand the candle **Score breakdown** on any card for reasons and warnings.")

if not rec.scores:
    st.warning("No scores available. Check internet / Yahoo Finance availability.")
else:
    cols = st.columns(len(rec.scores))
    for col, s in zip(cols, sorted(rec.scores, key=lambda x: x.priority)):
        is_pick = rec.recommended == s.short and not rec.sit_out
        with col:
            st.subheader(f"{'⭐ ' if is_pick else ''}{s.short}")
            st.caption(s.name)
            st.metric("Session score", f"{s.score:.1f}", help=s.grade)
            st.write(f"**{s.grade}**")
            st.write(f"Last: `{s.last_price}`")
            st.write(f"Structure: `{s.session_low}` – `{s.session_high}`")
            st.write(f"Width: **{s.range_width_pts} pts** · **${s.range_width_usd:.0f}**")
            st.write(f"Stop @ ${hard_stop}: **{s.stop_pts_at_default} pts**")
            st.write(
                f"In-structure position: **{s.position_in_range:.0%}** "
                + ("(boundary)" if s.at_extreme else "(mid)")
            )
            st.write(f"1H context: **{s.htf_label}**")
            st.progress(min(s.score / 100.0, 1.0))
            card_side = "bull" if is_pick or s.at_extreme else "bear"
            with candle_expander("Score breakdown", side=card_side):
                st.write(f"Structure / range-channel quality: {s.structure_score}")
                st.write(f"Risk fit: {s.risk_fit_score} — {s.range_fit_label}")
                st.write(f"1H trend context: {s.trend_context_score} — {s.htf_label}")
                st.write(f"Volume: {s.volume_score}")
                st.write(f"Volatility: {s.volatility_score}")
                st.write(f"Active chart pair: {s.chart_pair}")
                st.write(f"Static HTF: {s.static_htf}")
                if s.reasons:
                    st.markdown("**Why**")
                    for r in s.reasons:
                        st.markdown(f"- {r}")
                if s.warnings:
                    st.markdown("**Watch**")
                    for w in s.warnings:
                        st.markdown(f"- ⚠️ {w}")

st.markdown("---")

# ── Comparison table + chart ──────────────────────────────────────────────
if rec.scores:
    left, right = st.columns([1, 1.2])
    with left:
        desk_section("Head-to-head", side="bull")
        st.caption("Sorted by score. Use this to see how close the race is between micros.")
        table = pd.DataFrame(
            [
                {
                    "Micro": s.short,
                    "Score": s.score,
                    "Priority": s.priority,
                    "Last": s.last_price,
                    "Structure $": s.range_width_usd,
                    "At boundary": "Yes" if s.at_extreme else "No",
                    "1H bias": s.htf_bias,
                    "Structure": s.structure_score,
                    "Risk fit": s.risk_fit_score,
                    "1H ctx": s.trend_context_score,
                    "Volume": s.volume_score,
                }
                for s in sorted(rec.scores, key=lambda x: -x.score)
            ]
        )
        st.dataframe(table, use_container_width=True, hide_index=True)

        fig_bar = go.Figure(
            data=[
                go.Bar(
                    x=[s.short for s in sorted(rec.scores, key=lambda x: x.priority)],
                    y=[s.score for s in sorted(rec.scores, key=lambda x: x.priority)],
                    marker_color=[
                        "#C9A84C" if (rec.recommended == s.short and not rec.sit_out) else "#4A5568"
                        for s in sorted(rec.scores, key=lambda x: x.priority)
                    ],
                    text=[f"{s.score:.1f}" for s in sorted(rec.scores, key=lambda x: x.priority)],
                    textposition="outside",
                )
            ]
        )
        fig_bar.add_hline(
            y=MIN_SCORE_TO_TRADE,
            line_dash="dash",
            line_color="#D4AF37",
            annotation_text="Trade threshold",
        )
        fig_bar.update_layout(
            title="Session suitability score (CPRP)",
            yaxis_title="Score",
            yaxis_range=[0, 105],
            height=360,
            margin=dict(t=40, b=20),
            paper_bgcolor="rgba(6,11,22,0)",
            plot_bgcolor="rgba(15,27,45,0.6)",
            font=dict(color="#e8edf5"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with right:
        desk_section("Price structure (5m)", side="bear")
        st.caption(
            "Green/red dotted lines mark the analyzed window high/low (proxy support/resistance). "
            "Confirm real levels on NinjaTrader. Keep a separate **1-Hour** chart for long-term context (§2)."
        )
        pick_symbol = (
            rec.recommended
            if rec.recommended
            else sorted(rec.scores, key=lambda x: -x.score)[0].short
        )
        options = [s.short for s in sorted(rec.scores, key=lambda x: x.priority)]
        chart_choice = st.selectbox(
            "Chart micro",
            options,
            index=options.index(pick_symbol),
        )
        try:
            inst = INSTRUMENTS[chart_choice]
            bars = fetch_bars(inst.symbol).tail(120)
            fig = go.Figure(
                data=[
                    go.Candlestick(
                        x=bars.index,
                        open=bars["Open"],
                        high=bars["High"],
                        low=bars["Low"],
                        close=bars["Close"],
                        name=chart_choice,
                    )
                ]
            )
            sh = float(bars["High"].max())
            sl = float(bars["Low"].min())
            fig.add_hline(
                y=sh,
                line_color="#8B9BB4",
                line_dash="dot",
                annotation_text="Session high / resistance zone",
            )
            fig.add_hline(
                y=sl,
                line_color="#C9A84C",
                line_dash="dot",
                annotation_text="Session low / support zone",
            )
            fig.update_layout(
                title=f"{chart_choice} — structure extremes",
                xaxis_rangeslider_visible=False,
                height=420,
                margin=dict(t=40, b=20),
                paper_bgcolor="rgba(6,11,22,0)",
                plot_bgcolor="rgba(15,27,45,0.6)",
                font=dict(color="#e8edf5"),
            )
            st.plotly_chart(fig, use_container_width=True)
            # Show HTF bias for selected micro
            picked = next((x for x in rec.scores if x.short == chart_choice), None)
            if picked:
                st.caption(f"**Static 1H context:** {picked.htf_label} — {picked.static_htf}")
        except Exception as exc:
            st.warning(f"Chart unavailable: {exc}")

# ── Pre-trade checklist (Official Quick Reference v1.5) ──────────────────
st.markdown("---")
desk_section("Pre-trade confirmation checklist (Quick Reference v1.5)", side="bear")
st.caption(
    "Confirmation hierarchy from CPRP Quick Reference v1.5 — apply in order. "
    "If any item fails, stand aside. "
    f"After a structure break, pause at least {STRUCTURE_BREAK_PAUSE_MINUTES} minutes "
    "(or until a new clear range forms). "
    "Hard risk: max loss −$50 to −$100 · exit immediately at limit · no averaging down."
)
checks = [
    "1. Confirmed Support / Resistance of the active range (structure chart)",
    "2. Price at/near boundary — Support = long | Resistance = short (not mid-range)",
    "3. Price action at the level (rejection, absorption, engulfs)",
    "4. Volume confirmation",
    "5. RSI secondary confirm (prefer divergence at S/R; absolute 70/30 not mandatory alone)",
    f"6. Hard stop fits inside −${hard_stop} risk limit (−$50 to −$100 max)",
    f"7. No recent structure break (or {STRUCTURE_BREAK_PAUSE_MINUTES}-min pause / new clear range)",
]
for item in checks:
    st.checkbox(item, key=f"chk_{item[:28]}")

with candle_expander("RSI rules & exits (Quick Reference v1.5)", side="bear", expanded=False, kind="doc"):
    st.markdown(
        f"""
**RSI (v1.5)**
- Prefer **divergence at S/R** over absolute 70/30 extremes
- On 15m/30m: RSI extremes are alerts / preparation only — not automatic entries
- RSI extreme while **mid-range** → wait for boundary + PA + volume
- RSI is **secondary**; full entry still needs confirmed S/R + PA + volume
- Optional: RSI 7/9 on execution chart for divergence only; keep RSI 14 on structure

**Structure break**
| Action | Rule |
|--------|------|
| Break of prior range (new session high/low) | **Pause** — do not hunt lower-TF bounces |
| After break | Flatten · wait **{STRUCTURE_BREAK_PAUSE_MINUTES} min** or **new clear range** |
| Hard risk | **−${HARD_STOP_MIN_USD:.0f} to −${HARD_STOP_MAX_USD:.0f}** · exit at limit · no averaging down |
| Trade count | **Fewer, higher-quality** trades preferred (v1.5) |
"""
    )

# ── Quick Reference + Trading Journal (side-by-side) ─────────────────────
# Users can write journal notes without leaving the reference card.
_default_jr_micro = ""
if rec.recommended and not rec.sit_out:
    _default_jr_micro = rec.recommended
render_reference_and_journal_side_by_side(default_micro=_default_jr_micro)

# Extra rulebook base download (optional)
_rb_base_main = Path(RULEBOOK_BASE_PDF)
if _rb_base_main.is_file():
    with candle_expander("More documents (Official Rulebook base)", side="bull", expanded=False, kind="folder"):
        st.download_button(
            label="📂 Download Official Rulebook base (PDF)",
            data=_rb_base_main.read_bytes(),
            file_name=RULEBOOK_BASE_DOWNLOAD_NAME,
            mime="application/pdf",
            use_container_width=True,
            help=f"Official Rulebook v{RULEBOOK_BASE_VERSION} (Final).",
        )
        st.caption(
            "Open **Trading Journal** in the sidebar for full history, filters, and edit/delete. "
            "On this page the journal sits next to the Quick Reference so you can take notes live."
        )

from disclosure import render_disclosure_footer

render_disclosure_footer()
st.caption(
    f"Personal tool aligned to {PROTOCOL_NAME} Official Rulebook v{RULEBOOK_VERSION} (Final). "
    "Does not place orders. Market data via Yahoo Finance (delayed). "
    f"© 2026 {CREATOR}."
)

# ── Auto-refresh (Session Selector only) ──────────────────────────────────
if auto_refresh:
    time.sleep(refresh_sec)
    st.rerun()
