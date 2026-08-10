"""
Email helpers for CPRP subscriber notifications.

Configure via Streamlit secrets (local: .streamlit/secrets.toml,
Cloud: app Settings → Secrets):

[auth]
notify_email = "you@example.com"
pepper = "long-random-string"

[smtp]
host = "smtp.gmail.com"
port = 587
username = "you@example.com"
password = "your-app-password"
from_email = "you@example.com"
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any

import streamlit as st

from config import APP_NAME, CREATOR, PROTOCOL_SHORT


def _secrets_section(name: str) -> dict[str, Any]:
    try:
        section = st.secrets.get(name, {})
        # Streamlit AttrDict → plain dict
        return dict(section) if section is not None else {}
    except Exception:
        return {}


def smtp_configured() -> bool:
    smtp = _secrets_section("smtp")
    auth = _secrets_section("auth")
    return bool(
        smtp.get("host")
        and smtp.get("username")
        and smtp.get("password")
        and (auth.get("notify_email") or smtp.get("from_email"))
    )


def notify_owner_of_signup(subscriber_email: str) -> None:
    """
    Email the site owner that a new subscriber signed up.
    Raises on hard misconfiguration so callers can surface a soft warning.
    """
    smtp = _secrets_section("smtp")
    auth = _secrets_section("auth")

    host = str(smtp.get("host") or "").strip()
    port = int(smtp.get("port") or 587)
    username = str(smtp.get("username") or "").strip()
    password = str(smtp.get("password") or "").strip()
    from_email = str(smtp.get("from_email") or username).strip()
    notify_to = str(auth.get("notify_email") or from_email).strip()

    if not (host and username and password and notify_to):
        raise RuntimeError(
            "Email not configured. Add [smtp] and [auth] notify_email to Streamlit secrets."
        )

    msg = EmailMessage()
    msg["Subject"] = f"[{PROTOCOL_SHORT}] New subscriber: {subscriber_email}"
    msg["From"] = from_email
    msg["To"] = notify_to
    msg.set_content(
        f"""New subscriber signed up for {APP_NAME}.

Email: {subscriber_email}

This address was added to your CPRP tool subscriber list.

— Automated notice from {APP_NAME}
  Founder: {CREATOR}
"""
    )

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.ehlo()
        if port == 587:
            server.starttls()
            server.ehlo()
        server.login(username, password)
        server.send_message(msg)
