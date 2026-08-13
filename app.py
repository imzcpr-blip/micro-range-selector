"""
Cooper Precision Reversion Protocol (CPRP) — Session Micro Selector
Official Rulebook v1.6 (Multi-Timeframe Hierarchy & Order Flow)

Run:
  streamlit run app.py
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Load config first (local module — avoid shadowing / partial import issues on Cloud)
import config as _cprp_cfg

ADMIN_ROLE_LABEL = _cprp_cfg.ADMIN_ROLE_LABEL
APP_NAME = _cprp_cfg.APP_NAME
BRANDING_DIR = _cprp_cfg.BRANDING_DIR
BRANDING_LOGO_ICON = _cprp_cfg.BRANDING_LOGO_ICON
BRANDING_LOGO_IMAGE = _cprp_cfg.BRANDING_LOGO_IMAGE
BRANDING_LOGO_VIDEO = _cprp_cfg.BRANDING_LOGO_VIDEO
BRANDING_LOGO_VIDEO_ALT = _cprp_cfg.BRANDING_LOGO_VIDEO_ALT
SIDEBAR_VIDEO = getattr(_cprp_cfg, "SIDEBAR_VIDEO", BRANDING_DIR / "cprp_sidebar_video.mp4")
SIDEBAR_VIDEO_BRAND = getattr(_cprp_cfg, "SIDEBAR_VIDEO_BRAND", BRANDING_DIR / "cprp_sidebar_video.mp4")
SIDEBAR_VIDEO_BRAND_GIF = getattr(
    _cprp_cfg, "SIDEBAR_VIDEO_BRAND_GIF", BRANDING_DIR / "cprp_sidebar_video.gif"
)
SIDEBAR_VIDEO_GIF = getattr(_cprp_cfg, "SIDEBAR_VIDEO_GIF", Path(BRANDING_DIR).parent / "cprp_sidebar_video.gif")
SESSION_SELECTOR_IMAGE = getattr(
    _cprp_cfg, "SESSION_SELECTOR_IMAGE", Path(BRANDING_DIR).parent / "cprp_session_selector_image.jpg"
)
SESSION_SELECTOR_IMAGE_BRAND = getattr(
    _cprp_cfg, "SESSION_SELECTOR_IMAGE_BRAND", BRANDING_DIR / "cprp_session_selector_image.jpg"
)
SESSION_SELECTOR_BRAND_LOGO = getattr(
    _cprp_cfg, "SESSION_SELECTOR_BRAND_LOGO", Path(BRANDING_DIR).parent / "cprp_strategies_brand_logo.jpg"
)
SESSION_SELECTOR_BRAND_LOGO_BRAND = getattr(
    _cprp_cfg, "SESSION_SELECTOR_BRAND_LOGO_BRAND", BRANDING_DIR / "cprp_strategies_brand_logo.jpg"
)
SESSION_SELECTOR_VIDEO = getattr(
    _cprp_cfg, "SESSION_SELECTOR_VIDEO", Path(BRANDING_DIR).parent / "cprp_session_selector_video.mp4"
)
SESSION_SELECTOR_VIDEO_BRAND = getattr(
    _cprp_cfg, "SESSION_SELECTOR_VIDEO_BRAND", BRANDING_DIR / "cprp_session_selector_video.mp4"
)
SESSION_SELECTOR_VIDEO_BRAND_GIF = getattr(
    _cprp_cfg, "SESSION_SELECTOR_VIDEO_BRAND_GIF", BRANDING_DIR / "cprp_session_selector_video.gif"
)
SESSION_SELECTOR_VIDEO_GIF = getattr(
    _cprp_cfg, "SESSION_SELECTOR_VIDEO_GIF", Path(BRANDING_DIR).parent / "cprp_session_selector_video.gif"
)
SESSION_SELECTOR_VARIANT_GIF = getattr(
    _cprp_cfg, "SESSION_SELECTOR_VARIANT_GIF", BRANDING_DIR / "cprp_logo_video_variant_2.gif"
)
BRANDING_OFFICIAL_SEAL = getattr(_cprp_cfg, "BRANDING_OFFICIAL_SEAL", BRANDING_DIR / "cprp_official_seal.png")
BRANDING_OFFICIAL_SEAL_ANIM = getattr(
    _cprp_cfg, "BRANDING_OFFICIAL_SEAL_ANIM", Path(BRANDING_DIR).parent / "cprp_official_seal_anim.gif"
)
BRANDING_OFFICIAL_SEAL_ANIM_BRAND = getattr(
    _cprp_cfg, "BRANDING_OFFICIAL_SEAL_ANIM_BRAND", BRANDING_DIR / "cprp_official_seal_anim.gif"
)
BRANDING_OFFICIAL_SEAL_BRAND = getattr(
    _cprp_cfg, "BRANDING_OFFICIAL_SEAL_BRAND", BRANDING_DIR / "cprp_official_seal.png"
)
BRANDING_OFFICIAL_SEAL_BRAND_JPG = getattr(
    _cprp_cfg, "BRANDING_OFFICIAL_SEAL_BRAND_JPG", BRANDING_DIR / "cprp_official_seal.jpg"
)
BRANDING_OFFICIAL_SEAL_JPG = getattr(
    _cprp_cfg, "BRANDING_OFFICIAL_SEAL_JPG", Path(BRANDING_DIR).parent / "cprp_official_seal.jpg"
)
CREATOR = _cprp_cfg.CREATOR
MEMBER_CHAT_HERO_IMAGE = _cprp_cfg.MEMBER_CHAT_HERO_IMAGE
MEMBER_CHAT_HERO_VIDEO = _cprp_cfg.MEMBER_CHAT_HERO_VIDEO
FOUNDER_BIO = _cprp_cfg.FOUNDER_BIO
FOUNDER_NAME = _cprp_cfg.FOUNDER_NAME
FOUNDER_TAGLINE = _cprp_cfg.FOUNDER_TAGLINE
FOUNDER_TITLE = _cprp_cfg.FOUNDER_TITLE
HARD_STOP_DEFAULT_USD = _cprp_cfg.HARD_STOP_DEFAULT_USD
HARD_STOP_MAX_USD = _cprp_cfg.HARD_STOP_MAX_USD
HARD_STOP_MIN_USD = _cprp_cfg.HARD_STOP_MIN_USD
INSTRUMENTS = _cprp_cfg.INSTRUMENTS
MIN_SCORE_TO_TRADE = _cprp_cfg.MIN_SCORE_TO_TRADE
PROTOCOL_NAME = _cprp_cfg.PROTOCOL_NAME
PROTOCOL_SHORT = _cprp_cfg.PROTOCOL_SHORT
QUICK_REFERENCE_DOWNLOAD_NAME = _cprp_cfg.QUICK_REFERENCE_DOWNLOAD_NAME
QUICK_REFERENCE_IMAGE = _cprp_cfg.QUICK_REFERENCE_IMAGE
QUICK_REFERENCE_PDF = _cprp_cfg.QUICK_REFERENCE_PDF
RULEBOOK_BASE_DOWNLOAD_NAME = _cprp_cfg.RULEBOOK_BASE_DOWNLOAD_NAME
RULEBOOK_BASE_PDF = _cprp_cfg.RULEBOOK_BASE_PDF
RULEBOOK_BASE_VERSION = _cprp_cfg.RULEBOOK_BASE_VERSION
RULEBOOK_UPDATE_DOWNLOAD_NAME = _cprp_cfg.RULEBOOK_UPDATE_DOWNLOAD_NAME
RULEBOOK_UPDATE_PDF = _cprp_cfg.RULEBOOK_UPDATE_PDF
RULEBOOK_VERSION = _cprp_cfg.RULEBOOK_VERSION
STRUCTURE_BREAK_PAUSE_MINUTES = _cprp_cfg.STRUCTURE_BREAK_PAUSE_MINUTES

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
from micro_futures_news import render_micro_futures_news_panel
from micros_guide import render_micros_guide_panel
from platforms_brokers import render_platforms_brokers_panel
from session_stats import render_session_wl_panel

try:
    from loop_media import render_loop_media
except ImportError:  # pragma: no cover — safety for partial deploys
    def render_loop_media(*candidates, caption=None, height=320, sidebar=False):  # type: ignore
        from pathlib import Path as _P
        for p in candidates:
            if p is None:
                continue
            path = _P(p)
            if path.is_file() and path.suffix.lower() in {".gif", ".jpg", ".jpeg", ".png", ".webp"}:
                if sidebar:
                    st.sidebar.image(str(path), use_container_width=True, caption=caption)
                else:
                    st.image(str(path), use_container_width=True, caption=caption)
                return True
            if path.is_file() and path.suffix.lower() == ".mp4":
                if sidebar:
                    st.sidebar.video(str(path), format="video/mp4", start_time=0, loop=True, muted=True)
                else:
                    st.video(str(path), format="video/mp4", start_time=0, loop=True, muted=True)
                if caption and not sidebar:
                    st.caption(caption)
                return True
        return False

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
st.sidebar.caption(f"Independent Micro desk · Rulebook v{RULEBOOK_VERSION}")
st.sidebar.caption(f"{CREATOR}")

# Icon legend — explains nav / panel emoji meanings (desk-style mini panel)
with st.sidebar.expander("Icon legend", expanded=False):
    st.markdown(
        """
A quick map of the floor markers you’ll see on pages and expanders:

| Icon | On the desk it means… |
|:----:|------------------------|
| 📈 | **Primary / constructive** — tools, setups, bull edges |
| 📉 | **Risk / filter** — caution, calendar, secondary edges |
| 📂 | **Rulebooks & files** — official documents |
| 📁 | **Brand & suites** — identity packs |
| 📃 | **Journal & pages** — session notes, blotter |
| 📄 | **Profile docs** — founder / about |
| 📺 | **Live desk feed** — Bloomberg-style news |
| 🔗 | **Off-floor links** — brokers, platforms, new tab |

Gold rail = primary. Steel rail = risk or secondary. Expand anything marked ▶ for the full story.
"""
    )
    st.caption("Floor legend · CPRP Strategies")

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
PAGE_MICRO_NEWS = "Micro Futures News"
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
    PAGE_MICRO_NEWS,     # 7. TradingView micro futures news
    PAGE_NEWS,           # 8. Live news desk
    PAGE_JOURNAL,        # 9. Private session notes
    PAGE_SESSION_WL,     # 10. Shared session stats
    PAGE_COMMUNITY,      # 11. Ideas board
    PAGE_CHAT,           # 12. Live member chat
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

# ── Micro Futures News (TradingView Top Stories for MES/MNQ/MYM) ──────────
if page == PAGE_MICRO_NEWS:
    render_micro_futures_news_panel()
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
        f"Official identity for **CPRP Strategies** · seal · logos · motion · Scalping brand",
        side="bull",
        desk_tag="BRAND DESK · FLOOR IDENTITY",
    )

    # CPRP Strategies Brand Logo (Session Selector + brand suite hero)
    desk_section("CPRP Strategies Brand Logo", side="bull")
    _brand_logo_paths = [
        Path(BRANDING_DIR) / "cprp_strategies_brand_logo.jpg",
        Path(getattr(_cprp_cfg, "SESSION_SELECTOR_BRAND_LOGO", Path(BRANDING_DIR).parent / "cprp_strategies_brand_logo.jpg")),
        Path(getattr(_cprp_cfg, "SESSION_SELECTOR_IMAGE", Path(BRANDING_DIR).parent / "cprp_session_selector_image.jpg")),
    ]
    _bl_cols = st.columns([1, 1.6, 1])
    with _bl_cols[1]:
        _bl_shown = False
        for _bp in _brand_logo_paths:
            if _bp.is_file():
                st.image(
                    str(_bp),
                    use_container_width=True,
                    caption="CPRP Strategies Brand Logo · Session Selector",
                )
                st.download_button(
                    label="📁 Download Strategies Brand Logo",
                    data=_bp.read_bytes(),
                    file_name="CPRP_Strategies_Brand_Logo.jpg",
                    mime="image/jpeg",
                    key=f"dl_strategies_brand_logo_{_bp.name}",
                    use_container_width=True,
                )
                _bl_shown = True
                break
        if not _bl_shown:
            st.warning("CPRP Strategies Brand Logo not found — run branding sync.")

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
                    key=f"dl_suite_{i}_{img.stem}",
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
                        key=f"dl_anim_{i}_{media.stem}",
                        use_container_width=True,
                    )
                elif media.suffix.lower() == ".mp4":
                    st.download_button(
                        label="📁 Download MP4",
                        data=media.read_bytes(),
                        file_name=media.name,
                        mime="video/mp4",
                        key=f"dl_anim_mp4_{i}_{media.stem}",
                        use_container_width=True,
                    )
    else:
        st.caption("No official animated brand media found yet.")

    # CPRP Scalping brand motion (strategy logo)
    desk_section("CPRP Scalping brand motion", side="bear")
    _scalp_media_paths = [
        Path(getattr(_cprp_cfg, "SCALPING_VIDEO_GIF_BRAND", BRANDING_DIR / "cprp_scalping_video.gif")),
        Path(getattr(_cprp_cfg, "SCALPING_VIDEO_GIF", Path(BRANDING_DIR).parent / "cprp_scalping_video.gif")),
        Path(getattr(_cprp_cfg, "SCALPING_VIDEO_MP4_BRAND", BRANDING_DIR / "cprp_scalping_video.mp4")),
        Path(getattr(_cprp_cfg, "SCALPING_VIDEO_MP4", Path(BRANDING_DIR).parent / "cprp_scalping_video.mp4")),
    ]
    _scalp_shown = False
    for _sp in _scalp_media_paths:
        if _sp.is_file():
            st.caption("Official looping logo for **CPRP Scalping** strategy documents & desk panels.")
            render_loop_media(_sp, height=300, caption="CPRP Scalping · logo motion (loop)")
            mime = "image/gif" if _sp.suffix.lower() == ".gif" else "video/mp4"
            st.download_button(
                label=f"📁 Download {_sp.name}",
                data=_sp.read_bytes(),
                file_name=_sp.name,
                mime=mime,
                key=f"dl_scalp_brand_{_sp.name}",
                use_container_width=True,
            )
            _scalp_shown = True
            break
    if not _scalp_shown:
        st.info("CPRP Scalping video not found — run brand sync + `python scripts/convert_videos_to_gifs.py`.")

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
    seen_names: set[str] = set()

    def _add_media(p: Path) -> None:
        if not p.is_file():
            return
        # Dedupe by filename so assets/ and assets/branding/ copies don't collide
        key_name = p.name.lower()
        if key_name in seen_names:
            return
        seen_names.add(key_name)
        ordered.append(p)

    for p in (
        Path(BRANDING_LOGO_VIDEO),
        Path(BRANDING_LOGO_VIDEO_ALT),
        Path(BRANDING_DIR) / "cprp_logo_video_main.gif",
        Path(BRANDING_DIR) / "cprp_logo_video_alt.gif",
        Path(MEMBER_CHAT_HERO_VIDEO),
    ):
        _add_media(Path(p))
    for v in gifs:
        if v.suffix.lower() in {".gif", ".mp4"}:
            _add_media(Path(v))

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
        "cprp_session_selector_video": "Session Selector · Brand Logo Video",
        "cprp_brand_logo_video": "CPRP Brand Logo Video",
        "cprp_sidebar_video": "Sidebar media",
        "cprp_scalping_video": "CPRP Scalping logo motion",
    }

    if ordered:
        cols = st.columns(2)
        for i, v in enumerate(ordered):
            with cols[i % 2]:
                title = video_labels.get(v.stem.lower(), v.stem.replace("_", " ").title())
                st.markdown(f"**{title}**")
                render_loop_media(v, height=280)
                # Unique keys: index + stem (never filename alone — duplicates crash Streamlit)
                if v.suffix.lower() == ".gif":
                    st.download_button(
                        label="📁 Download GIF",
                        data=v.read_bytes(),
                        file_name=v.name,
                        mime="image/gif",
                        key=f"dl_brand_gif_{i}_{v.stem}",
                        use_container_width=True,
                    )
                elif v.suffix.lower() == ".mp4":
                    st.download_button(
                        label="📁 Download MP4",
                        data=v.read_bytes(),
                        file_name=v.name,
                        mime="video/mp4",
                        key=f"dl_brand_mp4_{i}_{v.stem}",
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

    # Dedupe stills by filename
    stills: list[Path] = []
    seen_stills: set[str] = set()
    for img in imgs:
        n = img.name.lower()
        if n in seen_stills:
            continue
        seen_stills.add(n)
        stills.append(img)

    if stills:
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
            "cprp_dark_support_resistance_theme": "Dark Support / Resistance theme",
            "cprp_lock_in_theme": "Lock-in theme",
            "cprp_logo_classic": "Classic logo",
            "cprp_logo_icon": "App icon",
            "cprp_logo_primary": "Primary logo",
            "cprp_member_chat_poster": "Member Chat poster",
            "cprp_strategies_brand_logo": "CPRP Strategies Brand Logo",
            "cprp_session_selector_image": "Session Selector brand image",
        }
        cols = st.columns(3)
        for i, img in enumerate(stills):
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
                    key=f"dl_brand_still_{i}_{img.stem}",
                    use_container_width=True,
                )
    else:
        st.caption("No still images found.")

    with candle_expander("Brand usage notes", side="bull", expanded=False, kind="page"):
        st.markdown(
            f"""
The brand is the same standard as the trading: clean, deliberate, no noise.

- Prefer **looping logo GIFs** for headers, chat, and motion on the desk.  
- Stills cover favicon, downloads, and offline kits.  
- Name: **{PROTOCOL_NAME} ({PROTOCOL_SHORT})** · desk brand **CPRP Strategies**  
- Founder: **{FOUNDER_NAME}**  
- Rulebook: **Official Rulebook v{RULEBOOK_VERSION}**  
- Line we live by: *Trade the boundaries. Respect the structure. Control the risk.*
"""
        )
    st.caption(f"© 2026 {CREATOR}. CPRP Strategies brand assets.")
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
**Desk:** CPRP Strategies · **Protocol:** {PROTOCOL_NAME} ({PROTOCOL_SHORT})  
**Rulebook:** Official Rulebook v{RULEBOOK_VERSION} · Scalping v{_cprp_cfg.SCALPING_VERSION}  
**Focus:** Micro E-mini day-trading — primary **range/channel reversion**, secondary **1m scalping** when the tape is quiet
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
Patterns, structure, and probability — measured, not mythologized.
"""
        )
        c3.markdown(
            """
**Structure first**  
Confirmed S/R, multi-timeframe confluence, hard dollar risk. No freestyle.
"""
        )
        c4.markdown(
            """
**Ownership**  
A craft written, broken, rewritten — and still owned by the person who built it.
"""
        )

    st.info(
        "Personal session desk for CPRP Strategies — not a broker, not a signal service. "
        f"{_cprp_cfg.DISCLAIMER_CAPTION}"
    )
    from disclosure import render_disclosure_footer

    render_disclosure_footer()
    st.caption(f"© 2026 {FOUNDER_NAME}. All rights reserved.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════
# SESSION SELECTOR — sidebar help + controls
# ══════════════════════════════════════════════════════════════════════════
st.sidebar.header("📖 Help & navigation")
st.sidebar.caption("Expand ▶ for the playbook · collapse when you know the floor")
with st.sidebar.expander("▶ How to use this desk (start here)", expanded=True):
    st.markdown(
        f"""
This is your **pre-session and in-session focus tool** for **{PROTOCOL_NAME}** — not a robot, not a broker, not a substitute for reading the chart.

**What you’re solving:**  
Which micro deserves your attention right now — **MES, MNQ, or MYM** — under written CPRP rules? Sometimes the honest answer is **sit out**. Sometimes the tape also offers **CPRP Scalping** as a second protocol. You choose; the desk reports.

**A clean session flow**
1. Set your **hard dollar stop** ($50–$100). That number is non-negotiable in the rulebook.  
2. Read the **top banner** — reversion pick, scalping option, both, or stand aside.  
3. Walk the **three micro cards** — scores, structure width, boundary vs mid, 60m bias.  
4. Open **Score breakdown** when you want the “why,” not just the grade.  
5. Confirm structure on **Head-to-head** and the **5m structure chart**.  
6. Keep a **static 60-minute** window open for bias (context only — never entries).  
7. Run the **official operating steps** and the **full pre-trade checklist** before you click buy or sell on NinjaTrader / Ironbeam.  
8. Leave **auto-refresh** on so the desk updates as the session evolves.

**Hard limits of this tool**
- It does **not** place or manage orders.  
- It does **not** replace your eyes on real S/R.  
- Market data is **Yahoo delayed** — session focus, not tick sniping.
"""
    )

with st.sidebar.expander("▶ What each section of the screen means"):
    st.markdown(
        f"""
| Area | What a professional reads it as |
|------|----------------------------------|
| **Top banner** | Today’s **protocol options**: Reversion, Scalping, both, or sit out |
| **Strategy options** | Explicit list of what the desk is offering — preference is yours |
| **Metrics row** | Clock (ET), session phase, chart pair, 60m context, reversion bar ({MIN_SCORE_TO_TRADE:.0f}+) |
| **Three cards** | Per-micro scorecard: price, structure $, stop distance, boundary, HTF |
| **Score breakdown** | The honest work — reasons, warnings, structure vs risk fit |
| **Head-to-head** | Who’s winning the race between micros right now |
| **Bar chart** | Visual score race; gold line = minimum bar for reversion |
| **Price structure** | 5m candles with session high/low as **proxy** S/R (confirm live) |
| **Operating steps** | Full CPRP process from the Official Quick Reference |
| **Checklist** | Every gate before an entry — miss one, no trade |
| **Quick References** | Side-by-side Reversion + Scalping one-pagers |
"""
    )

with st.sidebar.expander("▶ Sidebar controls, plain English"):
    st.markdown(
        """
- **Hard dollar stop** — Rulebook risk cap per trade ($50–$100). Shapes whether the structure “fits” your money.  
- **Auto-refresh** — Keeps the desk honest as conditions change.  
- **Refresh every (sec)** — How often we re-pull Yahoo and re-score. Slower = fewer calls.  
- **Desktop alerts** — A tap on the shoulder when the pick (or sit-out) flips.  
- **Analyze now** — Don’t wait for the timer; re-run on command.
"""
    )

with st.sidebar.expander("▶ How scores are built (rulebook map)"):
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
| Rejection / RSI | §4 / v1.6 | Wick rejection; RSI secondary (elevated may = strength) |
| Volatility | §5 | Quiet enough for a micro hard stop |

**Near ties:** prefer **MES → MNQ → MYM** (§8). **Quality over frequency** (v1.6).  
**Order flow** (Bid/Ask power) is confirmed on your platform — not scored here.

**Grades**
- **A** 75+ strong candidate  
- **B** 65+ tradeable with full confluence  
- **C** 55+ marginal — wait for boundary + confirm  
- **D** below threshold — prefer sit-out / other micro  
"""
    )

with st.sidebar.expander("▶ How to read a recommendation"):
    st.markdown(
        f"""
- **CPRP Reversion** — Primary protocol. That micro gets your range/channel focus and full checklist.  
- **CPRP Scalping** — Secondary protocol when the environment score clears. Preference is allowed; rules still bind.  
- **Both available** — Two clean options. One trade, one rulebook — pick, don’t mash.  
- **Sit out** — Nothing cleared. Standing aside is a professional outcome.  
- **At boundary** — Near support or resistance; the only honest entry zone for reversion.  
- **Mid-structure** — Not an invitation. Wait, even if RSI looks dramatic.  
- **60m bias** — Context only: ranging favors fades; strong trends demand selectivity.  
- **Chart pairs** — **15m+5m** when the room is clean; **30m+15m** when it’s slow, early, or choppy.  
- **Order flow** — Bids buy; asks sell. Confirm on the platform at the level.  
- **Structure break** — Decisive close through the map → flatten and pause **{STRUCTURE_BREAK_PAUSE_MINUTES} minutes** (or until a new map forms).
"""
    )

with st.sidebar.expander("▶ How to operate the strategy (official Quick Reference)", expanded=False):
    st.markdown(
        f"""
Source: **CPRP Official Quick Reference v{RULEBOOK_VERSION}**  
(Official Rulebook v{RULEBOOK_VERSION} is authoritative · Multi-TF hierarchy & order flow).

*“Trade the boundaries. Respect the structure. Control the risk.”*

### 1. Strategy identity
**Intraday range / channel reversion** on **MES** (primary), **MNQ**, **MYM** — **not scalping**.  
**Sell confirmed resistance · Buy confirmed support** until structure breaks.  
Hard risk **−${HARD_STOP_MIN_USD:.0f} to −${HARD_STOP_MAX_USD:.0f}** max per trade.  
Pause **{STRUCTURE_BREAK_PAUSE_MINUTES} minutes** (or until new clear structure) after any S/R break.  
Static **60-minute (or 4H)** = overall bias only — never generates entries.

### 2. Multi-timeframe hierarchy (v1.6)
| Chart | Role | Use for |
|-------|------|---------|
| **60-minute (static)** | Overall bias / sentiment | Trend context only — never entries |
| **15m or 30m** | Structure & levels | Confirmed S/R + swing structure (“map”) |
| **5m or 15m** | Timing & pressure | Entry timing, rejection, order flow (“trigger”) |

### 3. Working pairs (select by conditions)
| Pair | When | Roles |
|------|------|-------|
| **15m + 5m (default)** | Normal volume, clean ranges, active session | 15m = structure · 5m = timing + pressure |
| **30m + 15m** | Pre-market, low volume, lunch, wide/choppy | 30m = structure · 15m = timing · 5m fine-tune only |

**No 1-minute charts.** Former 5m+1m pair is fully retired.

### 4. Order flow (v1.6)
- **Bid = buying power** · **Ask = selling power**  
- More aggressive asks → price tends down · more aggressive bids → price tends up  
- Shift in dominance at a **key level** is strong confirmation (hold or break)

### 5. RSI guidance (v1.6)
- Secondary confirmation only. Prefer **divergence at the actual S/R level**.  
- **Elevated RSI that stays high** often = **strong buying power still in control** — do **not** fade solely because it is overbought.  
- Wait for **structure break + order-flow shift + RSI failure to reclaim** before treating as exhaustion.  
- On structure TF: extremes = alerts only; mid-range → wait for boundary + PA + volume + order flow.  
- Optional RSI **7 or 9** on execution chart for divergence only; keep **14** on structure chart.

### 6. Confirmation hierarchy (v1.6)
1. Confirmed S/R on higher TF of working pair  
2. Price at/near boundary (Support = long · Resistance = short)  
3. Price-action rejection on lower TF  
4. Volume supports rejection / absorption  
5. **Order flow confirms** (bids defend / asks aggressive)  
6. RSI favorable (divergence preferred at level)  
7. Hard stop fits −$50 to −$100  
8. No recent structure break (or 30-min pause done)  
9. 60m bias not strongly opposing (or highly selective)

### 7. Key operating rules
- **New session highs:** old highs/lows lose relevance — trade **current developing structure**.  
- Hard dollar risk **−${HARD_STOP_MIN_USD:.0f} to −${HARD_STOP_MAX_USD:.0f}**. Micros only.  
- Early pre-market → default **30m+15m**. Prefer **MES** unless MNQ/MYM clearly superior.  
- **Fewer, higher-quality trades** — do not force scalping in slow markets.

### 8. Using *this selector* with the Protocol
1. Let the app pick the **session micro** (or sit out).  
2. Open the suggested chart pair + static 60m on NinjaTrader.  
3. Confirm structure, order flow, and the full checklist before ordering.  
4. Re-check after structure breaks or major session shifts.
"""
    )

with st.sidebar.expander("▶ Strategy hard rules (always)"):
    st.markdown(
        f"""
**Core philosophy**
- Trade only **confirmed** structure — never anticipate  
- Fade the **extremes** of the range/channel until structure fails  
- Confirm: **S/R → PA → volume → order flow → RSI** (v1.6)  
- Hard dollar risk limit on every trade — **no exceptions**  
- When structure breaks, **step aside** — do not force trades  
- Respect higher-TF bias — do not fight sustained buying/selling power  

**Operational rules (Quick Reference v{RULEBOOK_VERSION})**
- **Instruments:** MES, MNQ, MYM only — no other contracts  
- **Style:** Intraday range/channel reversion — **not scalping**  
- **Default charts:** **15m + 5m** (or **30m + 15m** pre-market / slow / choppy)  
- **Risk:** Hard stop **−${HARD_STOP_MIN_USD:.0f} to −${HARD_STOP_MAX_USD:.0f}** per trade  
- **Target:** Opposite boundary; partials at mid-range  
- **No averaging down.** Exit immediately at the hard limit  
- **After structure break:** Flat + **{STRUCTURE_BREAK_PAUSE_MINUTES}-min** pause (or until new clear structure)  
- **Prefer MES**; quality over frequency  
- Protocol is complete as written — no discretionary overrides  
"""
    )

with st.sidebar.expander("▶ Troubleshooting"):
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
    _rb_side_label = (
        "📂 Download Official Rulebook (PDF)"
        if "Official_Rulebook" in RULEBOOK_UPDATE_DOWNLOAD_NAME
        else "📂 Download Rulebook Update (PDF)"
    )
    st.sidebar.download_button(
        label=_rb_side_label,
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

# CPRP Scalping documents (secondary strategy)
st.sidebar.markdown("##### CPRP Scalping docs")
st.sidebar.caption(
    f"Secondary 1m Keltner protocol · v{_cprp_cfg.SCALPING_VERSION}"
)
_scalp_qr_pdf = Path(_cprp_cfg.SCALPING_QUICK_REFERENCE_PDF)
_scalp_qr_img = Path(_cprp_cfg.SCALPING_QUICK_REFERENCE_IMAGE)
_scalp_rb_pdf = Path(_cprp_cfg.SCALPING_RULEBOOK_PDF)
if _scalp_qr_pdf.is_file():
    st.sidebar.download_button(
        label="📄 Scalping Quick Reference (PDF)",
        data=_scalp_qr_pdf.read_bytes(),
        file_name=_cprp_cfg.SCALPING_QUICK_REFERENCE_DOWNLOAD_NAME,
        mime="application/pdf",
        use_container_width=True,
        key="sidebar_scalp_qr_pdf",
    )
if _scalp_qr_img.is_file():
    st.sidebar.download_button(
        label="📃 Scalping QR card (JPG)",
        data=_scalp_qr_img.read_bytes(),
        file_name=f"CPRP_Scalping_Quick_Reference_v{_cprp_cfg.SCALPING_VERSION}.jpg",
        mime="image/jpeg",
        use_container_width=True,
        key="sidebar_scalp_qr_jpg",
    )
if _scalp_rb_pdf.is_file():
    st.sidebar.download_button(
        label="📂 Scalping Official Rulebook (PDF)",
        data=_scalp_rb_pdf.read_bytes(),
        file_name=_cprp_cfg.SCALPING_RULEBOOK_DOWNLOAD_NAME,
        mime="application/pdf",
        use_container_width=True,
        key="sidebar_scalp_rulebook_pdf",
    )
if not (_scalp_qr_pdf.is_file() or _scalp_rb_pdf.is_file()):
    st.sidebar.caption(
        "Scalping docs missing — run **Sync docs** (Founder) or re-deploy assets."
    )

st.sidebar.markdown("---")
st.sidebar.caption(f"Pages: Selector · Branding · About · © {CREATOR}")

# ══════════════════════════════════════════════════════════════════════════
# MAIN — Session Selector header video + description + analysis
# ══════════════════════════════════════════════════════════════════════════
# Session Selector banner: Brand Logo Video (looping GIF/MP4), then stills / other fallbacks
if not render_loop_media(
    Path(SESSION_SELECTOR_VIDEO_GIF),
    Path(SESSION_SELECTOR_VIDEO_BRAND_GIF),
    Path(SESSION_SELECTOR_VIDEO),
    Path(SESSION_SELECTOR_VIDEO_BRAND),
    Path(BRANDING_DIR) / "cprp_brand_logo_video.gif",
    Path(BRANDING_DIR) / "cprp_brand_logo_video.mp4",
    Path(SESSION_SELECTOR_BRAND_LOGO),
    Path(SESSION_SELECTOR_BRAND_LOGO_BRAND),
    Path(SESSION_SELECTOR_IMAGE),
    Path(SESSION_SELECTOR_IMAGE_BRAND),
    Path(SESSION_SELECTOR_VARIANT_GIF),
    Path(BRANDING_DIR) / "cprp_logo_video_variant_2.mp4",
    Path(BRANDING_LOGO_IMAGE),
    Path(BRANDING_LOGO_ICON),
    caption="CPRP Brand Logo Video · Session Selector",
    height=380,
):
    st.warning("CPRP Session Selector media not found in assets/.")

# Bloomberg Live audio/video option on main Session Selector page
render_bloomberg_audio_option(key_prefix="main_bb", height=280)

page_hero(
    f"{PROTOCOL_NAME} — Session Micro Selector",
    f"CPRP Strategies · multi-protocol day-trader desk · Reversion v{RULEBOOK_VERSION} · Scalping v{_cprp_cfg.SCALPING_VERSION} · MES · MNQ · MYM",
    side="bull",
    desk_tag="SESSION DESK · FOCUS & PROTOCOL OPTIONS",
)

st.markdown(
    f"""
> *Trade the boundaries. Respect the structure. Control the risk.*

**CPRP Strategies** is an independent **Micro E-mini futures** desk — chart analysis with written protocols for different market conditions. Primary work is **range/channel reversion**. When the tape goes quiet, **CPRP Scalping** can appear as a second, rules-bound option. Both have been pressure-tested against the Official Rulebooks. Neither replaces your eyes on the chart or your finger on the risk.
"""
)

with candle_expander("What this desk is for — and how to use it well", side="bull", expanded=True, kind="up"):
    st.markdown(
        f"""
**What the Selector actually does**
- Ranks **MES · MNQ · MYM** for **primary CPRP reversion** — who deserves the session.  
- When conditions allow, offers **CPRP Scalping** (1-minute Keltner) as a **preference option**, not a command.  
- Flags **boundary vs mid-structure** so you don’t invent trades in the middle of the range.  
- Checks whether structure width respects your **hard stop** (${HARD_STOP_MIN_USD:.0f}–${HARD_STOP_MAX_USD:.0f}).  
- Applies **60-minute bias** so you don’t casually fade sustained higher-timeframe power.  
- Suggests the working pair: **15m+5m** by default, **30m+15m** when the session is slow or choppy.  
- Alerts when the story changes. Reminds you: **order flow and full checklists live on your platform.**

**Who belongs here**
Traders who run **only** Micro E-minis under written CPRP rules — people who prefer quality over noise and will sit out when the map is unclear.

**How to run a session with it**
1. Open the desk **before** you trade; leave it running.  
2. Read the **protocol options** — reversion, scalping, both, or stand aside.  
3. On **NinjaTrader**, open the suggested pair plus a static **60-minute** bias chart.  
4. Enter only with full confluence (reversion stack or scalping checklist — **one** rulebook per trade).  
5. Route risk through your broker (e.g. Ironbeam). Hard stop is law.  
6. Prefer fewer, cleaner trades. Ego doesn’t get a vote.

**What this will never be**
- A bot that fills tickets for you  
- A replacement for structure you can actually see  
- Live CME firehose data (Yahoo is delayed by design for this tool)  
- A substitute for the **Acknowledgement & Disclosure** — you own your decisions and risk  

Futures can take money. Trade like it. See **Acknowledgement & Disclosure**.
"""
    )

st.info(
    "💡 **New here?** Open the left sidebar → **Help & navigation** for section-by-section "
    "app instructions, and the 📈 / 📉 / 📂 panels for full CPRP operating steps."
)

# ── Strategy operating instructions (Official Quick Reference v1.6) ──────
with candle_expander(
    "How to properly operate the strategy (CPRP Official Quick Reference v1.6)",
    side="bear",
    expanded=False,
    kind="doc",
):
    st.markdown(
        f"""
Official operating instructions for the **{PROTOCOL_NAME}**, distilled from the
**Official Quick Reference v{RULEBOOK_VERSION}** and **Official Rulebook v{RULEBOOK_VERSION}**
(Multi-Timeframe Hierarchy & Order Flow Clarified — authoritative).  
This selector chooses *which micro* to focus on; **you** still operate the Protocol on the charts.

> *Trade the boundaries. Respect the structure. Control the risk.*

---

### Step A — Session setup
1. Open this selector and note the **recommended micro** (or **SIT OUT**).
2. Trade **only** approved micros: **MES** (primary), **MNQ**, **MYM**. No other contracts.
3. Open the suggested **working pair** on **NinjaTrader** (v1.6 hierarchy):

| Pair | When | Roles |
|------|------|-------|
| **15m + 5m (default)** | Normal volume, clean ranges, active session | 15m = structure · 5m = timing + pressure |
| **30m + 15m** | Pre-market, low volume, lunch, wide/choppy | 30m = structure · 15m = timing · 5m fine-tune only |

4. Keep a **static 60-minute** chart in a separate window (4-Hour acceptable).  
   *Overall bias / sentiment only — never generates entries.*
5. Prefer **MES** unless MNQ or MYM is **clearly** superior. Prefer **quality over frequency**.  
   Protocol is **not scalping** — do not force ultra-short holds in slow markets.

**Multi-TF roles (v1.6):** 60m = bias · structure TF = map · timing TF = trigger + order flow.

---

### Step B — Build structure (do not trade until confirmed)
Identify a **confirmed** Support/Resistance **range or channel** (sideways or trending — direction does not change fade logic).

| Requirement | Rule |
|-------------|------|
| Zones | **Sell confirmed resistance · Buy confirmed support** |
| Touches | ≥2 clear touches (or near-touches) at **both** upper and lower boundaries |
| Clarity | Structure unambiguous — if unclear, **stand aside** |
| Developing structure | New session highs/lows: trade **current** swing structure — do not fade “new high” alone |
| Break rule | Decisive close beyond boundary → **pause** (do not hunt lower-TF bounces) |

---

### Step C — Confirmation hierarchy (v1.6 — all required)
1. **Confirmed S/R** on higher TF of working pair  
2. Price **at/near boundary** (Support = long · Resistance = short)  
3. **Price-action rejection** on lower TF  
4. **Volume** supports rejection / absorption  
5. **Order flow** confirms (bids defend for longs · asks aggressive for shorts)  
6. **RSI** favorable (divergence preferred at level; not opposing extreme alone)  
7. Hard stop fits **−${HARD_STOP_MIN_USD:.0f} to −${HARD_STOP_MAX_USD:.0f}**  
8. No recent structure break (or pause / new clear structure done)  
9. **60m bias** not strongly opposing (or you are highly selective)

**Order flow (v1.6):** Bid = buying power · Ask = selling power. Shift at a key level is strong confirmation.

**RSI rules (v1.6)**
- Prefer **divergence at S/R** over absolute 70/30 extremes  
- **Elevated RSI that stays high** often = **strong buying power** — do **not** fade solely because overbought  
- Treat exhaustion only with **structure break + order-flow shift + RSI failure to reclaim**  
- On structure TF: extremes = alerts only · mid-range → wait  
- Optional RSI **7 or 9** on execution chart for divergence only; keep **14** on structure chart

If **any** required item fails → **no trade**.

---

### Step D — Hard risk rule (non-negotiable)
- Maximum loss per trade: **−${HARD_STOP_MIN_USD:.0f} to −${HARD_STOP_MAX_USD:.0f}**
- Exit **immediately** when the hard limit is hit
- **No averaging down** · stay on micros only
- Primary target = opposite boundary · partials OK at mid-range

---

### Step E — Structure break & pause
- After any S/R break: **flatten** and pause **{STRUCTURE_BREAK_PAUSE_MINUTES} minutes**
  **or until a new clear structure forms** on the higher structure chart
- Do **not** chase lower-TF bounces after a break
- Wait for new clear structure before taking setups again

---

### Step F — Operational discipline
- **Fewer, higher-quality trades** — do not force scalping when the market is slow  
- Early pre-market → default **30m+15m**  
- Prefer **MES**; journal every trade; weekly review vs rules  
- **No discretionary overrides** — the Protocol is complete as written  

---

### How the selector fits (do not reverse these roles)
| This app does | You still do on the platform |
|---------------|------------------------------|
| Rank MES / MNQ / MYM for session suitability | Confirm real S/R structure visually |
| Flag boundary vs mid-structure (proxy) | Apply full checklist (incl. **order flow**) before entry |
| Check structure width vs hard dollar stop | Place / manage / exit orders |
| Suggest chart pair (v1.6) + 60m context | Enforce hard stop and structure-break pause |
| Alert when the pick changes | Prefer quality over frequency · not scalping |

Futures trading involves substantial risk of loss. Official documents are personal trading aids, not investment advice.
"""
    )

# ── Run analysis ─────────────────────────────────────────────────────────
with st.spinner("Pulling MES / MNQ / MYM data and scoring structure (incl. 1H context)…"):
    rec = analyze_all(hard_stop_usd=float(hard_stop))
    st.session_state.last_rec = rec
    _hist_pick = rec.recommended or "SIT OUT"
    if getattr(rec, "scalping", None) and rec.scalping.eligible and rec.scalping.micro:
        if rec.recommended:
            _hist_pick = f"{rec.recommended} + SCALP:{rec.scalping.micro}"
        else:
            _hist_pick = f"SCALP:{rec.scalping.micro}"
    st.session_state.history.append(
        {
            "time": rec.as_of,
            "pick": _hist_pick,
            "scores": {s.short: s.score for s in rec.scores},
        }
    )

if desktop_alerts:
    _alert_pick = rec.recommended
    if not _alert_pick and getattr(rec, "scalping", None) and rec.scalping.eligible:
        _alert_pick = f"SCALP:{rec.scalping.micro}"
    st.session_state.tracker.maybe_alert(
        _alert_pick,
        rec.sit_out and not (getattr(rec, "scalping", None) and rec.scalping.eligible),
        rec.alert_message,
    )

# ── Big recommendation banner (primary CPRP + optional Scalping) ─────────
st.markdown("### Current session recommendation")

_primary_on = bool(getattr(rec, "primary_active", False) and rec.recommended)
_scalp = getattr(rec, "scalping", None)
_scalp_on = bool(_scalp and getattr(_scalp, "eligible", False) and _scalp.micro)
_options = list(getattr(rec, "strategy_options", None) or [])

if _primary_on and _scalp_on:
    color = {"MES": "🟢", "MNQ": "🔵", "MYM": "🟣"}.get(rec.recommended, "⚪")
    st.success(
        f"### {color} **Both strategies available** — choose by preference"
    )
    st.info(
        f"**1 · CPRP Reversion (primary protocol)** → focus **{rec.recommended}**  \n"
        f"**2 · CPRP Scalping (secondary)** → focus **{_scalp.micro}** "
        f"(environment **{_scalp.score:.1f}**/100)  \n\n"
        "Both are offered this session. Use **your preference** and the matching rulebook "
        "for that trade — do not mix reversion and scalping checklists on the same entry.  \n\n"
        f"{rec.summary}"
    )
elif _primary_on:
    color = {"MES": "🟢", "MNQ": "🔵", "MYM": "🟣"}.get(rec.recommended, "⚪")
    st.success(
        f"### {color} PRIMARY · CPRP Reversion · **{rec.recommended}**"
    )
    st.info(rec.summary)
elif _scalp_on:
    st.warning(
        f"### ⚡ OPTION · CPRP Scalping · **{_scalp.micro}**  \n"
        f"Primary reversion is quiet — **CPRP Scalping** is available "
        f"(environment **{_scalp.score:.1f}**/100). Use by preference if checklist clears."
    )
    st.info(rec.summary)
else:
    st.error(f"### 🛑 {rec.alert_message}")
    if rec.summary:
        st.caption(rec.summary)

# Strategy options offered this session
desk_section("Strategy options offered", side="bull")
if _primary_on and _scalp_on:
    st.markdown(
        """
**Both protocols cleared this scan.** That’s not an order to trade twice — it’s permission to **choose** with eyes open.

| Protocol | Lean this way when… | Focus |
|----------|---------------------|--------|
| **CPRP Reversion** | You can map clean range/channel S/R on 15+5 or 30+15 | Primary micro pick |
| **CPRP Scalping** | **Sideways** movement on the **1-minute** chart (Keltner / SMA) — no 1H for scalping | Scalping micro pick |

One trade, one rulebook. Preference is yours; standards are not optional.
"""
    )
else:
    st.caption(
        "CPRP Strategies runs more than one playbook. **Reversion** is the main event; "
        "**Scalping** only steps forward when the environment score says the room is quiet enough."
    )
if _options:
    for opt in _options:
        if opt.upper().startswith("PRIMARY"):
            st.success(f"**{opt}**")
        elif "SCALPING" in opt.upper() or opt.upper().startswith("OPTION"):
            st.warning(f"**{opt}**")
        else:
            st.error(f"**{opt}**")
else:
    st.caption("No strategy options computed.")

# Explicit dual picker when both are on (preference only — does not place orders)
if _primary_on and _scalp_on:
    st.markdown("**Your preference this session (journal hint)**")
    _pref = st.radio(
        "Which protocol do you plan to trade?",
        [
            f"CPRP Reversion · {rec.recommended}",
            f"CPRP Scalping · {_scalp.micro}",
            "Either / decide on the chart",
        ],
        horizontal=True,
        key="session_strategy_preference",
        help="Saved in session for journaling. Does not place orders.",
    )
    st.session_state["journal_default_strategy"] = (
        "CPRP Reversion"
        if _pref.startswith("CPRP Reversion")
        else ("CPRP Scalping" if _pref.startswith("CPRP Scalping") else "")
    )
elif _primary_on:
    st.session_state["journal_default_strategy"] = "CPRP Reversion"
elif _scalp_on:
    st.session_state["journal_default_strategy"] = "CPRP Scalping"

if _scalp_on:
    with candle_expander(
        f"CPRP Scalping option details · {_scalp.micro}",
        side="bear",
        expanded=True,
        kind="down",
    ):
        from pathlib import Path as _P

        # Scalping brand logo motion (looping GIF preferred)
        _sv_paths = [
            _P(getattr(_cprp_cfg, "SCALPING_VIDEO_GIF", "")),
            _P(getattr(_cprp_cfg, "SCALPING_VIDEO_GIF_BRAND", "")),
            _P(getattr(_cprp_cfg, "SCALPING_VIDEO_MP4", "")),
            _P(getattr(_cprp_cfg, "SCALPING_VIDEO_MP4_BRAND", "")),
            _P(BRANDING_DIR) / "cprp_scalping_video.gif",
            _P(BRANDING_DIR) / "cprp_scalping_video.mp4",
        ]
        _logo_col, _body_col = st.columns([1, 1.6])
        with _logo_col:
            st.caption("CPRP Scalping logo")
            _logo_ok = False
            for _svp in _sv_paths:
                if _svp and _svp.is_file():
                    render_loop_media(_svp, height=220, caption="Scalping · loop")
                    _logo_ok = True
                    break
            if not _logo_ok:
                st.caption("Scalping logo media not found.")
        with _body_col:
            st.markdown(
                f"""
**Secondary tool only** — *Fade the extremes only when the market is quiet / **sideways**.*

| Item | Setting |
|------|---------|
| Focus micro | **{_scalp.micro}** |
| Status | **{getattr(_scalp, 'status_label', 'Option Conclusive')}** |
| Environment score | **{_scalp.score:.1f}** / 100 |
| **Chart** | **1-minute only** — scalping does **not** use a 1-Hour chart for entries |
| Indicators | Keltner (NT default) · **SMA(14)** midline · RSI 14 (80 / 20) |
| Risk | **$30 – $50** max per scalp · no averaging |
| Target | SMA(14) · Stop = SMA or opposite Keltner band |

**Conclusive when:** chart **movement is sideways** on the **1m**.  
**Stand aside when:** directional tape · chop through SMA · major news · dead volume ·  
or high-quality primary CPRP range/channel is present.
"""
            )
        if _scalp.reasons:
            st.markdown("**Why this option**")
            for r in _scalp.reasons:
                st.markdown(f"- {r}")
        if _scalp.warnings:
            st.markdown("**Watch**")
            for w in _scalp.warnings:
                st.markdown(f"- ⚠️ {w}")

        _sq = _P(_cprp_cfg.SCALPING_QUICK_REFERENCE_PDF)
        _sr = _P(_cprp_cfg.SCALPING_RULEBOOK_PDF)
        d1, d2 = st.columns(2)
        if _sq.is_file():
            d1.download_button(
                "📄 Scalping Quick Reference (PDF)",
                data=_sq.read_bytes(),
                file_name=_cprp_cfg.SCALPING_QUICK_REFERENCE_DOWNLOAD_NAME,
                mime="application/pdf",
                use_container_width=True,
                key="ss_scalp_qr",
            )
        if _sr.is_file():
            d2.download_button(
                "📂 Scalping Official Rulebook (PDF)",
                data=_sr.read_bytes(),
                file_name=_cprp_cfg.SCALPING_RULEBOOK_DOWNLOAD_NAME,
                mime="application/pdf",
                use_container_width=True,
                key="ss_scalp_rb",
            )

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("As of (ET)", rec.as_of)
c2.metric("Session phase", rec.session_phase.replace("_", " ").title())
c3.metric("Chart pair", rec.chart_pair_global.split("(")[0].strip())
c4.metric("Static HTF", rec.static_htf_global.split("(")[0].strip() if rec.static_htf_global else "1-Hour")
c5.metric("Reversion threshold", f"{MIN_SCORE_TO_TRADE:.0f}+")

# Always-available CPRP Scalping desk docs (logo + PDFs)
with candle_expander(
    "CPRP Scalping · strategy documents",
    side="bear",
    expanded=False,
    kind="doc",
):
    from pathlib import Path as _Pdocs

    _lg, _docs = st.columns([1, 1.5])
    with _lg:
        _shown = False
        for _p in (
            _Pdocs(getattr(_cprp_cfg, "SCALPING_VIDEO_GIF", "")),
            _Pdocs(getattr(_cprp_cfg, "SCALPING_VIDEO_GIF_BRAND", "")),
            Path(BRANDING_DIR) / "cprp_scalping_video.gif",
            Path(BRANDING_DIR) / "cprp_scalping_video.mp4",
            _Pdocs(getattr(_cprp_cfg, "SCALPING_VIDEO_MP4", "")),
        ):
            if _p and Path(_p).is_file():
                render_loop_media(Path(_p), height=200, caption="CPRP Scalping logo")
                _shown = True
                break
        if not _shown:
            st.caption("Scalping logo not found — sync branding.")
    with _docs:
        st.markdown(
            f"""
**CPRP Scalping v{_cprp_cfg.SCALPING_VERSION}** — secondary **1-minute Keltner** mean-reversion.  
**Chart: 1-minute only** (not 1H). **Option Conclusive** when movement is **sideways**.  
Risk **$30–$50** · SMA(14) · RSI 80/20 · stand aside on directional tape or when primary CPRP structure is strong.
"""
        )
        _sq = Path(_cprp_cfg.SCALPING_QUICK_REFERENCE_PDF)
        _sr = Path(_cprp_cfg.SCALPING_RULEBOOK_PDF)
        if _sq.is_file():
            st.download_button(
                "📄 Scalping Quick Reference (PDF)",
                data=_sq.read_bytes(),
                file_name=_cprp_cfg.SCALPING_QUICK_REFERENCE_DOWNLOAD_NAME,
                mime="application/pdf",
                use_container_width=True,
                key="ss_scalp_docs_qr",
            )
        if _sr.is_file():
            st.download_button(
                "📂 Scalping Official Rulebook (PDF)",
                data=_sr.read_bytes(),
                file_name=_cprp_cfg.SCALPING_RULEBOOK_DOWNLOAD_NAME,
                mime="application/pdf",
                use_container_width=True,
                key="ss_scalp_docs_rb",
            )

st.markdown("---")

# ── Per-instrument cards — CPRP Reversion ────────────────────────────────
desk_section("Micro comparison cards · CPRP Reversion", side="bull")
st.caption(
    "Primary protocol scorecards. ⭐ = reversion pick. "
    "Expand **Score breakdown** for reasons and warnings."
)

if not rec.scores:
    st.warning("No scores available. Check internet / Yahoo Finance availability.")
else:
    _scalp_micro = (
        rec.scalping.micro
        if getattr(rec, "scalping", None) and rec.scalping.eligible
        else None
    )
    cols = st.columns(len(rec.scores))
    for col, s in zip(cols, sorted(rec.scores, key=lambda x: x.priority)):
        is_pick = rec.recommended == s.short and bool(rec.recommended)
        is_scalp = _scalp_micro == s.short
        with col:
            mark = "⭐ " if is_pick else ("⚡ " if is_scalp else "")
            st.subheader(f"{mark}{s.short}")
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

# ── Per-instrument cards — CPRP Scalping (always shown) ──────────────────
desk_section("Micro comparison cards · CPRP Scalping", side="bear")
_scalp_obj = getattr(rec, "scalping", None)
_scalp_status = (
    getattr(_scalp_obj, "status_label", None)
    or ("Option Conclusive" if _scalp_on else "Option Inconclusive")
)
_scalp_env = float(getattr(_scalp_obj, "score", 0.0) or 0.0)
_scalp_cards = list(getattr(_scalp_obj, "micro_scores", None) or [])

if _scalp_status == "Option Conclusive":
    st.success(
        f"**CPRP Scalping · {_scalp_status}** · best env **{_scalp_env:.1f}**/100 · "
        f"focus **{getattr(_scalp_obj, 'micro', '—') or '—'}** · "
        f"chart **1-minute only** (sideways movement)"
    )
else:
    st.warning(
        f"**CPRP Scalping · {_scalp_status}** · best env **{_scalp_env:.1f}**/100. "
        "Need **sideways** movement on the **1m** chart — not directional tape, "
        "and not when high-quality primary CPRP structure hard-blocks scalps."
    )
if _scalp_obj and getattr(_scalp_obj, "warnings", None):
    for _w in _scalp_obj.warnings[:2]:
        st.caption(f"⚠️ {_w}")

st.caption(
    "Scalping uses the **1-minute chart only** (Keltner · SMA 14 · RSI) — **no 1-Hour chart** for scalping entries. "
    "If movement is **sideways** → **Option Conclusive**. If directional → **Option Inconclusive**. "
    "⚡ = best scalping focus when conclusive."
)

if not _scalp_cards and rec.scores:
    _scalp_cards = []
    for s in sorted(rec.scores, key=lambda x: x.priority):
        _er = float(getattr(s, "path_efficiency", 0.5) or 0.5)
        _sideways = _er <= 0.42
        _avail = bool(_scalp_on and _sideways)
        _scalp_cards.append(
            type("SC", (), {
                "short": s.short,
                "name": s.name,
                "priority": s.priority,
                "score": _scalp_env if _avail else max(0.0, _scalp_env - 10),
                "status": "Option Conclusive" if _avail else "Option Inconclusive",
                "available": _avail,
                "movement": "Sideways" if _sideways else "Directional",
                "path_efficiency": _er,
                "volume_score": s.volume_score,
                "volatility_score": s.volatility_score,
                "structure_score": s.structure_score,
                "chart": "1-minute only",
                "notes": [],
            })()
        )

if _scalp_cards:
    scols = st.columns(len(_scalp_cards))
    for col, sm in zip(scols, sorted(_scalp_cards, key=lambda x: x.priority)):
        is_focus = bool(
            _scalp_on
            and _scalp_obj
            and getattr(_scalp_obj, "micro", None) == sm.short
            and sm.available
        )
        with col:
            mark = "⚡ " if is_focus else ""
            st.subheader(f"{mark}{sm.short}")
            st.caption(sm.name)
            st.metric(
                "Scalp env score",
                f"{sm.score:.1f}",
                help="Sideways 1m movement → Option Conclusive",
            )
            if sm.available:
                st.success(f"**{sm.status}**")
            else:
                st.warning(f"**{sm.status}**")
            st.write(f"**Chart:** {getattr(sm, 'chart', '1-minute only')}")
            st.write(
                f"**Movement:** **{getattr(sm, 'movement', '—')}** "
                f"(efficiency {getattr(sm, 'path_efficiency', 0):.2f})"
            )
            st.write(f"Volume env: **{sm.volume_score:.0f}** · Volatility: **{sm.volatility_score:.0f}**")
            st.write(f"Primary map structure: **{sm.structure_score:.0f}**")
            st.progress(min(float(sm.score) / 100.0, 1.0))
            with candle_expander(
                "Scalping breakdown",
                side="bull" if sm.available else "bear",
            ):
                st.write(f"Status: **{sm.status}**")
                st.write(f"Chart: **1-minute only** (no 1H for scalping entries)")
                st.write(f"Movement: **{getattr(sm, 'movement', '—')}**")
                st.write(f"Environment score: {sm.score:.1f} / 100")
                st.write("Setup: 1m Keltner · SMA(14) · RSI 80/20 · risk $30–$50")
                if sm.notes:
                    st.markdown("**Notes**")
                    for n in sm.notes:
                        st.markdown(f"- {n}")
                if is_focus:
                    st.markdown("**Focus micro** for CPRP Scalping this scan.")
else:
    st.caption("Scalping comparison cards unavailable (no micro scores this run).")

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

# ── Pre-trade checklist (Official Quick Reference v1.6) ──────────────────
st.markdown("---")
desk_section("Pre-trade confirmation checklist (Quick Reference v1.6)", side="bear")
st.caption(
    "All 9 items required — CPRP Quick Reference v1.6. If any fails, stand aside. "
    f"After a structure break, pause at least {STRUCTURE_BREAK_PAUSE_MINUTES} minutes "
    "(or until a new clear structure forms). "
    "Hard risk: max loss −$50 to −$100 · exit immediately at limit · no averaging down. "
    "Order flow is confirmed on your platform (Bid/Ask power)."
)
checks = [
    "1. Confirmed S/R on higher TF of working pair (structure chart)",
    "2. Price at/near boundary — Support = long | Resistance = short (not mid-range)",
    "3. Price-action rejection on lower TF of working pair",
    "4. Volume supports rejection / absorption",
    "5. Order flow confirms (bids defend for longs / asks aggressive for shorts)",
    "6. RSI favorable (divergence preferred at level; elevated RSI ≠ auto-fade)",
    f"7. Hard stop fits inside −${hard_stop} risk limit (−$50 to −$100 max)",
    f"8. No recent structure break (or {STRUCTURE_BREAK_PAUSE_MINUTES}-min pause / new clear structure)",
    "9. 60m bias not strongly opposing the intended trade (or highly selective)",
]
for i, item in enumerate(checks):
    st.checkbox(item, key=f"chk_v16_{i}")

with candle_expander("RSI · order flow · exits (Quick Reference v1.6)", side="bear", expanded=False, kind="doc"):
    st.markdown(
        f"""
**Order flow (v1.6)**
- **Bid = buying power** · **Ask = selling power**  
- Aggressive asks → pressure down · aggressive bids → pressure up  
- Shift at a key level = strong confirmation of hold or break  

**RSI (v1.6)**
- Prefer **divergence at S/R** over absolute 70/30 extremes  
- **Elevated RSI that stays high** often = **strong buying power** — do **not** fade solely because overbought  
- Exhaustion needs **structure break + order-flow shift + RSI failure to reclaim**  
- On structure TF: extremes = alerts only · mid-range → wait for boundary + PA + volume + OF  
- Optional RSI 7/9 on execution chart for divergence only; keep RSI 14 on structure  

**Structure break**
| Action | Rule |
|--------|------|
| Decisive close beyond boundary | **Pause** — do not hunt lower-TF bounces |
| After break | Flatten · wait **{STRUCTURE_BREAK_PAUSE_MINUTES} min** or **new clear structure** |
| Hard risk | **−${HARD_STOP_MIN_USD:.0f} to −${HARD_STOP_MAX_USD:.0f}** · exit at limit · no averaging down |
| Trade count | **Fewer, higher-quality** trades preferred · not scalping (v1.6) |
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
            help=f"Official Rulebook v{RULEBOOK_BASE_VERSION}.",
        )
        st.caption(
            "Open **Trading Journal** in the sidebar for full history, filters, and edit/delete. "
            "On this page the journal sits next to the Quick Reference so you can take notes live."
        )

from disclosure import render_disclosure_footer

render_disclosure_footer()
st.caption(
    f"CPRP Strategies · {PROTOCOL_NAME} Rulebook v{RULEBOOK_VERSION} · "
    "session focus only — no order routing · Yahoo data delayed · "
    f"© 2026 {CREATOR}."
)

# ── Auto-refresh (Session Selector only) ──────────────────────────────────
if auto_refresh:
    time.sleep(refresh_sec)
    st.rerun()
