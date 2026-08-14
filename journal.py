"""
Per-user Trading Journal for CPRP Session Micro Selector.

Notes are stored in SQLite (data/users.db) keyed by login email so members
can review past sessions. Shown side-by-side with the Quick Reference on
the Session Selector page.

When a user's journal reaches JOURNAL_MAX_ENTRIES, new saves are blocked
until they export (email file / image / spreadsheet CSV) and optionally
free space by clearing entries.
"""

from __future__ import annotations

import csv
import io
import sqlite3
import textwrap
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from analyzer import fetch_bars
from auth import DATA_DIR, DB_PATH, current_display_name, current_user_email
from config import INSTRUMENTS
from wallstreet_ui import (
    candle_expander,
    desk_section,
    page_hero,
    quote_board_footer,
    quote_board_header,
)

MICROS = ["", "MES", "MNQ", "MYM", "SIT OUT", "Multiple", "Other"]
RESULTS = ["", "Open", "Win", "Loss", "Scratch", "No trade", "Lesson only"]
# Strategy used on the session (primary reversion vs secondary scalping)
STRATEGIES = [
    "",
    "CPRP Reversion",
    "CPRP Scalping",
    "Both (separate trades)",
    "Other / mixed",
]

# Soft capacity per user — when full, prompt to export session notes
JOURNAL_MAX_ENTRIES = 50

# Yahoo Finance continuous Micro E-mini futures (same symbols as Session Selector)
#   MES → MES=F   MNQ → MNQ=F   MYM → MYM=F
# Chart: 1-Hour candles · multi-day window + Keltner / RSI / Volume
# Wider bar count so structure / trend is readable (not just one session).
YF_MICRO_ORDER = ("MES", "MNQ", "MYM")
YF_CHART_PERIOD = "60d"  # enough history for KC/RSI warmup + multi-day display
YF_CHART_INTERVAL = "1h"
YF_CHART_BARS = 120  # ~5 sessions of hourly futures bars (display window)
# Indicator defaults (structure-friendly; RSI 14 matches CPRP structure chart)
KC_EMA = 20
KC_ATR = 10
KC_MULT = 2.0
RSI_PERIOD = 14
TV_CHART_HEIGHT = 920  # larger price pane + volume + RSI; full-width board


@dataclass
class JournalEntry:
    id: int
    email: str
    created_at: str
    updated_at: str
    session_date: str
    title: str
    micro: str
    result: str
    notes: str
    lessons: str
    strategy: str = ""


def _conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            session_date TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            micro TEXT NOT NULL DEFAULT '',
            result TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            lessons TEXT NOT NULL DEFAULT '',
            strategy TEXT NOT NULL DEFAULT ''
        )
        """
    )
    # Migrate older DBs that predate the strategy column
    cols = {r[1] for r in con.execute("PRAGMA table_info(journal_entries)").fetchall()}
    if "strategy" not in cols:
        con.execute(
            "ALTER TABLE journal_entries ADD COLUMN strategy TEXT NOT NULL DEFAULT ''"
        )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_journal_email_date "
        "ON journal_entries (email, session_date DESC, id DESC)"
    )
    con.commit()
    return con


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def create_entry(
    email: str,
    *,
    session_date: str,
    title: str,
    micro: str,
    result: str,
    notes: str,
    lessons: str,
    strategy: str = "",
) -> int:
    now = _utc_now()
    with _conn() as con:
        cur = con.execute(
            """
            INSERT INTO journal_entries
            (email, created_at, updated_at, session_date, title, micro, result, notes, lessons, strategy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email.lower().strip(),
                now,
                now,
                session_date,
                (title or "").strip() or f"Session {session_date}",
                (micro or "").strip(),
                (result or "").strip(),
                (notes or "").strip(),
                (lessons or "").strip(),
                (strategy or "").strip(),
            ),
        )
        con.commit()
        return int(cur.lastrowid)


def update_entry(
    entry_id: int,
    email: str,
    *,
    session_date: str,
    title: str,
    micro: str,
    result: str,
    notes: str,
    lessons: str,
    strategy: str = "",
) -> bool:
    now = _utc_now()
    with _conn() as con:
        cur = con.execute(
            """
            UPDATE journal_entries
            SET updated_at = ?, session_date = ?, title = ?, micro = ?,
                result = ?, notes = ?, lessons = ?, strategy = ?
            WHERE id = ? AND email = ?
            """,
            (
                now,
                session_date,
                (title or "").strip() or f"Session {session_date}",
                (micro or "").strip(),
                (result or "").strip(),
                (notes or "").strip(),
                (lessons or "").strip(),
                (strategy or "").strip(),
                entry_id,
                email.lower().strip(),
            ),
        )
        con.commit()
        return cur.rowcount > 0


def delete_entry(entry_id: int, email: str) -> bool:
    with _conn() as con:
        cur = con.execute(
            "DELETE FROM journal_entries WHERE id = ? AND email = ?",
            (entry_id, email.lower().strip()),
        )
        con.commit()
        return cur.rowcount > 0


def get_entry(entry_id: int, email: str) -> Optional[JournalEntry]:
    with _conn() as con:
        row = con.execute(
            """
            SELECT id, email, created_at, updated_at, session_date,
                   title, micro, result, notes, lessons, strategy
            FROM journal_entries
            WHERE id = ? AND email = ?
            """,
            (entry_id, email.lower().strip()),
        ).fetchone()
    if not row:
        return None
    return JournalEntry(*row)


def list_entries(email: str, limit: int = 100) -> list[JournalEntry]:
    with _conn() as con:
        rows = con.execute(
            """
            SELECT id, email, created_at, updated_at, session_date,
                   title, micro, result, notes, lessons, strategy
            FROM journal_entries
            WHERE email = ?
            ORDER BY session_date DESC, id DESC
            LIMIT ?
            """,
            (email.lower().strip(), limit),
        ).fetchall()
    return [JournalEntry(*r) for r in rows]


def count_entries(email: str) -> int:
    with _conn() as con:
        row = con.execute(
            "SELECT COUNT(*) FROM journal_entries WHERE email = ?",
            (email.lower().strip(),),
        ).fetchone()
    return int(row[0] or 0) if row else 0


def journal_max_entries() -> int:
    """Optional override via secrets: [journal] max_entries = 50"""
    try:
        raw = st.secrets.get("journal", {}).get("max_entries", JOURNAL_MAX_ENTRIES)
        n = int(raw)
        return max(5, min(n, 500))
    except Exception:
        return JOURNAL_MAX_ENTRIES


def is_journal_full(email: str) -> bool:
    return count_entries(email) >= journal_max_entries()


def journal_slots_remaining(email: str) -> int:
    return max(0, journal_max_entries() - count_entries(email))


def clear_all_entries(email: str) -> int:
    """Delete all journal entries for a user. Returns number removed."""
    with _conn() as con:
        cur = con.execute(
            "DELETE FROM journal_entries WHERE email = ?",
            (email.lower().strip(),),
        )
        con.commit()
        return int(cur.rowcount or 0)


def clear_oldest_entries(email: str, keep: int | None = None) -> int:
    """
    Delete oldest entries so at most `keep` remain (default half of max).
    Returns number removed.
    """
    email = email.lower().strip()
    keep = journal_max_entries() // 2 if keep is None else max(0, int(keep))
    entries = list_entries(email, limit=10_000)
    if len(entries) <= keep:
        return 0
    # list_entries is newest-first; drop the oldest beyond `keep`
    to_delete = entries[keep:]
    n = 0
    with _conn() as con:
        for e in to_delete:
            cur = con.execute(
                "DELETE FROM journal_entries WHERE id = ? AND email = ?",
                (e.id, email),
            )
            n += int(cur.rowcount or 0)
        con.commit()
    return n


def export_entries_csv(email: str) -> tuple[bytes, str]:
    """Spreadsheet-ready CSV of all session notes for this user."""
    entries = list_entries(email, limit=10_000)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "session_date",
            "title",
            "micro",
            "strategy",
            "result",
            "notes",
            "lessons",
            "created_at",
            "updated_at",
        ]
    )
    for e in entries:
        writer.writerow(
            [
                e.id,
                e.session_date,
                e.title,
                e.micro,
                e.strategy,
                e.result,
                e.notes,
                e.lessons,
                e.created_at,
                e.updated_at,
            ]
        )
    stamp = date.today().isoformat()
    filename = f"CPRP_Trading_Journal_{stamp}.csv"
    # UTF-8 BOM helps Excel open CSV cleanly
    data = ("\ufeff" + buf.getvalue()).encode("utf-8")
    return data, filename


def export_entries_image(email: str, display_name: str = "") -> tuple[bytes, str]:
    """
    Simple PNG summary image of session notes (downloadable).
    Uses Pillow when available; otherwise a minimal PPM→PNG fallback is not used —
    Pillow is required (listed in requirements).
    """
    from PIL import Image, ImageDraw, ImageFont

    entries = list_entries(email, limit=10_000)
    display_name = display_name or email
    max_w = 1100
    line_h = 18
    margin = 28
    # Build text lines
    lines: list[str] = [
        "CPRP Trading Journal — Session Notes Export",
        f"Member: {display_name}  |  Email: {email}",
        f"Exported: {_utc_now()}  |  Entries: {len(entries)}",
        "—",
    ]
    if not entries:
        lines.append("(No journal entries.)")
    for e in entries:
        lines.append(
            f"[{e.session_date}] {e.title}  ·  {e.micro or '—'}  ·  "
            f"{e.strategy or '—'}  ·  {e.result or '—'}"
        )
        if e.notes:
            for part in textwrap.wrap(f"Notes: {e.notes}", width=100):
                lines.append(f"  {part}")
        if e.lessons:
            for part in textwrap.wrap(f"Lessons: {e.lessons}", width=100):
                lines.append(f"  {part}")
        lines.append("")

    # Cap very long exports for image size
    max_lines = 120
    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + [f"… ({len(entries)} entries total — use CSV for full export)"]

    height = margin * 2 + line_h * len(lines) + 20
    height = max(height, 400)
    img = Image.new("RGB", (max_w, height), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
        font_bold = ImageFont.truetype("arialbd.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
        font_bold = font

    y = margin
    for i, line in enumerate(lines):
        f = font_bold if i < 3 else font
        color = (226, 232, 240) if i >= 3 else (148, 163, 184)
        if i == 0:
            color = (96, 165, 250)
        draw.text((margin, y), line, fill=color, font=f)
        y += line_h

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    stamp = date.today().isoformat()
    return out.getvalue(), f"CPRP_Trading_Journal_{stamp}.png"


def _parse_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return date.today()


def render_journal_full_export_prompt(*, key_prefix: str = "jfull") -> None:
    """
    Shown when the user's journal has reached capacity.
    Offers export to email, image download, or spreadsheet CSV.
    """
    email = current_user_email()
    if not email:
        return

    n = count_entries(email)
    max_n = journal_max_entries()
    display = current_display_name() or email

    st.warning(
        f"**Your Trading Journal is full** ({n} / {max_n} session notes).  \n"
        "New notes can’t be saved until you free space.  \n\n"
        "**Would you like to export your session notes first?**  \n"
        "Choose any option below — then you can clear space and keep journaling."
    )

    st.markdown(
        """
**Export options**
1. **Email** — send a downloadable file to your login email  
2. **Image** — download a simple PNG summary of your notes  
3. **Spreadsheet** — download a CSV you can open in Excel / Google Sheets  
"""
    )

    tab_email, tab_image, tab_sheet = st.tabs(
        ["📧 Email file", "🖼️ Image download", "📊 Spreadsheet (CSV)"]
    )

    # Shared export payloads
    csv_bytes, csv_name = export_entries_csv(email)
    try:
        img_bytes, img_name = export_entries_image(email, display)
        img_ok = True
        img_err = ""
    except Exception as exc:  # noqa: BLE001
        img_bytes, img_name = b"", ""
        img_ok = False
        img_err = str(exc)

    with tab_email:
        st.caption(
            f"We’ll email **{email}** a file attachment with your full journal. "
            "Requires app email (SMTP) to be configured by the site owner."
        )
        fmt = st.radio(
            "Attachment format",
            ["Spreadsheet (CSV)", "Image (PNG)"],
            horizontal=True,
            key=f"{key_prefix}_email_fmt",
        )
        if st.button("Email my session notes", type="primary", key=f"{key_prefix}_email_btn"):
            try:
                from emailer import send_file_to_user

                if fmt.startswith("Spreadsheet"):
                    fb, fn, main, sub = csv_bytes, csv_name, "text", "csv"
                else:
                    if not img_ok:
                        st.error(f"Could not build image export: {img_err}")
                        return
                    fb, fn, main, sub = img_bytes, img_name, "image", "png"

                send_file_to_user(
                    email,
                    subject=f"[CPRP] Your Trading Journal export ({n} entries)",
                    body=(
                        f"Hi {display},\n\n"
                        f"Attached is your CPRP Trading Journal export ({n} session notes).\n"
                        f"File: {fn}\n\n"
                        "You can download this file and keep it for your records.\n"
                        "After saving it, return to the app to free journal space if you wish.\n\n"
                        "— CPRP Session Micro Selector\n"
                    ),
                    filename=fn,
                    file_bytes=fb,
                    mime_main=main,
                    mime_sub=sub,
                )
                st.success(f"Sent **{fn}** to **{email}**. Check your inbox (and spam folder).")
            except Exception as exc:  # noqa: BLE001
                st.error(
                    f"Could not send email: {exc}  \n"
                    "You can still use **Image download** or **Spreadsheet (CSV)** below."
                )

    with tab_image:
        st.caption("Download a simple image summary of your session notes.")
        if img_ok:
            st.image(img_bytes, caption=img_name, use_container_width=True)
            st.download_button(
                "Download journal image (PNG)",
                data=img_bytes,
                file_name=img_name,
                mime="image/png",
                type="primary",
                use_container_width=True,
                key=f"{key_prefix}_img_dl",
            )
        else:
            st.error(f"Image export unavailable: {img_err}")

    with tab_sheet:
        st.caption(
            "CSV opens in Excel, Google Sheets, or Numbers — one row per session note."
        )
        st.download_button(
            "Download spreadsheet file (CSV)",
            data=csv_bytes,
            file_name=csv_name,
            mime="text/csv",
            type="primary",
            use_container_width=True,
            key=f"{key_prefix}_csv_dl",
        )
        st.code(
            "Columns: id, session_date, title, micro, strategy, result, notes, lessons, created_at, updated_at",
            language=None,
        )

    st.markdown("---")
    st.markdown("**Free space after exporting**")
    st.caption("Only do this after you’ve saved your export.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "Clear oldest half of entries",
            key=f"{key_prefix}_clear_half",
            use_container_width=True,
        ):
            removed = clear_oldest_entries(email)
            st.success(f"Removed {removed} oldest entries. You can save new notes again.")
            st.rerun()
    with c2:
        if st.button(
            "Clear ALL journal entries",
            key=f"{key_prefix}_clear_all",
            use_container_width=True,
        ):
            removed = clear_all_entries(email)
            st.warning(f"Deleted all {removed} journal entries for your account.")
            st.rerun()


def render_journal_composer(
    *,
    key_prefix: str = "jr",
    default_micro: str = "",
    compact: bool = False,
) -> None:
    """
    New-note form for the journal. When compact=True, suited for side-by-side layout.
    """
    email = current_user_email()
    if not email:
        st.warning("Sign in to use the Trading Journal.")
        return

    display = current_display_name() or email
    n = count_entries(email)
    max_n = journal_max_entries()
    remaining = journal_slots_remaining(email)

    st.markdown(f"**Trading Journal** · {display}")
    st.caption(f"Storage: **{n} / {max_n}** session notes" + (f" · {remaining} free" if remaining else ""))
    if not compact:
        st.caption(
            "Your private blotter — structure, execution, and the lessons you refuse to forget. "
            "Saved to your account for review, not for performance theater."
        )

    if is_journal_full(email):
        render_journal_full_export_prompt(key_prefix=f"{key_prefix}_full")
        return

    # Soft notice when nearing capacity
    if remaining <= 5:
        st.info(
            f"Your journal is almost full ({n}/{max_n}). "
            "When it reaches the limit you’ll be asked to export your notes."
        )

    with st.form(f"{key_prefix}_new_entry", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            session_d = st.date_input(
                "Session date",
                value=date.today(),
                key=f"{key_prefix}_date",
            )
            title = st.text_input(
                "Title",
                placeholder="e.g. MES open range fade",
                key=f"{key_prefix}_title",
            )
        with c2:
            micro_default = default_micro if default_micro in MICROS else ""
            micro = st.selectbox(
                "Micro / focus",
                MICROS,
                index=MICROS.index(micro_default) if micro_default in MICROS else 0,
                key=f"{key_prefix}_micro",
            )
            # Strategy used — from session preference (Selector) when available
            _pref_strat = ""
            try:
                _pref_strat = str(st.session_state.get("journal_default_strategy") or "")
            except Exception:
                _pref_strat = ""
            strat_default = _pref_strat if _pref_strat in STRATEGIES else ""
            strategy = st.selectbox(
                "Strategy used",
                STRATEGIES,
                index=STRATEGIES.index(strat_default) if strat_default in STRATEGIES else 0,
                key=f"{key_prefix}_strategy",
                help=(
                    "CPRP Reversion = primary range/channel protocol (v1.6). "
                    "CPRP Scalping = secondary 5m Keltner protocol (1m if tight & confirmed feasible)."
                ),
            )
            result = st.selectbox("Result", RESULTS, key=f"{key_prefix}_result")

        notes = st.text_area(
            "Session notes",
            height=160 if compact else 200,
            placeholder=(
                "Structure, entry confirmations, what you saw on 15m/5m, "
                "risk, emotions, execution…"
            ),
            key=f"{key_prefix}_notes",
        )
        lessons = st.text_area(
            "Lessons / takeaways",
            height=90 if compact else 120,
            placeholder="What will you repeat or change next session?",
            key=f"{key_prefix}_lessons",
        )
        saved = st.form_submit_button(
            "Save journal entry",
            type="primary",
            use_container_width=True,
        )

    if saved:
        if is_journal_full(email):
            st.error("Journal is full. Export your notes, then free space to continue.")
            return
        if not (notes or "").strip() and not (lessons or "").strip() and not (title or "").strip():
            st.error("Add a title, notes, or lessons before saving.")
            return
        entry_id = create_entry(
            email,
            session_date=_parse_date(session_d).isoformat(),
            title=title,
            micro=micro,
            result=result,
            notes=notes,
            lessons=lessons,
            strategy=strategy,
        )
        st.success(f"Saved journal entry #{entry_id}.")
        st.session_state[f"{key_prefix}_last_saved"] = entry_id
        if is_journal_full(email):
            st.warning("Your journal is now full. Export your session notes when ready.")
            st.rerun()


def render_journal_history(*, key_prefix: str = "jhist", show_edit: bool = True) -> None:
    """List past entries for the logged-in user; optional expand/edit/delete."""
    email = current_user_email()
    if not email:
        return

    entries = list_entries(email)
    total = len(entries)
    max_n = journal_max_entries()
    st.markdown(f"**Past sessions** ({total} / {max_n})")

    if is_journal_full(email):
        with candle_expander("Journal full — export options", side="bear", expanded=True, kind="folder"):
            render_journal_full_export_prompt(key_prefix=f"{key_prefix}_histfull")

    if not entries:
        st.info("No journal entries yet. Save your first session notes above.")
        return

    # Filter
    f1, f2 = st.columns(2)
    with f1:
        filter_micro = st.selectbox(
            "Filter micro",
            ["All"] + [m for m in MICROS if m],
            key=f"{key_prefix}_fmicro",
        )
    with f2:
        filter_result = st.selectbox(
            "Filter result",
            ["All"] + [r for r in RESULTS if r],
            key=f"{key_prefix}_fresult",
        )

    filtered = entries
    if filter_micro != "All":
        filtered = [e for e in filtered if e.micro == filter_micro]
    if filter_result != "All":
        filtered = [e for e in filtered if e.result == filter_result]

    if not filtered:
        st.caption("No entries match this filter.")
        return

    for i, e in enumerate(filtered):
        header = f"{e.session_date} · {e.title}"
        meta_bits = [b for b in (e.micro, e.strategy, e.result) if b]
        if meta_bits:
            header += " · " + " · ".join(meta_bits)
        side = "bull" if (e.result or "").lower() in {"win", "scratch", ""} and i % 2 == 0 else "bear"
        if (e.result or "").lower() == "win":
            side = "bull"
        elif (e.result or "").lower() == "loss":
            side = "bear"
        with candle_expander(header, side=side, expanded=False):
            st.caption(f"Created {e.created_at} · Updated {e.updated_at} · ID #{e.id}")
            if e.strategy:
                st.caption(f"Strategy used: **{e.strategy}**")
            if e.notes:
                st.markdown("**Notes**")
                st.write(e.notes)
            if e.lessons:
                st.markdown("**Lessons**")
                st.write(e.lessons)

            if show_edit:
                edit_key = f"{key_prefix}_edit_{e.id}"
                if st.checkbox("Edit this entry", key=f"{edit_key}_toggle"):
                    with st.form(f"{edit_key}_form"):
                        ed_date = st.date_input(
                            "Session date",
                            value=_parse_date(e.session_date),
                            key=f"{edit_key}_date",
                        )
                        ed_title = st.text_input("Title", value=e.title, key=f"{edit_key}_title")
                        ed_micro = st.selectbox(
                            "Micro",
                            MICROS,
                            index=MICROS.index(e.micro) if e.micro in MICROS else 0,
                            key=f"{edit_key}_micro",
                        )
                        ed_strategy = st.selectbox(
                            "Strategy used",
                            STRATEGIES,
                            index=(
                                STRATEGIES.index(e.strategy)
                                if e.strategy in STRATEGIES
                                else 0
                            ),
                            key=f"{edit_key}_strategy",
                        )
                        ed_result = st.selectbox(
                            "Result",
                            RESULTS,
                            index=RESULTS.index(e.result) if e.result in RESULTS else 0,
                            key=f"{edit_key}_result",
                        )
                        ed_notes = st.text_area("Notes", value=e.notes, height=140, key=f"{edit_key}_notes")
                        ed_lessons = st.text_area(
                            "Lessons", value=e.lessons, height=100, key=f"{edit_key}_lessons"
                        )
                        c_save, c_del = st.columns(2)
                        with c_save:
                            do_save = st.form_submit_button("Update entry", type="primary")
                        with c_del:
                            do_del = st.form_submit_button("Delete entry")

                    if do_save:
                        update_entry(
                            e.id,
                            email,
                            session_date=_parse_date(ed_date).isoformat(),
                            title=ed_title,
                            micro=ed_micro,
                            result=ed_result,
                            notes=ed_notes,
                            lessons=ed_lessons,
                            strategy=ed_strategy,
                        )
                        st.success("Entry updated.")
                        st.rerun()
                    if do_del:
                        delete_entry(e.id, email)
                        st.warning("Entry deleted.")
                        st.rerun()


def render_quick_reference_panel() -> None:
    """Show primary CPRP + CPRP Scalping Quick Reference cards side by side."""
    from config import (
        QUICK_REFERENCE_DOWNLOAD_NAME,
        QUICK_REFERENCE_IMAGE,
        QUICK_REFERENCE_PDF,
        RULEBOOK_UPDATE_DOWNLOAD_NAME,
        RULEBOOK_UPDATE_PDF,
        RULEBOOK_VERSION,
        SCALPING_QUICK_REFERENCE_IMAGE,
        SCALPING_QUICK_REFERENCE_PDF,
        SCALPING_QUICK_REFERENCE_DOWNLOAD_NAME,
        SCALPING_RULEBOOK_PDF,
        SCALPING_RULEBOOK_DOWNLOAD_NAME,
        SCALPING_VERSION,
    )

    st.markdown("**Quick Reference guides**")
    st.caption(
        "Keep both cards open while you write — **Reversion** for the main map, "
        "**Scalping** when the tape goes quiet. Same standards; different playbooks."
    )

    col_main, col_scalp = st.columns(2)

    with col_main:
        st.markdown(f"**CPRP Reversion · v{RULEBOOK_VERSION}**")
        st.caption("Primary range / channel protocol")
        qr = Path(QUICK_REFERENCE_IMAGE)
        if qr.is_file():
            st.image(
                str(qr),
                caption=f"CPRP Quick Reference v{RULEBOOK_VERSION}",
                use_container_width=True,
            )
            st.download_button(
                "📄 Reversion QR (JPG)",
                data=qr.read_bytes(),
                file_name=QUICK_REFERENCE_DOWNLOAD_NAME,
                mime="image/jpeg",
                use_container_width=True,
                key="jr_side_qr_jpg",
            )
        else:
            st.warning("Main Quick Reference image not found.")
        pdf = Path(QUICK_REFERENCE_PDF)
        if pdf.is_file():
            st.download_button(
                "📃 Reversion QR (PDF)",
                data=pdf.read_bytes(),
                file_name=f"CPRP_Quick_Reference_v{RULEBOOK_VERSION}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="jr_side_qr_pdf",
            )
        rb = Path(RULEBOOK_UPDATE_PDF)
        if rb.is_file():
            st.download_button(
                "📂 Reversion Rulebook (PDF)",
                data=rb.read_bytes(),
                file_name=RULEBOOK_UPDATE_DOWNLOAD_NAME,
                mime="application/pdf",
                use_container_width=True,
                key="jr_side_rb_pdf",
            )

    with col_scalp:
        st.markdown(f"**CPRP Scalping · v{SCALPING_VERSION}**")
        st.caption("Secondary 5m Keltner (1m if tight & confirmed feasible)")
        sq = Path(SCALPING_QUICK_REFERENCE_IMAGE)
        if sq.is_file():
            st.image(
                str(sq),
                caption=f"CPRP Scalping Quick Reference v{SCALPING_VERSION}",
                use_container_width=True,
            )
            st.download_button(
                "📄 Scalping QR (JPG)",
                data=sq.read_bytes(),
                file_name=f"CPRP_Scalping_Quick_Reference_v{SCALPING_VERSION}.jpg",
                mime="image/jpeg",
                use_container_width=True,
                key="jr_side_scalp_qr_jpg",
            )
        else:
            # PDF-only fallback message
            st.caption("Scalping QR image not found — use PDF download.")
        spdf = Path(SCALPING_QUICK_REFERENCE_PDF)
        if spdf.is_file():
            st.download_button(
                "📃 Scalping QR (PDF)",
                data=spdf.read_bytes(),
                file_name=SCALPING_QUICK_REFERENCE_DOWNLOAD_NAME,
                mime="application/pdf",
                use_container_width=True,
                key="jr_side_scalp_qr_pdf",
            )
        srb = Path(SCALPING_RULEBOOK_PDF)
        if srb.is_file():
            st.download_button(
                "📂 Scalping Rulebook (PDF)",
                data=srb.read_bytes(),
                file_name=SCALPING_RULEBOOK_DOWNLOAD_NAME,
                mime="application/pdf",
                use_container_width=True,
                key="jr_side_scalp_rb_pdf",
            )
        if not spdf.is_file() and not srb.is_file():
            st.warning("Scalping documents missing — run document sync.")


def _true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _rsi(close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """Wilder-style RSI (matches structure-chart RSI 14 used in CPRP)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def _keltner_channels(
    df: pd.DataFrame,
    *,
    ema_len: int = KC_EMA,
    atr_len: int = KC_ATR,
    mult: float = KC_MULT,
) -> pd.DataFrame:
    """
    Classic Keltner Channels:
      mid  = EMA(close, ema_len)
      upper = mid + mult * ATR(atr_len)
      lower = mid - mult * ATR(atr_len)
    """
    out = df.copy()
    out["KC_Mid"] = out["Close"].ewm(span=ema_len, adjust=False).mean()
    atr = _true_range(out).ewm(alpha=1.0 / atr_len, min_periods=atr_len, adjust=False).mean()
    out["KC_Upper"] = out["KC_Mid"] + mult * atr
    out["KC_Lower"] = out["KC_Mid"] - mult * atr
    out["ATR"] = atr
    out["RSI"] = _rsi(out["Close"], RSI_PERIOD)
    return out


@st.cache_data(ttl=60, show_spinner=False)
def _yahoo_1h_1d_bars(yahoo_symbol: str) -> pd.DataFrame:
    """
    Yahoo Finance 1-Hour bars with Keltner / RSI warmed up on longer history,
    then clipped to a multi-day display window (~YF_CHART_BARS hours) so trend
    and structure are visible — not just a single session.
    Cached ~60s so tab switches stay snappy without hammering Yahoo.
    """
    raw = fetch_bars(
        yahoo_symbol,
        period=YF_CHART_PERIOD,
        interval=YF_CHART_INTERVAL,
    )
    enriched = _keltner_channels(raw)
    return enriched.tail(YF_CHART_BARS)


def _yahoo_candlestick_figure(
    bars: pd.DataFrame,
    *,
    short: str,
    yahoo_symbol: str,
    name: str,
    height: int = TV_CHART_HEIGHT,
) -> go.Figure:
    """
    Dark desk-style multi-panel chart:
      row 1 — Candles + Keltner Channels
      row 2 — Volume
      row 3 — RSI (14) with 30/70 guides
    """
    last = float(bars["Close"].iloc[-1])
    prev = float(bars["Close"].iloc[-2]) if len(bars) > 1 else last
    chg = last - prev
    chg_pct = (chg / prev * 100.0) if prev else 0.0
    chg_color = "#7dcea0" if chg >= 0 else "#e07a7a"
    sign = "+" if chg >= 0 else ""
    rsi_last = float(bars["RSI"].iloc[-1]) if "RSI" in bars.columns else 50.0
    rsi_color = (
        "#e07a7a" if rsi_last >= 70 else "#7dcea0" if rsi_last <= 30 else "#E8D5A3"
    )

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.035,
        row_heights=[0.62, 0.16, 0.22],  # prioritize price candles for trend read
        subplot_titles=(
            f"{short}  ·  Keltner ({KC_EMA}/{KC_ATR}×{KC_MULT:g})  ·  1H · {len(bars)} bars",
            "Volume",
            f"RSI ({RSI_PERIOD})",
        ),
    )

    # ── Price + Keltner ──────────────────────────────────────────────────
    fig.add_trace(
        go.Candlestick(
            x=bars.index,
            open=bars["Open"],
            high=bars["High"],
            low=bars["Low"],
            close=bars["Close"],
            name=short,
            increasing_line_color="#C9A84C",
            increasing_fillcolor="#C9A84C",
            decreasing_line_color="#8B9BB4",
            decreasing_fillcolor="#5a6a80",
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    # Keltner band fill (upper then lower with fill)
    fig.add_trace(
        go.Scatter(
            x=bars.index,
            y=bars["KC_Upper"],
            mode="lines",
            name="KC Upper",
            line=dict(color="rgba(201,168,76,0.55)", width=1.2, dash="dot"),
            hovertemplate="KC Upper %{y:.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=bars.index,
            y=bars["KC_Lower"],
            mode="lines",
            name="KC Lower",
            line=dict(color="rgba(201,168,76,0.55)", width=1.2, dash="dot"),
            fill="tonexty",
            fillcolor="rgba(201,168,76,0.08)",
            hovertemplate="KC Lower %{y:.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=bars.index,
            y=bars["KC_Mid"],
            mode="lines",
            name="KC Mid (EMA)",
            line=dict(color="#E8D5A3", width=1.4),
            hovertemplate="KC Mid %{y:.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # 1D high / low guides on price pane
    hi = float(bars["High"].max())
    lo = float(bars["Low"].min())
    fig.add_hline(
        y=hi,
        line_color="rgba(139,155,180,0.45)",
        line_dash="dot",
        line_width=1,
        row=1,
        col=1,
    )
    fig.add_hline(
        y=lo,
        line_color="rgba(201,168,76,0.45)",
        line_dash="dot",
        line_width=1,
        row=1,
        col=1,
    )

    # ── Volume ───────────────────────────────────────────────────────────
    vol_colors = [
        "#C9A84C" if c >= o else "#8B9BB4"
        for o, c in zip(bars["Open"], bars["Close"])
    ]
    fig.add_trace(
        go.Bar(
            x=bars.index,
            y=bars["Volume"],
            name="Volume",
            marker_color=vol_colors,
            marker_line_width=0,
            opacity=0.85,
            showlegend=False,
            hovertemplate="Vol %{y:,.0f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # ── RSI ──────────────────────────────────────────────────────────────
    fig.add_trace(
        go.Scatter(
            x=bars.index,
            y=bars["RSI"],
            mode="lines",
            name="RSI",
            line=dict(color="#D4AF37", width=1.6),
            showlegend=False,
            hovertemplate="RSI %{y:.1f}<extra></extra>",
        ),
        row=3,
        col=1,
    )
    # 30 / 50 / 70 reference levels
    for level, color, dash in (
        (70, "rgba(224,122,122,0.65)", "dash"),
        (50, "rgba(138,132,120,0.45)", "dot"),
        (30, "rgba(125,206,160,0.65)", "dash"),
    ):
        fig.add_hline(
            y=level,
            line_color=color,
            line_dash=dash,
            line_width=1,
            row=3,
            col=1,
        )
    # Soft overbought / oversold bands
    fig.add_hrect(
        y0=70,
        y1=100,
        fillcolor="rgba(224,122,122,0.08)",
        line_width=0,
        row=3,
        col=1,
    )
    fig.add_hrect(
        y0=0,
        y1=30,
        fillcolor="rgba(125,206,160,0.08)",
        line_width=0,
        row=3,
        col=1,
    )

    axis_common = dict(
        gridcolor="rgba(201,168,76,0.08)",
        linecolor="rgba(201,168,76,0.28)",
        showgrid=True,
        zeroline=False,
    )
    fig.update_layout(
        title=dict(
            text=(
                f"<b>{short}</b>  {yahoo_symbol}  ·  {name}<br>"
                f"<span style='font-size:13px;color:{chg_color}'>"
                f"{last:,.2f}  {sign}{chg:,.2f} ({sign}{chg_pct:.2f}%)</span>"
                f"<span style='font-size:12px;color:{rsi_color}'>"
                f"  ·  RSI {rsi_last:.1f}</span>"
                f"<span style='font-size:11px;color:#8a8478'>"
                f"  ·  KC {KC_EMA}/{KC_ATR}×{KC_MULT:g}  ·  1H · {len(bars)} bars · Yahoo</span>"
            ),
            x=0.01,
            xanchor="left",
            font=dict(size=13, color="#E8D5A3", family="IBM Plex Mono, monospace"),
        ),
        height=height,
        # Tight side margins so the candle pane uses full board width
        margin=dict(t=68, b=28, l=36, r=56),
        paper_bgcolor="rgba(6,10,14,1)",
        plot_bgcolor="rgba(8,12,16,0.96)",
        font=dict(color="#e8e4d8", family="IBM Plex Mono, monospace", size=10),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10, color="#a8a090"),
            bgcolor="rgba(0,0,0,0)",
        ),
        dragmode="pan",
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
    )
    # Shared x / pane y styling
    fig.update_xaxes(**axis_common, rangeslider_visible=False)
    fig.update_yaxes(**axis_common, side="right", tickformat=",.2f", row=1, col=1)
    fig.update_yaxes(**axis_common, side="right", row=2, col=1)
    fig.update_yaxes(
        **axis_common,
        side="right",
        range=[0, 100],
        tickvals=[0, 30, 50, 70, 100],
        row=3,
        col=1,
    )
    # Subplot title styling
    for ann in fig.layout.annotations:
        ann.font = dict(size=10, color="#C9A84C", family="IBM Plex Mono, monospace")
        ann.xanchor = "left"
        ann.x = 0.0

    return fig


def render_live_micro_charts(
    *,
    key_prefix: str = "tvjr",
    height: int = TV_CHART_HEIGHT,
    default_micro: str = "MES",
) -> None:
    """
    Full-width LIVE Yahoo Finance charts: MES / MNQ / MYM
    1-Hour candles over a multi-day window with Keltner Channels, Volume, and RSI.
    """
    desk_section("Quote Board · 1 Hour · multi-day trend", side="bull")
    st.caption(
        "Yahoo Finance continuous micros: **MES=F** · **MNQ=F** · **MYM=F**  ·  "
        f"**1H** · **~{YF_CHART_BARS} bars** (multi-day)  ·  "
        f"Keltner ({KC_EMA}/{KC_ATR}×{KC_MULT:g}) · "
        f"Volume · RSI ({RSI_PERIOD}). Wider board for structure and trend."
    )

    pick = (default_micro or "MES").strip().upper()
    pick = pick.replace("1!", "").replace("!", "").replace("=F", "").strip()
    if pick not in INSTRUMENTS:
        pick = "MES"

    ordered = [pick] + [s for s in YF_MICRO_ORDER if s != pick]

    quote_board_header(
        f"Floor Quote Board · MES=F · MNQ=F · MYM=F · KC · Vol · RSI · {YF_CHART_BARS}×1H",
        live_label="YAHOO · 1H · TREND",
    )
    tabs = st.tabs([f"● {s} ({INSTRUMENTS[s].symbol})" for s in ordered])

    for tab, short in zip(tabs, ordered):
        with tab:
            inst = INSTRUMENTS[short]
            yahoo_sym = inst.symbol
            st.markdown(
                f"<div style='font-size:11px;color:#C9A84C;margin:0 0 6px 0;"
                f"font-family:IBM Plex Mono,monospace;letter-spacing:0.06em;'>"
                f"<strong>{short}</strong> · {yahoo_sym} · {inst.name} · "
                f"Keltner + Volume + RSI · Yahoo continuous"
                f"</div>",
                unsafe_allow_html=True,
            )
            try:
                with st.spinner(f"Loading {yahoo_sym} 1H bars + indicators…"):
                    bars = _yahoo_1h_1d_bars(yahoo_sym)
                fig = _yahoo_candlestick_figure(
                    bars,
                    short=short,
                    yahoo_symbol=yahoo_sym,
                    name=inst.name,
                    height=height,
                )
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config={
                        "displayModeBar": True,
                        "displaylogo": False,
                        "modeBarButtonsToRemove": [
                            "lasso2d",
                            "select2d",
                            "autoScale2d",
                        ],
                        "scrollZoom": True,
                    },
                    key=f"{key_prefix}_chart_{short}",
                )
                t0 = bars.index[0].strftime("%b %d %H:%M")
                t1 = bars.index[-1].strftime("%b %d %H:%M %Z")
                rsi_now = float(bars["RSI"].iloc[-1])
                vol_last = float(bars["Volume"].iloc[-1])
                st.caption(
                    f"{len(bars)} × 1H bars · {t0} → {t1} · "
                    f"High {float(bars['High'].max()):,.2f} · "
                    f"Low {float(bars['Low'].min()):,.2f} · "
                    f"RSI {rsi_now:.1f} · Last vol {vol_last:,.0f} · "
                    f"KC EMA{KC_EMA} / ATR{KC_ATR}×{KC_MULT:g}"
                )
            except Exception as exc:  # noqa: BLE001
                st.warning(
                    f"Yahoo chart unavailable for **{yahoo_sym}** ({short}): {exc}  \n"
                    "Try again in a moment, or confirm market data on your platform."
                )
    quote_board_footer(
        f"MES=F · MNQ=F · MYM=F · {YF_CHART_BARS}×1H · Keltner + Volume + RSI · Yahoo Finance · Desk display only"
    )


def render_reference_and_journal_side_by_side(default_micro: str = "") -> None:
    """Main dual-pane: Quick Reference | Trading Journal composer + recent list."""
    st.markdown("---")
    desk_section("Quick Reference + Trading Journal", side="bull")
    st.caption(
        "Write session notes while viewing the official card — no need to leave this page."
    )

    left, right = st.columns([1, 1], gap="large")
    with left:
        render_quick_reference_panel()
    with right:
        render_journal_composer(
            key_prefix="side",
            default_micro=default_micro,
            compact=True,
        )
        st.markdown("---")
        # Compact history peek
        email = current_user_email()
        if email:
            recent = list_entries(email, limit=5)
            st.markdown(f"**Recent entries** ({count_entries(email)} total)")
            if not recent:
                st.caption("No saved sessions yet.")
            else:
                for i, e in enumerate(recent):
                    bits = " · ".join(
                        x for x in (e.session_date, e.micro, e.strategy, e.result, e.title) if x
                    )
                    side = "bull" if i % 2 == 0 else "bear"
                    if (e.result or "").lower() == "win":
                        side = "bull"
                    elif (e.result or "").lower() == "loss":
                        side = "bear"
                    with candle_expander(bits or f"Entry #{e.id}", side=side, expanded=False):
                        if e.notes:
                            st.write(e.notes)
                        if e.lessons:
                            st.markdown("**Lessons**")
                            st.write(e.lessons)


def render_journal_page(default_micro: str = "") -> None:
    """Full Trading Journal navigation page."""
    page_hero(
        "Trading Journal",
        "Private blotter · honest notes · Reversion & Scalping quick cards beside you",
        side="bull",
        desk_tag="JOURNAL DESK · PRIVATE BLOTTER",
    )
    from disclosure import render_disclosure

    render_disclosure(expanded=False)

    # Top row: Quick Reference (left) | Journal composer (right)
    # Full-width below: LIVE multi-day 1H charts (wider trend view)
    left, right = st.columns([1, 1], gap="large")
    with left:
        render_quick_reference_panel()
    with right:
        render_journal_composer(
            key_prefix="page",
            default_micro=default_micro,
            compact=False,
        )

    st.markdown("---")
    # Full board width so more 1H candles / structure are readable
    render_live_micro_charts(
        key_prefix="page_tv",
        height=TV_CHART_HEIGHT,
        default_micro=default_micro or "MES",
    )

    st.markdown("---")
    render_journal_history(key_prefix="pagehist", show_edit=True)
