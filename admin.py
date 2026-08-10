"""
Admin / Founder controls for CPRP Session Micro Selector.

Only the founder account(s) may open this panel or perform application-level edits
(document sync, chat moderation, subscriber list, capacity settings view).
"""

from __future__ import annotations

import streamlit as st

from auth import (
    current_display_name,
    current_user_email,
    is_admin,
    list_subscribers,
)
from config import (
    CREATOR,
    FOUNDER_NAME,
    PROTOCOL_NAME,
    PROTOCOL_SHORT,
    RULEBOOK_VERSION,
)
from journal import count_entries, journal_max_entries


def is_current_user_admin() -> bool:
    """True only for the founder admin account(s)."""
    return is_admin()


def require_admin() -> bool:
    """Return True if current user is admin; otherwise show denied UI."""
    if is_current_user_admin():
        return True
    st.error("**Access denied.** Only the ADMIN / FOUNDER can open this area.")
    st.info(
        f"Application edits and domain administration are reserved for "
        f"**{FOUNDER_NAME}** (ADMIN / FOUNDER)."
    )
    return False


def _chat_message_count() -> int:
    try:
        from chat import _conn

        with _conn() as con:
            row = con.execute("SELECT COUNT(*) FROM chat_messages").fetchone()
        return int(row[0] or 0) if row else 0
    except Exception:
        return 0


def _active_online() -> int:
    try:
        from chat import active_user_count

        return active_user_count()
    except Exception:
        return 0


def render_admin_panel() -> None:
    """Full Admin / Founder control panel."""
    if not require_admin():
        return

    email = current_user_email() or ""
    name = current_display_name() or FOUNDER_NAME

    st.title("Admin / Founder")
    st.markdown(
        f"""
<span style="
  display:inline-block;background:linear-gradient(90deg,#1d4ed8,#7c3aed);
  color:white;font-weight:700;font-size:0.85rem;letter-spacing:0.04em;
  padding:0.35rem 0.75rem;border-radius:999px;">
  ADMIN / FOUNDER
</span>
&nbsp; **{name}** · `{email}`
""",
        unsafe_allow_html=True,
    )
    st.caption(
        f"You are the only account authorized to edit application data and administration "
        f"controls for **{PROTOCOL_NAME}** ({PROTOCOL_SHORT}). "
        f"Members can use the tool, journal, and chat — they cannot change app settings."
    )

    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    subs = list_subscribers()
    c1.metric("Registered members", len(subs))
    c2.metric("Online now", _active_online())
    c3.metric("Chat messages", _chat_message_count())
    c4.metric("Rulebook", f"v{RULEBOOK_VERSION}")

    st.markdown("---")
    st.subheader("Subscriber list")
    st.caption("Accounts that signed up (email list). Also emailed to you on each new signup.")
    if not subs:
        st.info("No members yet.")
    else:
        rows = [
            {
                "Email": s.email,
                "Username": s.display_name or "—",
                "Joined (UTC)": s.created_at,
                "Journal notes": count_entries(s.email),
            }
            for s in subs
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Application edits (Founder only)")

    # Document / branding sync
    st.markdown("##### Sync official documents & branding")
    st.caption("Pull latest files from your CPRP Trading folder into the app assets.")
    if st.button("Sync branding & documents now", type="primary", key="admin_sync"):
        try:
            from sync_cprp_assets import sync_cprp_assets

            with st.spinner("Scanning CPRP Trading…"):
                rep = sync_cprp_assets()
            st.session_state.doc_sync_report = rep
            for line in rep.summary_lines():
                st.markdown(f"- {line}")
            if rep.copied:
                st.success(f"Updated {len(rep.copied)} file(s).")
            else:
                st.info("Already up to date (or no newer source files found).")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Sync failed: {exc}")

    st.markdown("##### Member Chat moderation")
    st.caption("Remove individual messages or clear the room.")
    try:
        from chat import delete_message, list_recent_for_admin, clear_all_messages

        msgs = list_recent_for_admin(limit=40)
        if not msgs:
            st.caption("No chat messages.")
        else:
            for m in msgs:
                cols = st.columns([4, 1])
                with cols[0]:
                    st.markdown(
                        f"**{m['display_name']}** · `{m['created_at']}`  \n"
                        f"{m['body']}"
                    )
                with cols[1]:
                    if st.button("Delete", key=f"adm_del_msg_{m['id']}"):
                        delete_message(int(m["id"]))
                        st.rerun()
        if st.button("Clear entire Member Chat", key="adm_clear_chat"):
            n = clear_all_messages()
            st.warning(f"Deleted {n} chat messages.")
            st.rerun()
    except Exception as exc:  # noqa: BLE001
        st.caption(f"Chat moderation unavailable: {exc}")

    st.markdown("##### Journal capacity")
    st.caption(
        f"Per-member journal limit is currently **{journal_max_entries()}** entries. "
        "Override in Streamlit secrets: `[journal] max_entries = 50`."
    )

    st.markdown("---")
    st.subheader("Domain & code ownership")
    st.markdown(
        f"""
| Control | Owner |
|---------|--------|
| Application admin panel | **ADMIN / FOUNDER only** ({FOUNDER_NAME}) |
| Document / branding sync | **ADMIN / FOUNDER only** |
| Chat moderation | **ADMIN / FOUNDER only** |
| GitHub repository & Streamlit Cloud deploy | **You** (outside this app) |
| Member journal / chat posts | Each member (their own content only) |

**GitHub:** [imzcpr-blip/micro-range-selector](https://github.com/imzcpr-blip/micro-range-selector)  
**Founder:** {CREATOR}
"""
    )
    st.info(
        "To keep the **public domain app** under your control: only your GitHub account "
        "should have write access, and only you should hold Streamlit Cloud admin on the app. "
        "This in-app role does not replace GitHub/Streamlit account security — it protects "
        "in-app administrative actions."
    )
