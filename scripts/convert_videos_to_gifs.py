"""Convert CPRP branding MP4 videos to full-length looping GIFs for Streamlit."""

from __future__ import annotations

import sys
from pathlib import Path

import imageio.v2 as imageio
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

# Full clip playback (~6s sources) with smooth loop; sized for web
MAX_WIDTH = 480
SIDEBAR_MAX_WIDTH = 280
FPS = 12  # smooth motion
# No early cut: process entire source (with a safety ceiling)
MAX_DURATION_SEC = 30.0
COLORS = 64


def convert_one(src: Path, dest: Path, max_width: int = MAX_WIDTH) -> None:
    if not src.is_file():
        print(f"skip missing {src}")
        return

    reader = imageio.get_reader(str(src), format="ffmpeg")
    meta = reader.get_meta_data()
    src_fps = float(meta.get("fps") or 24) or 24.0
    try:
        src_duration = float(meta.get("duration") or 0) or None
    except Exception:
        src_duration = None

    # Sample evenly so the whole clip is represented at target FPS
    frame_interval = max(1, int(round(src_fps / FPS)))
    # Allow full video length (+ small pad); do not truncate to 3s
    if src_duration and src_duration > 0:
        max_frames = int(round(src_duration * FPS)) + 2
    else:
        max_frames = int(FPS * MAX_DURATION_SEC)

    frames: list[Image.Image] = []
    for i, frame in enumerate(reader):
        if i % frame_interval != 0:
            continue
        img = Image.fromarray(frame)
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        if w > max_width:
            nh = max(1, int(h * (max_width / w)))
            img = img.resize((max_width, nh), Image.Resampling.LANCZOS)
        frames.append(img.convert("P", palette=Image.Palette.ADAPTIVE, colors=COLORS))
        if len(frames) >= max_frames:
            break
    reader.close()

    if not frames:
        print(f"no frames from {src.name}")
        return

    # Ensure first/last frames are similar-friendly for a clean loop when possible:
    # keep full sequence as-is (source videos already loop-friendly).
    dest.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = max(1, int(round(1000 / FPS)))
    frames[0].save(
        dest,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,  # infinite loop
        optimize=False,
        disposal=2,
    )
    play_sec = len(frames) * duration_ms / 1000.0
    print(
        f"OK {src.name} -> {dest.relative_to(ROOT)} "
        f"({dest.stat().st_size // 1024} KB, {len(frames)} frames, "
        f"~{play_sec:.1f}s loop, src={src_duration or '?'}s @ {src_fps:.0f}fps)"
    )


def main() -> int:
    pairs = [
        (ASSETS / "cprp_logo_video.mp4", ASSETS / "cprp_logo_video.gif", MAX_WIDTH),
        (ASSETS / "cprp_logo_video_alt.mp4", ASSETS / "cprp_logo_video_alt.gif", SIDEBAR_MAX_WIDTH),
        (ASSETS / "cprp_member_chat_hero.mp4", ASSETS / "cprp_member_chat_hero.gif", MAX_WIDTH),
        # Session Selector + sidebar brand clips (prefer GIF for seamless loop UI)
        (ASSETS / "cprp_session_selector_video.mp4", ASSETS / "cprp_session_selector_video.gif", MAX_WIDTH),
        (ASSETS / "cprp_sidebar_video.mp4", ASSETS / "cprp_sidebar_video.gif", SIDEBAR_MAX_WIDTH),
        (
            ASSETS / "branding" / "cprp_session_selector_video.mp4",
            ASSETS / "branding" / "cprp_session_selector_video.gif",
            MAX_WIDTH,
        ),
        (
            ASSETS / "branding" / "cprp_sidebar_video.mp4",
            ASSETS / "branding" / "cprp_sidebar_video.gif",
            SIDEBAR_MAX_WIDTH,
        ),
        (
            ASSETS / "branding" / "cprp_logo_video_main.mp4",
            ASSETS / "branding" / "cprp_logo_video_main.gif",
            MAX_WIDTH,
        ),
        (
            ASSETS / "branding" / "cprp_logo_video_alt.mp4",
            ASSETS / "branding" / "cprp_logo_video_alt.gif",
            SIDEBAR_MAX_WIDTH,
        ),
        (
            ASSETS / "branding" / "cprp_logo_video_variant_1.mp4",
            ASSETS / "branding" / "cprp_logo_video_variant_1.gif",
            MAX_WIDTH,
        ),
        (
            ASSETS / "branding" / "cprp_logo_video_variant_2.mp4",
            ASSETS / "branding" / "cprp_logo_video_variant_2.gif",
            MAX_WIDTH,
        ),
        (
            ASSETS / "branding" / "cprp_logo_video_variant_3.mp4",
            ASSETS / "branding" / "cprp_logo_video_variant_3.gif",
            MAX_WIDTH,
        ),
        (
            ASSETS / "branding" / "cprp_logo_video_variant_4.mp4",
            ASSETS / "branding" / "cprp_logo_video_variant_4.gif",
            MAX_WIDTH,
        ),
    ]
    if not (ASSETS / "cprp_logo_video.mp4").is_file():
        main_mp4 = ASSETS / "branding" / "cprp_logo_video_main.mp4"
        if main_mp4.is_file():
            pairs[0] = (main_mp4, ASSETS / "cprp_logo_video.gif", MAX_WIDTH)

    for src, dest, mw in pairs:
        try:
            convert_one(src, dest, max_width=mw)
        except Exception as exc:
            print(f"FAIL {src.name}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
