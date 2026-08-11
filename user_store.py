"""
Permanent member account storage for CPRP.

Priority:
  1) PostgreSQL when secrets provide database.url / DATABASE_URL
     (Neon, Supabase, Railway, etc. — survives Streamlit Cloud redeploys)
  2) Local SQLite data/users.db (local dev / fallback)

Founder account: ImzCpr@gmail.com (normalized to imzcpr@gmail.com).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional, Sequence

import streamlit as st

# Project-local fallback (ephemeral on Streamlit Cloud)
_LOCAL_DIR = Path(__file__).resolve().parent / "data"
_LOCAL_DB = _LOCAL_DIR / "users.db"

FOUNDER_EMAIL = "imzcpr@gmail.com"


def _secret_database_url() -> str:
    try:
        # Nested TOML: [database] url = "..."
        db = st.secrets.get("database", {})
        if isinstance(db, dict):
            url = str(db.get("url") or db.get("connection_string") or "").strip()
            if url:
                return url
        # Flat / env-style
        url = str(st.secrets.get("DATABASE_URL", "") or "").strip()
        if url:
            return url
    except Exception:
        pass
    return ""


def using_postgres() -> bool:
    url = _secret_database_url().lower()
    return url.startswith("postgres://") or url.startswith("postgresql://")


def storage_label() -> str:
    return "PostgreSQL (permanent)" if using_postgres() else "Local SQLite (temporary on Cloud)"


def _adapt_sql(sql: str, postgres: bool) -> str:
    """Convert SQLite-style placeholders to psycopg2 when needed."""
    if not postgres:
        return sql
    # Replace ? placeholders with %s (not inside strings — our SQL is controlled)
    return sql.replace("?", "%s")


class _PgConn:
    """Minimal sqlite-like wrapper around a psycopg2 connection."""

    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql: str, params: Sequence[Any] | None = None):
        sql = _adapt_sql(sql, postgres=True)
        # Strip SQLite-only COLLATE NOCASE (Postgres uses citext or lower())
        sql = sql.replace(" COLLATE NOCASE", "")
        cur = self._raw.cursor()
        if params is None:
            cur.execute(sql)
        else:
            cur.execute(sql, tuple(params))
        return _PgCursor(cur)

    def commit(self) -> None:
        self._raw.commit()

    def close(self) -> None:
        self._raw.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        try:
            self.commit()
        finally:
            self.close()


class _PgCursor:
    def __init__(self, cur):
        self._cur = cur

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()


@contextmanager
def connect() -> Iterator[Any]:
    """Yield a DB connection (Postgres or SQLite) with .execute / .commit / context manager."""
    url = _secret_database_url()
    if url.lower().startswith("postgres://") or url.lower().startswith("postgresql://"):
        # postgres:// → postgresql:// for some drivers
        if url.lower().startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        try:
            import psycopg2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL URL is configured but psycopg2-binary is not installed. "
                "Add psycopg2-binary to requirements.txt."
            ) from exc
        raw = psycopg2.connect(url, connect_timeout=15)
        raw.autocommit = False
        con = _PgConn(raw)
        try:
            _ensure_users_schema(con, postgres=True)
            yield con
            con.commit()
        except Exception:
            try:
                raw.rollback()
            except Exception:
                pass
            raise
        finally:
            con.close()
        return

    # Local SQLite fallback
    _LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(_LOCAL_DB), check_same_thread=False, timeout=30)
    con.execute("PRAGMA journal_mode=WAL;")
    try:
        _ensure_users_schema(con, postgres=False)
        yield con
        con.commit()
    finally:
        con.close()


def _ensure_users_schema(con: Any, *, postgres: bool) -> None:
    if postgres:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TEXT NOT NULL,
                display_name TEXT
            )
            """
        )
        # Unique username when set (case-insensitive via unique index on lower())
        try:
            con.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_users_display_name_lower
                ON users (LOWER(display_name))
                WHERE display_name IS NOT NULL AND display_name <> ''
                """
            )
        except Exception:
            pass
        con.commit()
        return

    # SQLite
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT NOT NULL,
            display_name TEXT
        )
        """
    )
    cols = {r[1] for r in con.execute("PRAGMA table_info(users)").fetchall()}
    if "display_name" not in cols:
        con.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
    con.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_display_name
        ON users (display_name COLLATE NOCASE)
        WHERE display_name IS NOT NULL AND display_name != ''
        """
    )
    con.commit()


@dataclass
class UserRow:
    email: str
    password_hash: str
    salt: str
    created_at: str
    display_name: Optional[str] = None


def fetch_user(email: str) -> Optional[UserRow]:
    email = (email or "").strip().lower()
    with connect() as con:
        if using_postgres():
            row = con.execute(
                "SELECT email, password_hash, salt, created_at, display_name FROM users WHERE LOWER(email) = LOWER(?)",
                (email,),
            ).fetchone()
        else:
            row = con.execute(
                "SELECT email, password_hash, salt, created_at, display_name FROM users WHERE email = ? COLLATE NOCASE",
                (email,),
            ).fetchone()
    if not row:
        return None
    return UserRow(
        email=row[0],
        password_hash=row[1],
        salt=row[2],
        created_at=row[3],
        display_name=row[4],
    )


def user_exists(email: str) -> bool:
    return fetch_user(email) is not None


def count_users() -> int:
    with connect() as con:
        row = con.execute("SELECT COUNT(*) FROM users").fetchone()
    return int(row[0] or 0) if row else 0


def insert_user(
    email: str,
    password_hash: str,
    salt: str,
    created_at: str,
    display_name: Optional[str] = None,
) -> None:
    email = (email or "").strip().lower()
    with connect() as con:
        con.execute(
            """
            INSERT INTO users (email, password_hash, salt, created_at, display_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            (email, password_hash, salt, created_at, display_name),
        )
        con.commit()


def update_password_hash(email: str, password_hash: str) -> None:
    email = (email or "").strip().lower()
    with connect() as con:
        if using_postgres():
            con.execute(
                "UPDATE users SET password_hash = ? WHERE LOWER(email) = LOWER(?)",
                (password_hash, email),
            )
        else:
            con.execute(
                "UPDATE users SET password_hash = ? WHERE email = ? COLLATE NOCASE",
                (password_hash, email),
            )
        con.commit()


def update_display_name(email: str, username: str) -> None:
    email = (email or "").strip().lower()
    with connect() as con:
        if using_postgres():
            con.execute(
                "UPDATE users SET display_name = ? WHERE LOWER(email) = LOWER(?)",
                (username, email),
            )
        else:
            con.execute(
                "UPDATE users SET display_name = ? WHERE email = ? COLLATE NOCASE",
                (username, email),
            )
        con.commit()


def username_taken(name: str, exclude_email: str = "") -> bool:
    name = (name or "").strip()
    exclude_email = (exclude_email or "").strip().lower()
    with connect() as con:
        if using_postgres():
            if exclude_email:
                row = con.execute(
                    """
                    SELECT 1 FROM users
                    WHERE LOWER(display_name) = LOWER(?)
                      AND LOWER(email) <> LOWER(?)
                    """,
                    (name, exclude_email),
                ).fetchone()
            else:
                row = con.execute(
                    "SELECT 1 FROM users WHERE LOWER(display_name) = LOWER(?)",
                    (name,),
                ).fetchone()
        else:
            if exclude_email:
                row = con.execute(
                    """
                    SELECT 1 FROM users
                    WHERE display_name = ? COLLATE NOCASE
                      AND email != ?
                    """,
                    (name, exclude_email),
                ).fetchone()
            else:
                row = con.execute(
                    "SELECT 1 FROM users WHERE display_name = ? COLLATE NOCASE",
                    (name,),
                ).fetchone()
    return row is not None


def list_all_users() -> list[tuple[str, str, Optional[str]]]:
    """Return (email, created_at, display_name) newest first."""
    with connect() as con:
        rows = con.execute(
            """
            SELECT email, created_at, display_name
            FROM users
            ORDER BY created_at DESC
            """
        ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]
