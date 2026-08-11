"""
Clean autoplay / loop media for CPRP branding.

- GIFs via st.image → seamless browser loop, no play button
- MP4 via HTML5 <video autoplay muted loop playsinline> with NO controls
  (st.video always shows a player chrome — avoid it for brand media)
"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


def _video_html(b64: str, *, radius: int = 10) -> str:
    return f"""
<div style="width:100%;line-height:0;border-radius:{radius}px;overflow:hidden;
            background:transparent;margin:0;padding:0;">
  <video
    autoplay
    muted
    loop
    playsinline
    webkit-playsinline
    disablepictureinpicture
    controlslist="nodownload nofullscreen noremoteplayback noplaybackrate"
    style="width:100%;height:auto;display:block;object-fit:contain;
           pointer-events:none;border:0;outline:none;background:transparent;"
  >
    <source src="data:video/mp4;base64,{b64}" type="video/mp4" />
  </video>
</div>
<script>
  // Ensure autoplay after Streamlit injects the iframe (browsers require muted)
  (function () {{
    var v = document.querySelector('video');
    if (!v) return;
    v.muted = true;
    v.playsInline = true;
    var p = v.play();
    if (p && p.catch) p.catch(function () {{ /* ignore autoplay block */ }});
  }})();
</script>
"""


def render_loop_media(
    *candidates: Path | str | None,
    caption: str | None = None,
    height: int = 320,
    sidebar: bool = False,
) -> bool:
    """
    Render the first existing candidate as clean autoplay loop media.
    Preference order: GIF → MP4 (silent HTML) → still image.
    Returns True if something was shown.
    """
    paths = [Path(p) for p in candidates if p is not None]

    # 1) GIF — true seamless loop, no player UI
    for p in paths:
        if p.is_file() and p.suffix.lower() == ".gif":
            if sidebar:
                st.sidebar.image(str(p), use_container_width=True, caption=caption)
            else:
                st.image(str(p), use_container_width=True, caption=caption)
            return True

    # 2) MP4 — custom HTML autoplay/loop, no controls / no play button
    for p in paths:
        if p.is_file() and p.suffix.lower() == ".mp4":
            try:
                raw = p.read_bytes()
            except OSError:
                continue
            # Guard very large embeds (Streamlit iframe size)
            if len(raw) > 8 * 1024 * 1024:
                continue
            b64 = base64.b64encode(raw).decode("ascii")
            html = _video_html(b64)
            frame_h = max(120, min(height, 720))
            if sidebar:
                # Must nest under sidebar context so the iframe lands in the side panel
                with st.sidebar:
                    components.html(html, height=min(frame_h, 220), scrolling=False)
                    if caption:
                        st.caption(caption)
            else:
                components.html(html, height=frame_h, scrolling=False)
                if caption:
                    st.caption(caption)
            return True

    # 3) Still images
    for p in paths:
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            if sidebar:
                st.sidebar.image(str(p), use_container_width=True, caption=caption)
            else:
                st.image(str(p), use_container_width=True, caption=caption)
            return True

    return False
