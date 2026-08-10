"""
Simple email + password auth for CPRP Session Micro Selector.

- Login identity = email address
- Optional public display username chosen after account creation
- Passwords stored as salted PBKDF2 hashes (never plain text)
- Signups trigger owner email notification (subscriber list)
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import streamlit as st

from config import (
    ADMIN_EMAILS,
    ADMIN_ROLE_LABEL,
    APP_NAME,
    BRANDING_LOGO_ICON,
    BRANDING_LOGO_IMAGE,
    BRANDING_LOGO_VIDEO,
    BRANDING_LOGO_VIDEO_ALT,
    BRANDING_OFFICIAL_SEAL,
    BRANDING_OFFICIAL_SEAL_ANIM,
    BRANDING_OFFICIAL_SEAL_ANIM_BRAND,
    BRANDING_OFFICIAL_SEAL_BRAND,
    CREATOR,
    PROTOCOL_SHORT,
)

DATA_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DATA_DIR / "users.db"
SUBSCRIBERS_CSV = DATA_DIR / "subscribers.csv"

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
MIN_PASSWORD_LEN = 8
PBKDF2_ITERATIONS = 200_000


@dataclass
class UserRecord:
    email: str
    created_at: str
    display_name: Optional[str] = None


def _pepper() -> str:
    try:
        return str(st.secrets.get("auth", {}).get("pepper", "") or "")
    except Exception:
        return ""


def _conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
    con.execute("PRAGMA journal_mode=WAL;")
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
    # Migrate older DBs that lack display_name
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
    return con


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(normalize_email(email)))


def normalize_username(name: str) -> str:
    return (name or "").strip()


def is_valid_username(name: str) -> bool:
    return bool(USERNAME_RE.match(normalize_username(name)))


def _hash_password(password: str, salt_hex: str) -> str:
    material = (password + _pepper()).encode("utf-8")
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", material, salt, PBKDF2_ITERATIONS)
    return digest.hex()


def user_exists(email: str) -> bool:
    email = normalize_email(email)
    with _conn() as con:
        row = con.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
    return row is not None


def username_taken(name: str, exclude_email: Optional[str] = None) -> bool:
    name = normalize_username(name)
    exclude_email = normalize_email(exclude_email or "")
    with _conn() as con:
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


def create_user(email: str, password: str) -> tuple[bool, str]:
    """Register a new user (email + password). Display name chosen next."""
    email = normalize_email(email)
    if not is_valid_email(email):
        return False, "Please enter a valid email address."
    if len(password or "") < MIN_PASSWORD_LEN:
        return False, f"Password must be at least {MIN_PASSWORD_LEN} characters."
    if user_exists(email):
        return False, "An account with this email already exists. Please log in."

    salt_hex = secrets.token_hex(16)
    pw_hash = _hash_password(password, salt_hex)
    created = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        with _conn() as con:
            con.execute(
                """
                INSERT INTO users (email, password_hash, salt, created_at, display_name)
                VALUES (?, ?, ?, ?, NULL)
                """,
                (email, pw_hash, salt_hex, created),
            )
            con.commit()
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists. Please log in."

    _append_subscriber_csv(email, created)
    return True, "Account created. Choose a public username next."


def verify_login(email: str, password: str) -> tuple[bool, str]:
    email = normalize_email(email)
    if not is_valid_email(email):
        return False, "Please enter a valid email address."
    with _conn() as con:
        row = con.execute(
            "SELECT password_hash, salt FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    if not row:
        return False, "No account found for that email. Please sign up."
    stored_hash, salt_hex = row
    candidate = _hash_password(password, salt_hex)
    if not hmac.compare_digest(stored_hash, candidate):
        return False, "Incorrect password."
    return True, "Logged in."


def get_display_name(email: str) -> Optional[str]:
    email = normalize_email(email)
    with _conn() as con:
        row = con.execute(
            "SELECT display_name FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    if not row:
        return None
    name = (row[0] or "").strip()
    return name or None


def set_display_name(email: str, username: str) -> tuple[bool, str]:
    email = normalize_email(email)
    username = normalize_username(username)
    if not is_valid_username(username):
        return (
            False,
            "Username must be 3–20 characters: letters, numbers, and underscores only.",
        )
    if username_taken(username, exclude_email=email):
        return False, "That username is already taken. Please choose another."
    try:
        with _conn() as con:
            con.execute(
                "UPDATE users SET display_name = ? WHERE email = ?",
                (username, email),
            )
            con.commit()
    except sqlite3.IntegrityError:
        return False, "That username is already taken. Please choose another."
    return True, f"Username set to {username}."


def _append_subscriber_csv(email: str, created_at: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    new_file = not SUBSCRIBERS_CSV.is_file()
    with SUBSCRIBERS_CSV.open("a", encoding="utf-8") as f:
        if new_file:
            f.write("email,created_at\n")
        f.write(f"{email},{created_at}\n")


def list_subscribers() -> list[UserRecord]:
    with _conn() as con:
        rows = con.execute(
            """
            SELECT email, created_at, display_name
            FROM users ORDER BY created_at DESC
            """
        ).fetchall()
    return [
        UserRecord(email=r[0], created_at=r[1], display_name=r[2]) for r in rows
    ]


def is_logged_in() -> bool:
    return bool(st.session_state.get("auth_email"))


def current_user_email() -> Optional[str]:
    return st.session_state.get("auth_email")


def admin_email_set() -> set[str]:
    """
    Founder admin emails — defaults to ImzCpr@gmail.com only.
    Optional secrets can list the same address; they cannot remove the founder default.
    """
    # Hard-coded founder account (always included)
    emails = {normalize_email(e) for e in ADMIN_EMAILS}
    emails.add("imzcpr@gmail.com")
    try:
        raw = st.secrets.get("auth", {}).get("admin_emails", None)
        if raw is None:
            one = st.secrets.get("auth", {}).get("admin_email", None)
            if one:
                raw = [one]
        if isinstance(raw, str):
            raw = [raw]
        # Only accept ImzCpr@gmail.com from secrets (ignore accidental extra admins)
        if raw:
            for x in raw:
                n = normalize_email(x)
                if n == "imzcpr@gmail.com":
                    emails.add(n)
    except Exception:
        pass
    return emails


def is_admin(email: Optional[str] = None) -> bool:
    """True only for ImzCpr@gmail.com (ADMIN / FOUNDER)."""
    email = normalize_email(email or current_user_email() or "")
    if not email:
        return False
    # Strict: only the founder Gmail account
    return email == "imzcpr@gmail.com"


def current_display_name() -> Optional[str]:
    email = current_user_email()
    if not email:
        return None
    # Founder always shows a clear public name if they never set one
    if is_admin(email):
        stored = None
        cached = st.session_state.get("display_name")
        if cached:
            return cached
        stored = get_display_name(email)
        if stored:
            st.session_state.display_name = stored
            return stored
        # Default founder display if not set yet
        return "Founder"
    cached = st.session_state.get("display_name")
    if cached:
        return cached
    name = get_display_name(email)
    if name:
        st.session_state.display_name = name
    return name


def logout() -> None:
    try:
        from chat import clear_presence_for_session

        clear_presence_for_session()
    except Exception:
        pass
    for key in ("auth_email", "auth_just_signed_up", "display_name", "chat_session_id"):
        if key in st.session_state:
            del st.session_state[key]


def _render_landing_branding() -> None:
    """Official Seal only on the public welcome landing page (no video/logo below)."""
    seal_candidates = [
        Path(BRANDING_OFFICIAL_SEAL),
        Path(BRANDING_OFFICIAL_SEAL_BRAND),
        Path(BRANDING_OFFICIAL_SEAL_ANIM),
        Path(BRANDING_OFFICIAL_SEAL_ANIM_BRAND),
    ]
    for p in seal_candidates:
        if p.is_file():
            # Prefer static seal JPG over animated GIF for a clean, single-mark landing
            if p.suffix.lower() == ".gif" and any(
                Path(s).is_file() and Path(s).suffix.lower() in {".jpg", ".jpeg", ".png"}
                for s in (
                    BRANDING_OFFICIAL_SEAL,
                    BRANDING_OFFICIAL_SEAL_BRAND,
                )
            ):
                continue
            _, mid, _ = st.columns([1, 1.2, 1])
            with mid:
                st.image(
                    str(p),
                    use_container_width=True,
                    caption="CPRP Official Seal",
                )
            return
    st.caption("CPRP Official Seal not found.")


def require_login() -> bool:
    """
    Render login/signup UI if needed.
    Returns True when the user is authenticated (display name may still be required).
    """
    if is_logged_in():
        return True

    # ── Landing / welcome (professional desk look; no BULL/BEAR labels) ──
    from wallstreet_ui import inject_wallstreet_theme, market_tape, page_hero

    inject_wallstreet_theme()
    _render_landing_branding()
    # Tape without bull/bear wording (glyphs only stripped on landing)
    market_tape()
    page_hero(
        "CPRP Trading Strategies",
        "Session Micro Range Selector · Cooper Precision Reversion Protocol · by Raymon Michael Cooper",
        side="bull",
        desk_tag="MEMBER ACCESS · TRADING DESK",
    )
    st.markdown(
        "*Trade the boundaries. Respect the structure. Control the risk.*"
    )

    # Plain expanders on landing — no candle / BULL / BEAR prefixes in labels
    with st.expander("Access the Tool / Site", expanded=True):
        st.markdown(
            f"""
To use this site you need a free member account:

1. **Sign up** with a valid **email address** and a **password** (at least {MIN_PASSWORD_LEN} characters).  
2. Confirm the risk acknowledgment (futures trading involves substantial risk of loss).  
3. **Log in** anytime with the same email and password.

Without signing up or logging in, the Session Micro Range Selector, Trading Journal, Community, Member Chat, and other member tools stay locked.
"""
        )

    with st.expander("After you sign up — create a custom username", expanded=False):
        st.markdown(
            """
Right after your account is created, you’ll be asked to choose a **custom public username**  
(3–20 characters: letters, numbers, and underscores).

- Your **email** is only for login and account recovery.  
- Your **username** is what other members see in Community, Member Chat, and the online list.  
- You can pick something unique that represents you — it does not have to match your email.

Then you’ll have full access to the tool.
"""
        )

    # Full disclosure on landing — plain titles (no candle BULL/BEAR labels)
    from config import (
        DISCLOSURE_BODY,
        DISCLOSURE_THIRD_PARTY_BODY,
        DISCLOSURE_THIRD_PARTY_TITLE,
        DISCLOSURE_TITLE,
    )

    st.markdown("---")
    with st.expander(DISCLOSURE_TITLE, expanded=True):
        st.markdown(f"### {DISCLOSURE_TITLE}")
        st.markdown(DISCLOSURE_BODY)
    with st.expander(DISCLOSURE_THIRD_PARTY_TITLE, expanded=True):
        st.markdown(f"### {DISCLOSURE_THIRD_PARTY_TITLE}")
        st.markdown(DISCLOSURE_THIRD_PARTY_BODY)

    st.markdown("---")
    st.subheader("Member access")

    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

    with tab_login:
        st.caption("Already have an account? Log in with your email and password.")
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email", key="login_email", autocomplete="username")
            password = st.text_input(
                "Password",
                type="password",
                key="login_password",
                autocomplete="current-password",
            )
            submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)
        if submitted:
            ok, msg = verify_login(email, password)
            if ok:
                st.session_state.auth_email = normalize_email(email)
                name = get_display_name(st.session_state.auth_email)
                if name:
                    st.session_state.display_name = name
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    with tab_signup:
        st.caption(
            f"Create a free account with your **email** and a **password** (min {MIN_PASSWORD_LEN} characters). "
            "After signup, you’ll create a **custom username** for Community and chat. "
            "The founder is notified of new members by email."
        )
        with st.form("signup_form", clear_on_submit=False):
            email = st.text_input("Email", key="signup_email", autocomplete="username")
            password = st.text_input(
                "Password",
                type="password",
                key="signup_password",
                autocomplete="new-password",
            )
            password2 = st.text_input(
                "Confirm password",
                type="password",
                key="signup_password2",
                autocomplete="new-password",
            )
            agree = st.checkbox(
                "I have read and agree to the Acknowledgement & Disclosure above. "
                "I understand CPRP is not personalized financial advice, "
                "futures trading involves substantial risk of loss, "
                "and I participate at my own risk.",
                key="signup_agree",
            )
            submitted = st.form_submit_button(
                "Create account", type="primary", use_container_width=True
            )

        if submitted:
            if not agree:
                st.error("Please confirm the risk acknowledgment to sign up.")
            elif password != password2:
                st.error("Passwords do not match.")
            else:
                ok, msg = create_user(email, password)
                if ok:
                    notify_error = None
                    try:
                        from emailer import notify_owner_of_signup

                        notify_owner_of_signup(normalize_email(email))
                    except Exception as exc:  # noqa: BLE001
                        notify_error = str(exc)

                    st.session_state.auth_email = normalize_email(email)
                    st.session_state.auth_just_signed_up = True
                    st.success(msg)
                    if notify_error:
                        st.warning(
                            "Account created, but the subscriber notification email could not be sent. "
                            "(Owner setup issue: check Streamlit secrets / SMTP.)"
                        )
                    st.rerun()
                else:
                    st.error(msg)

    st.markdown("---")
    st.caption(
        f"CPRP Trading Strategies · Session Micro Range Selector Tool  \n"
        f"Accounts use email + password (hashed). After signup, choose a custom username.  \n"
        f"Not financial advice. © {CREATOR}."
    )
    return False


def require_display_name() -> bool:
    """
    After login, force a public username before entering the app.
    Returns True when a display name is set.
    Founder/admin may skip with a default name.
    """
    email = current_user_email()
    if not email:
        return False

    existing = get_display_name(email)
    if existing:
        st.session_state.display_name = existing
        return True

    # Founder can continue with default "Founder" display name
    if is_admin(email):
        st.session_state.display_name = "Founder"
        # Persist so chat/presence stay consistent
        set_display_name(email, "Founder")
        return True

    st.markdown(
        f"""
# Create your custom username

Welcome to **CPRP Trading Strategies**. You’re signed in as `{email}`.

Next, choose a **custom public username**. This is what other members will see in:
- **Community** posts  
- **Member Chat**  
- The **online members** list  

Your email stays private for login only. Username: **3–20 characters** (letters, numbers, underscores).
"""
    )
    with st.form("username_form"):
        uname = st.text_input(
            "Custom username",
            max_chars=20,
            placeholder="e.g. ChartRanger_01",
            help="3–20 characters: letters, numbers, underscores.",
        )
        submitted = st.form_submit_button(
            "Save username & enter the tool", type="primary", use_container_width=True
        )
    if submitted:
        ok, msg = set_display_name(email, uname)
        if ok:
            st.session_state.display_name = normalize_username(uname)
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.caption("You can only set this once here; contact the founder if you need a change later.")
    return False


def render_account_sidebar() -> None:
    """Show logged-in user + logout in the sidebar."""
    email = current_user_email()
    if not email:
        return
    name = current_display_name()
    st.sidebar.markdown("---")
    if is_admin(email):
        st.sidebar.markdown(
            f"""
<div style="
  display:inline-block;background:linear-gradient(90deg,#1d4ed8,#7c3aed);
  color:#fff;font-weight:700;font-size:0.72rem;letter-spacing:0.06em;
  padding:0.28rem 0.55rem;border-radius:999px;margin-bottom:0.35rem;">
  {ADMIN_ROLE_LABEL}
</div>
""",
            unsafe_allow_html=True,
        )
        st.sidebar.markdown(f"**{name or CREATOR}**  \n`{email}`")
        st.sidebar.caption("Only you can edit app administration.")
    elif name:
        st.sidebar.markdown(f"**{name}**  \n`{email}`")
        st.sidebar.caption("Member")
    else:
        st.sidebar.markdown(f"**Signed in**  \n`{email}`")
    if st.sidebar.button("Log out", use_container_width=True):
        logout()
        st.rerun()
