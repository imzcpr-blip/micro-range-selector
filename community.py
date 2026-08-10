"""
Community board — member posts for trading ideas (text + images).

Logged-in members can publish ideas; images are stored under data/community_uploads/.
"""

from __future__ import annotations

import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import streamlit as st

from auth import DATA_DIR, DB_PATH, current_display_name, current_user_email, is_admin
from wallstreet_ui import candle_expander, desk_section, page_hero

UPLOAD_DIR = DATA_DIR / "community_uploads"
MAX_TITLE = 120
MAX_BODY = 4000
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@dataclass
class CommunityPost:
    id: int
    email: str
    display_name: str
    title: str
    body: str
    image_path: Optional[str]
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
        CREATE TABLE IF NOT EXISTS community_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            display_name TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            body TEXT NOT NULL DEFAULT '',
            image_path TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_community_created "
        "ON community_posts (id DESC)"
    )
    con.commit()
    return con


def create_post(
    email: str,
    display_name: str,
    title: str,
    body: str,
    image_rel_path: Optional[str] = None,
) -> int:
    title = (title or "").strip()
    body = (body or "").strip()
    if not title and not body and not image_rel_path:
        raise ValueError("Add a title, text, or image.")
    if len(title) > MAX_TITLE:
        raise ValueError(f"Title too long (max {MAX_TITLE} characters).")
    if len(body) > MAX_BODY:
        raise ValueError(f"Post text too long (max {MAX_BODY} characters).")

    with _conn() as con:
        cur = con.execute(
            """
            INSERT INTO community_posts
            (email, display_name, title, body, image_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                email.lower().strip(),
                (display_name or "Member").strip(),
                title or "Trading idea",
                body,
                image_rel_path,
                _utc_now(),
            ),
        )
        con.commit()
        return int(cur.lastrowid)


def list_posts(limit: int = 50) -> list[CommunityPost]:
    with _conn() as con:
        rows = con.execute(
            """
            SELECT id, email, display_name, title, body, image_path, created_at
            FROM community_posts
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [CommunityPost(*r) for r in rows]


def delete_post(post_id: int, email: str, *, as_admin: bool = False) -> bool:
    """Authors can delete their own posts; admin can delete any."""
    email = email.lower().strip()
    with _conn() as con:
        row = con.execute(
            "SELECT email, image_path FROM community_posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if not row:
            return False
        owner, image_path = row
        if not as_admin and owner.lower() != email:
            return False
        con.execute("DELETE FROM community_posts WHERE id = ?", (post_id,))
        con.commit()
    if image_path:
        p = DATA_DIR / image_path
        try:
            if p.is_file():
                p.unlink()
        except OSError:
            pass
    return True


def save_uploaded_image(uploaded) -> str:
    """
    Save Streamlit UploadedFile to disk.
    Returns path relative to DATA_DIR (e.g. community_uploads/xyz.jpg).
    """
    if uploaded is None:
        raise ValueError("No image provided.")

    raw = uploaded.getvalue()
    if len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("Image must be 5 MB or smaller.")

    mime = (uploaded.type or "").lower()
    name = (uploaded.name or "image.jpg").lower()
    ext = Path(name).suffix
    if mime not in ALLOWED_IMAGE_TYPES and ext not in ALLOWED_EXT:
        raise ValueError("Use JPG, PNG, WEBP, or GIF images only.")

    if ext not in ALLOWED_EXT:
        # map mime → ext
        ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }.get(mime, ".jpg")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}{ext}"
    dest = UPLOAD_DIR / fname
    dest.write_bytes(raw)
    return f"community_uploads/{fname}"


def _resolve_image(rel: Optional[str]) -> Optional[Path]:
    if not rel:
        return None
    # prevent path traversal
    rel = rel.replace("\\", "/").lstrip("/")
    if ".." in rel or not rel.startswith("community_uploads/"):
        return None
    p = DATA_DIR / rel
    return p if p.is_file() else None


def render_community_panel() -> None:
    """Full Community board UI for members."""
    email = current_user_email()
    if not email:
        st.warning("Sign in to use Community.")
        return

    display = current_display_name() or "Member"
    page_hero(
        "Community",
        "Member idea board · text + charts · respectful ideas only — not financial advice",
        side="bull",
        desk_tag="IDEA DESK · MEMBER BOARD",
    )
    from disclosure import render_disclosure

    render_disclosure(expanded=False)

    st.caption(f"Posting as **{display}**")

    desk_section("Compose", side="bull")
    with candle_expander("New post — publish a trading idea", side="bull", expanded=True, kind="up"):
        with st.form("community_new_post", clear_on_submit=True):
            title = st.text_input(
                "Title",
                max_chars=MAX_TITLE,
                placeholder="e.g. MES support bounce setup — mid-session",
            )
            body = st.text_area(
                "Your idea / notes",
                height=140,
                max_chars=MAX_BODY,
                placeholder="Describe the structure, levels, timeframe pair, risk, and what you're watching…",
            )
            image = st.file_uploader(
                "Upload chart or image (optional)",
                type=["jpg", "jpeg", "png", "webp", "gif"],
                accept_multiple_files=False,
                help="Max 5 MB. JPG / PNG / WEBP / GIF.",
            )
            submitted = st.form_submit_button("Publish post", type="primary", use_container_width=True)

        if submitted:
            try:
                rel = None
                if image is not None:
                    rel = save_uploaded_image(image)
                post_id = create_post(email, display, title, body, rel)
                st.success(f"Published post #{post_id}.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    desk_section("Tape of member posts", side="bear")
    posts = list_posts(limit=60)
    if not posts:
        st.info("No community posts yet — share the first trading idea.")
        return

    for i, p in enumerate(posts):
        header = p.title or "Trading idea"
        side = "bull" if i % 2 == 0 else "bear"
        with candle_expander(
            f"{header} · {p.display_name}",
            side=side,
            expanded=False,
        ):
            st.caption(f"**{p.display_name}** · {p.created_at}")
            if p.body:
                st.write(p.body)
            img_path = _resolve_image(p.image_path)
            if img_path is not None:
                st.image(str(img_path), use_container_width=True)

            can_delete = is_admin(email) or p.email.lower() == email.lower()
            if can_delete:
                if st.button("Delete post", key=f"cdel_{p.id}"):
                    delete_post(p.id, email, as_admin=is_admin(email))
                    st.rerun()


def count_posts() -> int:
    with _conn() as con:
        row = con.execute("SELECT COUNT(*) FROM community_posts").fetchone()
    return int(row[0] or 0) if row else 0


def list_posts_admin(limit: int = 40) -> list[CommunityPost]:
    return list_posts(limit=limit)
