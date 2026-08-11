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
    BRANDING_OFFICIAL_SEAL_BRAND_JPG,
    BRANDING_OFFICIAL_SEAL_JPG,
    CREATOR,
    PROTOCOL_SHORT,
)
from user_store import (
    FOUNDER_EMAIL,
    count_users as store_count_users,
    fetch_user,
    insert_user,
    list_all_users,
    storage_label,
    update_display_name,
    update_password_hash,
    user_exists as store_user_exists,
    username_taken as store_username_taken,
    using_postgres,
)

DATA_DIR = Path(__file__).resolve().parent / "data"
# Local SQLite path kept for journal/chat modules; accounts use user_store (Postgres when configured)
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


def _auth_secret(key: str, default: str = "") -> str:
    try:
        return str(st.secrets.get("auth", {}).get(key, default) or default)
    except Exception:
        return default


def count_users() -> int:
    try:
        return store_count_users()
    except Exception:
        return 0


def normalize_email(email: str) -> str:
    # Strip whitespace + common invisible chars from mobile paste
    raw = (email or "").strip().lower()
    for ch in ("\u200b", "\u200c", "\u200d", "\ufeff", "\u00a0"):
        raw = raw.replace(ch, "")
    return raw


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(normalize_email(email)))


def normalize_username(name: str) -> str:
    return (name or "").strip()


def is_valid_username(name: str) -> bool:
    return bool(USERNAME_RE.match(normalize_username(name)))


def _hash_password(password: str, salt_hex: str, *, pepper: Optional[str] = None) -> str:
    """Hash password with optional pepper (defaults to secrets auth.pepper)."""
    p = _pepper() if pepper is None else pepper
    material = (password + (p or "")).encode("utf-8")
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", material, salt, PBKDF2_ITERATIONS)
    return digest.hex()


def user_exists(email: str) -> bool:
    try:
        return store_user_exists(normalize_email(email))
    except Exception:
        return False


def ensure_bootstrap_accounts() -> None:
    """
    Ensure the founder account (ImzCpr@gmail.com) exists.

    With PostgreSQL secrets, accounts persist across Cloud redeploys.
    bootstrap_password still creates the founder row if missing (first setup).

      [database]
      url = "postgresql://..."

      [auth]
      admin_email = "ImzCpr@gmail.com"
      bootstrap_password = "your-stable-password"
      pepper = "long-random-stable-string"
    """
    if st.session_state.get("_auth_bootstrap_done"):
        return
    st.session_state["_auth_bootstrap_done"] = True

    password = _auth_secret("bootstrap_password", "")
    if not password or len(password) < MIN_PASSWORD_LEN:
        return

    emails: list[str] = [FOUNDER_EMAIL]
    secret_admin = normalize_email(_auth_secret("admin_email", ""))
    if secret_admin and is_valid_email(secret_admin) and secret_admin not in emails:
        emails.append(secret_admin)
    for e in ADMIN_EMAILS:
        ne = normalize_email(e)
        if ne and ne not in emails and is_valid_email(ne):
            emails.append(ne)

    for email in emails:
        if user_exists(email):
            if not get_display_name(email):
                set_display_name(email, "Founder")
            continue
        ok, _msg = create_user(email, password)
        if ok:
            set_display_name(email, "Founder")


def username_taken(name: str, exclude_email: Optional[str] = None) -> bool:
    try:
        return store_username_taken(normalize_username(name), normalize_email(exclude_email or ""))
    except Exception:
        return False


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
        insert_user(email, pw_hash, salt_hex, created, display_name=None)
    except Exception as exc:
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg or "integrity" in msg:
            return False, "An account with this email already exists. Please log in."
        return False, f"Could not create account ({storage_label()}): {exc}"

    _append_subscriber_csv(email, created)
    backend = "permanent cloud database" if using_postgres() else "local database"
    return True, f"Account created ({backend}). Choose a public username next."


def verify_login(email: str, password: str) -> tuple[bool, str]:
    try:
        ensure_bootstrap_accounts()
    except Exception:
        pass

    email = normalize_email(email)
    if not is_valid_email(email):
        return False, "Please enter a valid email address."

    row = None
    try:
        row = fetch_user(email)
    except Exception as exc:
        return False, f"Database error ({storage_label()}): {exc}"

    if not row:
        try:
            st.session_state["_auth_bootstrap_done"] = False
            ensure_bootstrap_accounts()
            row = fetch_user(email)
        except Exception:
            row = None

    if not row:
        n = count_users()
        if n == 0:
            return (
                False,
                "No accounts found. "
                + (
                    "Sign up to create the first member account, or set auth.bootstrap_password "
                    "in Secrets to auto-create the founder (ImzCpr@gmail.com)."
                    if using_postgres()
                    else "Streamlit Cloud wiped the temporary local database — "
                    "add a permanent [database] url in Secrets, then Sign up again."
                ),
            )
        return (
            False,
            "No account found for that email. Check spelling, or Sign up if this is your first login "
            f"on this server ({storage_label()}).",
        )

    stored_hash, salt_hex = row.password_hash, row.salt
    peppers_to_try = [_pepper(), ""]
    for pep in peppers_to_try:
        candidate = _hash_password(password, salt_hex, pepper=pep)
        if hmac.compare_digest(stored_hash, candidate):
            if pep != _pepper():
                try:
                    new_hash = _hash_password(password, salt_hex, pepper=_pepper())
                    update_password_hash(email, new_hash)
                except Exception:
                    pass
            return True, "Logged in."

    return False, "Incorrect password."


def get_display_name(email: str) -> Optional[str]:
    try:
        row = fetch_user(normalize_email(email))
    except Exception:
        return None
    if not row:
        return None
    name = (row.display_name or "").strip()
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
        update_display_name(email, username)
    except Exception as exc:
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg:
            return False, "That username is already taken. Please choose another."
        return False, f"Could not save username: {exc}"
    return True, f"Username set to {username}."


def _append_subscriber_csv(email: str, created_at: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    new_file = not SUBSCRIBERS_CSV.is_file()
    with SUBSCRIBERS_CSV.open("a", encoding="utf-8") as f:
        if new_file:
            f.write("email,created_at\n")
        f.write(f"{email},{created_at}\n")


def list_subscribers() -> list[UserRecord]:
    try:
        rows = list_all_users()
    except Exception:
        return []
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
    """True only for founder ImzCpr@gmail.com (ADMIN / FOUNDER)."""
    email = normalize_email(email or current_user_email() or "")
    if not email:
        return False
    return email == FOUNDER_EMAIL


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
    """Official Seal only on the public welcome landing page (transparent PNG preferred)."""
    seal_candidates = [
        Path(BRANDING_OFFICIAL_SEAL),           # transparent PNG
        Path(BRANDING_OFFICIAL_SEAL_BRAND),     # branding transparent PNG
        Path(BRANDING_OFFICIAL_SEAL_JPG),       # jpg fallback
        Path(BRANDING_OFFICIAL_SEAL_BRAND_JPG),
        Path(BRANDING_OFFICIAL_SEAL_ANIM),
        Path(BRANDING_OFFICIAL_SEAL_ANIM_BRAND),
    ]
    for p in seal_candidates:
        if p.is_file():
            # Prefer static transparent PNG/JPG over animated GIF
            if p.suffix.lower() == ".gif" and any(
                Path(s).is_file() and Path(s).suffix.lower() in {".png", ".jpg", ".jpeg"}
                for s in (
                    BRANDING_OFFICIAL_SEAL,
                    BRANDING_OFFICIAL_SEAL_BRAND,
                    BRANDING_OFFICIAL_SEAL_JPG,
                    BRANDING_OFFICIAL_SEAL_BRAND_JPG,
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
    # Restore founder from secrets after Cloud redeploy (ephemeral users.db)
    try:
        ensure_bootstrap_accounts()
    except Exception:
        pass

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
2. Confirm the risk acknowledgement (futures trading involves substantial risk of loss).  
3. **Log in** at any time with the same email and password.

Without signing up or logging in, the Session Micro Range Selector, Trading Journal, Community, Member Chat, and other member tools remain locked.
"""
        )

    with st.expander("After you sign up — create a custom username", expanded=False):
        st.markdown(
            """
Right after your account is created, you will be asked to choose a **custom public username**  
(3–20 characters: letters, numbers, and underscores).

- Your **email** is only for login and account recovery.  
- Your **username** is what other members see in Community, Member Chat, and the online list.  
- You can pick something unique that represents you — it does not have to match your email.

You will then have full access to the tool.
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
        try:
            backend = storage_label()
            if using_postgres():
                st.success(f"Account storage: **{backend}** — accounts survive Cloud redeploys.")
            else:
                st.warning(
                    f"Account storage: **{backend}**. "
                    "On Streamlit Cloud this is wiped on redeploy. "
                    "Add a free **Neon/Supabase PostgreSQL** URL under `[database] url` in Secrets "
                    "for permanent accounts."
                )
            if count_users() == 0:
                st.info(
                    "No members yet. Use **Sign up**, or set `auth.bootstrap_password` so "
                    f"**{FOUNDER_EMAIL}** is created automatically as Founder."
                )
        except Exception as exc:
            st.error(f"Database connection issue: {exc}")

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
            "The founder is notified of new members by email. "
            f"Founder account: **{FOUNDER_EMAIL}**."
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
