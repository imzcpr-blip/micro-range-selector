"""
Member Chat + live presence for CPRP Session Micro Selector.

Uses shared SQLite (data/users.db) so all sessions on the same server
see the same chat messages and active-user count.
"""

from __future__ import annotations

import re
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import streamlit as st

from auth import DATA_DIR, DB_PATH, current_user_email, get_display_name

# Path is used for optional hero media on the chat page

PRESENCE_TIMEOUT_SEC = 75  # count user active if heartbeat within this window
CHAT_HISTORY_LIMIT = 80
MAX_MESSAGE_LEN = 500

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso() -> str:
    return _utc_now().strftime("%Y-%m-%d %H:%M:%S UTC")


def _conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS presence (
            session_id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            display_name TEXT NOT NULL,
            last_seen TEXT NOT NULL
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            display_name TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    con.commit()
    return con


def ensure_session_id() -> str:
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = uuid.uuid4().hex
    return st.session_state.chat_session_id


def heartbeat(email: str, display_name: str) -> None:
    """Mark this browser session as online."""
    sid = ensure_session_id()
    now = _utc_iso()
    with _conn() as con:
        con.execute(
            """
            INSERT INTO presence (session_id, email, display_name, last_seen)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                email=excluded.email,
                display_name=excluded.display_name,
                last_seen=excluded.last_seen
            """,
            (sid, email, display_name, now),
        )
        # prune stale rows
        cutoff = (_utc_now() - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S UTC")
        con.execute("DELETE FROM presence WHERE last_seen < ?", (cutoff,))
        con.commit()


def active_user_count() -> int:
    cutoff = (_utc_now() - timedelta(seconds=PRESENCE_TIMEOUT_SEC)).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )
    with _conn() as con:
        # unique emails currently online (one person, multiple tabs = 1)
        row = con.execute(
            """
            SELECT COUNT(DISTINCT email) FROM presence
            WHERE last_seen >= ?
            """,
            (cutoff,),
        ).fetchone()
    return int(row[0] or 0) if row else 0


def active_display_names() -> list[str]:
    cutoff = (_utc_now() - timedelta(seconds=PRESENCE_TIMEOUT_SEC)).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )
    with _conn() as con:
        rows = con.execute(
            """
            SELECT display_name FROM (
                SELECT display_name, MAX(last_seen) AS ls
                FROM presence
                WHERE last_seen >= ?
                GROUP BY email
            )
            ORDER BY display_name COLLATE NOCASE
            """,
            (cutoff,),
        ).fetchall()
    return [r[0] for r in rows]


def post_message(email: str, display_name: str, body: str) -> tuple[bool, str]:
    body = (body or "").strip()
    if not body:
        return False, "Message cannot be empty."
    if len(body) > MAX_MESSAGE_LEN:
        return False, f"Message too long (max {MAX_MESSAGE_LEN} characters)."
    # light sanitize: collapse newlines for simple panel
    body = re.sub(r"\s+", " ", body)
    with _conn() as con:
        con.execute(
            """
            INSERT INTO chat_messages (email, display_name, body, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (email, display_name, body, _utc_iso()),
        )
        con.commit()
    return True, "Sent."


def recent_messages(limit: int = CHAT_HISTORY_LIMIT) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            """
            SELECT display_name, body, created_at, email
            FROM chat_messages
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    # oldest first for display
    out = [
        {
            "display_name": r[0],
            "body": r[1],
            "created_at": r[2],
            "email": r[3],
        }
        for r in reversed(rows)
    ]
    return out


def clear_presence_for_session() -> None:
    sid = st.session_state.get("chat_session_id")
    if not sid:
        return
    try:
        with _conn() as con:
            con.execute("DELETE FROM presence WHERE session_id = ?", (sid,))
            con.commit()
    except Exception:
        pass


def render_active_users_badge() -> None:
    """Sidebar / header: green user icon + online count."""
    n = active_user_count()
    names = active_display_names()
    label = "member" if n == 1 else "members"
    st.markdown(
        f"""
<div style="
  display:inline-flex;align-items:center;gap:0.45rem;
  background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.35);
  border-radius:999px;padding:0.25rem 0.75rem;font-size:0.92rem;">
  <span style="
    width:0.55rem;height:0.55rem;border-radius:50%;
    background:#22c55e;box-shadow:0 0 0 3px rgba(34,197,94,0.25);
    display:inline-block;"></span>
  <strong style="color:#86efac;">{n}</strong>
  <span style="opacity:0.9;">online {label}</span>
</div>
""",
        unsafe_allow_html=True,
    )
    if names:
        preview = ", ".join(names[:8])
        more = f" +{len(names) - 8} more" if len(names) > 8 else ""
        st.caption(f"Active: {preview}{more}")


def render_member_chat(
    hero_video: Path | None = None,
    hero_image: Path | None = None,
    logo_video: Path | None = None,
) -> None:
    """Full Member Chat page content."""
    email = current_user_email() or ""
    display = get_display_name(email) or st.session_state.get("display_name") or "Member"
    heartbeat(email, display)

    # Branding header for Member Chat (looping GIF preferred, then MP4, then still)
    shown = False
    for p in (hero_video, logo_video):
        if p is None or not Path(p).is_file():
            continue
        suf = Path(p).suffix.lower()
        if suf == ".gif":
            st.image(str(p), use_container_width=True, caption="CPRP Member Chat")
            shown = True
            break
        if suf == ".mp4":
            st.video(str(p), format="video/mp4", start_time=0, loop=True, muted=True)
            shown = True
            break
    if not shown and hero_image is not None and Path(hero_image).is_file():
        st.image(str(hero_image), use_container_width=True, caption="CPRP Member Chat")
        shown = True

    st.title("Member Chat")
    st.caption(
        "Live chat for signed-in CPRP members. Be respectful — this is a community space, not financial advice."
    )

    top_l, top_r = st.columns([1, 2])
    with top_l:
        render_active_users_badge()
    with top_r:
        st.caption(f"You are chatting as **{display}**")

    st.markdown("---")

    # Auto-refreshing message feed (Streamlit 1.33+)
    try:
        from datetime import timedelta as _td

        @st.fragment(run_every=_td(seconds=5))
        def _live_feed() -> None:
            # keep presence warm while on this page
            em = current_user_email() or ""
            dn = get_display_name(em) or st.session_state.get("display_name") or "Member"
            if em:
                heartbeat(em, dn)
            n = active_user_count()
            st.markdown(f"🟢 **{n}** online")
            msgs = recent_messages()
            if not msgs:
                st.info("No messages yet — say hello to the room.")
            else:
                box = st.container(height=380)
                with box:
                    for m in msgs:
                        when = m["created_at"].replace(" UTC", "")
                        st.markdown(
                            f"**{m['display_name']}**  ·  `{when}`  \n{m['body']}"
                        )

        _live_feed()
    except Exception:
        # Fallback without fragment
        if st.button("Refresh chat", use_container_width=False):
            st.rerun()
        msgs = recent_messages()
        if not msgs:
            st.info("No messages yet — say hello to the room.")
        else:
            for m in msgs:
                when = m["created_at"].replace(" UTC", "")
                st.markdown(f"**{m['display_name']}**  ·  `{when}`  \n{m['body']}")

    st.markdown("---")
    with st.form("member_chat_send", clear_on_submit=True):
        body = st.text_input(
            "Message",
            max_chars=MAX_MESSAGE_LEN,
            placeholder="Share a thought with members…",
            label_visibility="collapsed",
        )
        sent = st.form_submit_button("Send", type="primary", use_container_width=True)
    if sent:
        ok, msg = post_message(email, display, body)
        if ok:
            st.rerun()
        else:
            st.error(msg)
