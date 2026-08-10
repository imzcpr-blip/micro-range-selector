"""
CPRP Session Statistics — Winning vs. Losing Trades image gallery.

Members upload session statistics charts (win/loss, contracts by instrument, etc.).
Images are stored under data/session_stats_uploads/.
"""

from __future__ import annotations

import secrets
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import streamlit as st

from auth import DATA_DIR, DB_PATH, current_display_name, current_user_email, is_admin
from disclosure import render_disclosure
from wallstreet_ui import candle_expander, desk_section, page_hero

UPLOAD_DIR = DATA_DIR / "session_stats_uploads"
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_CAPTION = 200


@dataclass
class SessionStatImage:
    id: int
    email: str
    display_name: str
    session_date: str
    caption: str
    image_path: str
    created_at: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS session_stat_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            display_name TEXT NOT NULL,
            session_date TEXT NOT NULL,
            caption TEXT NOT NULL DEFAULT '',
            image_path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_session_stats_date "
        "ON session_stat_images (session_date DESC, id DESC)"
    )
    con.commit()
    return con


def save_uploaded_image(uploaded) -> str:
    if uploaded is None:
        raise ValueError("Choose an image to upload.")
    raw = uploaded.getvalue()
    if len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("Image must be 8 MB or smaller.")

    mime = (uploaded.type or "").lower()
    name = (uploaded.name or "chart.png").lower()
    ext = Path(name).suffix
    if mime not in ALLOWED_IMAGE_TYPES and ext not in ALLOWED_EXT:
        raise ValueError("Use JPG, PNG, WEBP, or GIF images only.")
    if ext not in ALLOWED_EXT:
        ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }.get(mime, ".png")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}{ext}"
    dest = UPLOAD_DIR / fname
    dest.write_bytes(raw)
    return f"session_stats_uploads/{fname}"


def create_stat_image(
    email: str,
    display_name: str,
    session_date: str,
    caption: str,
    image_rel: str,
) -> int:
    with _conn() as con:
        cur = con.execute(
            """
            INSERT INTO session_stat_images
            (email, display_name, session_date, caption, image_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                email.lower().strip(),
                (display_name or "Member").strip(),
                session_date,
                (caption or "").strip()[:MAX_CAPTION],
                image_rel,
                _utc_now(),
            ),
        )
        con.commit()
        return int(cur.lastrowid)


def list_stat_images(limit: int = 100) -> list[SessionStatImage]:
    with _conn() as con:
        rows = con.execute(
            """
            SELECT id, email, display_name, session_date, caption, image_path, created_at
            FROM session_stat_images
            ORDER BY session_date DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [SessionStatImage(*r) for r in rows]


def delete_stat_image(image_id: int, email: str, *, as_admin: bool = False) -> bool:
    email = email.lower().strip()
    with _conn() as con:
        row = con.execute(
            "SELECT email, image_path FROM session_stat_images WHERE id = ?",
            (image_id,),
        ).fetchone()
        if not row:
            return False
        owner, image_path = row
        if not as_admin and owner.lower() != email:
            return False
        con.execute("DELETE FROM session_stat_images WHERE id = ?", (image_id,))
        con.commit()
    if image_path:
        p = DATA_DIR / image_path.replace("\\", "/").lstrip("/")
        try:
            if p.is_file() and "session_stats_uploads" in str(p):
                p.unlink()
        except OSError:
            pass
    return True


def _resolve_image(rel: str) -> Optional[Path]:
    rel = (rel or "").replace("\\", "/").lstrip("/")
    if ".." in rel or not rel.startswith("session_stats_uploads/"):
        return None
    p = DATA_DIR / rel
    return p if p.is_file() else None


def render_session_wl_panel() -> None:
    """CPRP Session Statistics — upload & view Winning vs. Losing Trades images."""
    email = current_user_email()
    if not email:
        st.warning("Sign in to use CPRP Session Statistics.")
        return

    display = current_display_name() or "Member"

    page_hero(
        "CPRP Session Statistics",
        "Winning vs. Losing Trades gallery · illustrative only — not a performance guarantee",
        side="bull",
        desk_tag="PERFORMANCE DESK · W/L TAPE",
    )
    render_disclosure(expanded=False)

    st.caption(f"Uploading as **{display}**")

    desk_section("Upload", side="bull")
    with candle_expander("Upload session statistics image", side="bull", expanded=True, kind="up"):
        st.markdown(
            "Add a chart or screenshot of your **winning vs. losing trades** "
            "(or contracts-by-instrument) for a session."
        )
        with st.form("session_stats_upload", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                session_d = st.date_input("Session date", value=date.today())
            with c2:
                caption = st.text_input(
                    "Caption (optional)",
                    max_chars=MAX_CAPTION,
                    placeholder="e.g. Winning vs losing trades · Session 08.10.26",
                )
            image = st.file_uploader(
                "Session statistics image",
                type=["jpg", "jpeg", "png", "webp", "gif"],
                accept_multiple_files=False,
                help="Win/loss pie charts, contracts by instrument, etc. Max 8 MB.",
            )
            submitted = st.form_submit_button(
                "Upload statistics image",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            try:
                if image is None:
                    st.error("Please choose an image to upload.")
                else:
                    rel = save_uploaded_image(image)
                    sid = session_d.isoformat() if hasattr(session_d, "isoformat") else str(session_d)
                    img_id = create_stat_image(email, display, sid, caption, rel)
                    st.success(f"Uploaded session statistics image #{img_id}.")
                    st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    desk_section("Gallery", side="bear")
    st.caption("Winning vs. losing trades and related session charts uploaded by members.")

    items = list_stat_images(limit=100)
    if not items:
        st.info(
            "No session statistics images yet. Upload your first "
            "**Winning vs. Losing Trades** chart above."
        )
        return

    # Gallery: 2 columns
    cols = st.columns(2)
    for i, item in enumerate(items):
        with cols[i % 2]:
            path = _resolve_image(item.image_path)
            label = item.caption or "Winning vs. Losing Trades"
            side = "bull" if i % 2 == 0 else "bear"
            with candle_expander(
                f"{item.session_date} · {label}",
                side=side,
                expanded=True,
            ):
                st.caption(f"{item.display_name} · {item.created_at}")
                if path is not None:
                    st.image(str(path), use_container_width=True)
                    st.download_button(
                        "Download",
                        data=path.read_bytes(),
                        file_name=path.name,
                        mime="image/png",
                        key=f"dl_stat_{item.id}",
                        use_container_width=True,
                    )
                else:
                    st.warning("Image file missing.")

                can_delete = is_admin(email) or item.email.lower() == email.lower()
                if can_delete:
                    if st.button("Delete", key=f"del_stat_{item.id}"):
                        delete_stat_image(item.id, email, as_admin=is_admin(email))
                        st.rerun()

    st.markdown("---")
    st.caption(
        "Session statistics images are shared for learning. "
        "Past results do not indicate future performance. Not financial advice."
    )
