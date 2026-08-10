"""Convert CPRP branding MP4 videos to looping GIFs for Streamlit display."""

from __future__ import annotations

import sys
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

# Target max width and FPS to keep GIF sizes reasonable for Streamlit Cloud / git push
MAX_WIDTH = 360
SIDEBAR_MAX_WIDTH = 200
FPS = 6
MAX_DURATION_SEC = 3.0  # cap long clips


def convert_one(src: Path, dest: Path, max_width: int = MAX_WIDTH) -> None:
    if not src.is_file():
        print(f"skip missing {src}")
        return

    reader = imageio.get_reader(str(src), format="ffmpeg")
    meta = reader.get_meta_data()
    src_fps = float(meta.get("fps") or 24) or 24.0
    nframes = meta.get("nframes")
    # duration estimate
    try:
        duration = float(meta.get("duration") or 0) or None
    except Exception:
        duration = None

    frame_interval = max(1, int(round(src_fps / FPS)))
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
            nh = int(h * (max_width / w))
            img = img.resize((max_width, nh), Image.Resampling.LANCZOS)
        # reduce colors for smaller GIF
        frames.append(img.convert("P", palette=Image.Palette.ADAPTIVE, colors=48))
        if len(frames) >= max_frames:
            break
    reader.close()

    if not frames:
        print(f"no frames from {src.name}")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = int(1000 / FPS)
    frames[0].save(
        dest,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,  # infinite loop
        optimize=False,
        disposal=2,
    )
    print(f"OK {src.name} -> {dest.relative_to(ROOT)} ({dest.stat().st_size // 1024} KB, {len(frames)} frames)")


def main() -> int:
    pairs = [
        # (source mp4, dest gif, max_width)
        (ASSETS / "cprp_logo_video.mp4", ASSETS / "cprp_logo_video.gif", MAX_WIDTH),
        (ASSETS / "cprp_logo_video_alt.mp4", ASSETS / "cprp_logo_video_alt.gif", SIDEBAR_MAX_WIDTH),
        (ASSETS / "cprp_member_chat_hero.mp4", ASSETS / "cprp_member_chat_hero.gif", MAX_WIDTH),
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
    # Also copy primary root from branding main if root missing source
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
