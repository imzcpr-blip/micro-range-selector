"""
Scan CPRP Trading (and related folders) for official documents + branding,
and sync newer files into this app's assets/ tree.

Run standalone:
  python sync_cprp_assets.py

Or import:
  from sync_cprp_assets import sync_cprp_assets
  report = sync_cprp_assets()
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

# Project paths
APP_ROOT = Path(__file__).resolve().parent
ASSETS = APP_ROOT / "assets"
BRANDING_DIR = ASSETS / "branding"
DOCS_DIR = ASSETS / "docs"

# Folders to scan (first found wins for search roots; all are searched)
DEFAULT_SEARCH_ROOTS = [
    Path(r"C:\Users\imzcp\OneDrive\Desktop\CPRP Trading"),
    Path(r"C:\Users\imzcp\OneDrive\Desktop"),
    Path(r"C:\Users\imzcp\Downloads"),
    Path(r"C:\Users\imzcp\micro-range-selector"),
]

# Document patterns → destination filenames under assets/
# Version is extracted when possible; highest version wins.
DOC_RULES: list[tuple[str, str, str]] = [
    # (glob-ish regex on filename, dest stem, kind)
    (r"(?i)CPRP_Quick_Reference_v?(\d+\.\d+)\.pdf$", "CPRP_Quick_Reference", "quick_ref_pdf"),
    (r"(?i)CPRP_Quick_Reference_v?(\d+\.\d+)\.jpe?g$", "CPRP_Quick_Reference", "quick_ref_img"),
    (r"(?i)CPRP_Rulebook_Update_v?(\d+\.\d+)\.pdf$", "CPRP_Rulebook_Update", "rulebook_update"),
    (
        r"(?i)Cooper_Precision_Reversion_Protocol_Official_Rulebook_v?(\d+\.\d+)\.pdf$",
        "CPRP_Official_Rulebook",
        "rulebook_base",
    ),
    (
        r"(?i)Cooper_Precision_Reversion_Protocol_Quick_Reference_v?(\d+\.\d+)\.pdf$",
        "CPRP_Quick_Reference",
        "quick_ref_pdf",
    ),
    (
        r"(?i)Cooper_Precision_Reversion_Protocol_Quick_Reference\.pdf$",
        "CPRP_Quick_Reference_legacy",
        "quick_ref_legacy",
    ),
]

# Branding files to copy (source name under CPRP_Branding or roots → dest name)
BRANDING_MAP: dict[str, str] = {
    # ── Official 2026 brand suite (numbered stills) ──────────────────────
    "01_CPRP_Brand_Logo_Candlestick.jpg": "cprp_brand_logo_candlestick.jpg",
    "02_CPRP_Brand_Logo_Support_Resistance.jpg": "cprp_brand_logo_support_resistance.jpg",
    "03_CPRP_Icon_Minimal.jpg": "cprp_icon_minimal.jpg",
    "04_CPRP_Banner_Horizontal.jpg": "cprp_banner_horizontal.jpg",
    "05_CPRP_Official_Seal.jpg": "cprp_official_seal.jpg",
    # Animated suite (from CPRP_Branding/Animated/)
    "01_CPRP_Brand_Logo_Candlestick_anim.gif": "cprp_brand_logo_candlestick_anim.gif",
    "01_CPRP_Brand_Logo_Candlestick_anim.mp4": "cprp_brand_logo_candlestick_anim.mp4",
    "02_CPRP_Brand_Logo_Support_Resistance_anim.gif": "cprp_brand_logo_support_resistance_anim.gif",
    "02_CPRP_Brand_Logo_Support_Resistance_anim.mp4": "cprp_brand_logo_support_resistance_anim.mp4",
    "03_CPRP_Icon_Minimal_anim.gif": "cprp_icon_minimal_anim.gif",
    "03_CPRP_Icon_Minimal_anim.mp4": "cprp_icon_minimal_anim.mp4",
    "04_CPRP_Banner_Horizontal_anim.gif": "cprp_banner_horizontal_anim.gif",
    "04_CPRP_Banner_Horizontal_anim.mp4": "cprp_banner_horizontal_anim.mp4",
    "05_CPRP_Official_Seal_anim.gif": "cprp_official_seal_anim.gif",
    "05_CPRP_Official_Seal_anim.mp4": "cprp_official_seal_anim.mp4",
    # ── Legacy suite (kept for compatibility) ────────────────────────────
    "CPRP_Logo_Square_Monogram.jpg": "cprp_logo_square_monogram.jpg",
    "CPRP_Logo_Primary_Chart.jpg": "cprp_logo_primary_chart.jpg",
    "CPRP_Logo_Minimal_Dark.jpg": "cprp_logo_minimal_dark.jpg",
    "CPRP_Logo_Light.jpg": "cprp_logo_light.jpg",
    "CPRP Logo .jpg": "cprp_logo_classic.jpg",
    "CPRP_Logo_Classic.jpg": "cprp_logo_classic.jpg",
    "Main CPRP Logo Video.mp4": "cprp_logo_video_main.mp4",
    "CPRP Video Logo.mp4": "cprp_logo_video_alt.mp4",
    "grok_video_2026-08-09-09-49-22.mp4": "cprp_logo_video_variant_1.mp4",
    "grok_video_2026-08-09-09-51-29.mp4": "cprp_logo_video_variant_2.mp4",
    "grok_video_2026-08-09-09-53-05.mp4": "cprp_logo_video_variant_3.mp4",
    "grok_video_2026-08-09-09-53-06.mp4": "cprp_logo_video_variant_4.mp4",
    # Sidebar panel video
    "grok-video-4bdc3ca9-daa2-4dad-84e6-7f270bc2ca95.mp4": "cprp_sidebar_video.mp4",
}

# Primary app files kept at assets/ root (synced from branding when newer)
PRIMARY_BRANDING_LINKS: list[tuple[str, str]] = [
    # Prefer new official suite for app chrome when available
    ("cprp_official_seal.png", "cprp_official_seal.png"),
    ("cprp_official_seal.jpg", "cprp_official_seal.jpg"),
    ("cprp_official_seal_anim.gif", "cprp_official_seal_anim.gif"),
    ("cprp_icon_minimal.jpg", "cprp_logo_icon.jpg"),
    ("cprp_brand_logo_candlestick.jpg", "cprp_logo_primary.jpg"),
    ("cprp_banner_horizontal.jpg", "cprp_banner_horizontal.jpg"),
    ("cprp_logo_square_monogram.jpg", "cprp_logo_icon.jpg"),  # fallback if icon missing
    ("cprp_logo_primary_chart.jpg", "cprp_logo_primary.jpg"),
    ("cprp_logo_primary_chart.jpg", "cprp_member_chat_poster.jpg"),
    ("cprp_logo_video_main.mp4", "cprp_logo_video.mp4"),
    ("cprp_logo_video_alt.mp4", "cprp_logo_video_alt.mp4"),
    ("cprp_logo_video_variant_1.mp4", "cprp_member_chat_hero.mp4"),
    # Session Selector header video (source: grok_video_2026-08-09-09-51-29.mp4)
    ("cprp_logo_video_variant_2.mp4", "cprp_session_selector_video.mp4"),
    ("cprp_session_selector_video.mp4", "cprp_session_selector_video.mp4"),
    ("cprp_session_selector_video.gif", "cprp_session_selector_video.gif"),
    ("cprp_logo_video_variant_2.gif", "cprp_session_selector_video.gif"),
    # Sidebar panel video
    ("cprp_sidebar_video.mp4", "cprp_sidebar_video.mp4"),
    ("cprp_sidebar_video.mp4", "cprp_logo_video_alt.mp4"),
    ("cprp_sidebar_video.gif", "cprp_sidebar_video.gif"),
    ("cprp_sidebar_video.gif", "cprp_logo_video_alt.gif"),
    # Prefer animated candlestick brand as primary looping media when present
    ("cprp_brand_logo_candlestick_anim.gif", "cprp_logo_video.gif"),
    ("cprp_banner_horizontal_anim.gif", "cprp_logo_video_alt.gif"),
]


@dataclass
class SyncReport:
    scanned_roots: list[str] = field(default_factory=list)
    copied: list[str] = field(default_factory=list)
    skipped_current: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    detected_version: str | None = None
    errors: list[str] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        lines = []
        if self.detected_version:
            lines.append(f"Latest document version detected: **v{self.detected_version}**")
        lines.append(f"Roots scanned: {len(self.scanned_roots)}")
        lines.append(f"Files updated: {len(self.copied)}")
        lines.append(f"Already current: {len(self.skipped_current)}")
        if self.missing:
            lines.append(f"Not found: {', '.join(self.missing)}")
        if self.errors:
            lines.append(f"Errors: {len(self.errors)}")
        return lines


def _version_key(v: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", v)
    return tuple(int(p) for p in parts) if parts else (0,)


def _newer(src: Path, dest: Path) -> bool:
    if not dest.is_file():
        return True
    try:
        return src.stat().st_mtime > dest.stat().st_mtime + 0.5 or src.stat().st_size != dest.stat().st_size
    except OSError:
        return True


def _copy_if_newer(src: Path, dest: Path, report: SyncReport) -> bool:
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not _newer(src, dest):
            report.skipped_current.append(f"{dest.name} (already current)")
            return False
        shutil.copy2(src, dest)
        report.copied.append(f"{src.name} → {dest.relative_to(APP_ROOT)}")
        return True
    except OSError as exc:
        report.errors.append(f"{src} → {dest}: {exc}")
        return False


def _iter_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    files: list[Path] = []
    try:
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            # Skip nested app copies / caches
            name = p.name
            if name.endswith((".pyc", ".py")):
                continue
            parts = {x.lower() for x in p.parts}
            if "__pycache__" in parts:
                continue
            files.append(p)
    except OSError:
        return []
    return files


def find_latest_docs(search_roots: list[Path] | None = None) -> dict[str, tuple[Path, str | None]]:
    """Return kind → (best_path, version_or_None)."""
    roots = search_roots or DEFAULT_SEARCH_ROOTS
    best: dict[str, tuple[Path, str | None, tuple[int, ...]]] = {}

    for root in roots:
        for path in _iter_files(root):
            fname = path.name
            for pattern, _stem, kind in DOC_RULES:
                m = re.search(pattern, fname)
                if not m:
                    continue
                ver = m.group(1) if m.lastindex else None
                key = _version_key(ver or "0")
                prev = best.get(kind)
                if prev is None or key > prev[2] or (key == prev[2] and path.stat().st_mtime > prev[0].stat().st_mtime):
                    best[kind] = (path, ver, key)

    return {k: (v[0], v[1]) for k, v in best.items()}


def sync_branding(search_roots: list[Path] | None = None, report: SyncReport | None = None) -> SyncReport:
    report = report or SyncReport()
    roots = [r for r in (search_roots or DEFAULT_SEARCH_ROOTS) if r.is_dir()]
    BRANDING_DIR.mkdir(parents=True, exist_ok=True)

    # Prefer dedicated branding folder (+ Animated subfolder) when present
    candidate_dirs: list[Path] = []
    for r in roots:
        b = r / "CPRP_Branding"
        if b.is_dir():
            candidate_dirs.append(b)
            anim = b / "Animated"
            if anim.is_dir():
                candidate_dirs.append(anim)
        candidate_dirs.append(r)

    found_names: set[str] = set()
    for d in candidate_dirs:
        for src_name, dest_name in BRANDING_MAP.items():
            if src_name in found_names:
                continue
            src = d / src_name
            if src.is_file():
                found_names.add(src_name)
                _copy_if_newer(src, BRANDING_DIR / dest_name, report)

    for missing_src, dest_name in BRANDING_MAP.items():
        if missing_src not in found_names and not (BRANDING_DIR / dest_name).is_file():
            if dest_name not in report.missing:
                report.missing.append(dest_name)

    # Mirror primary branding into assets root for existing app paths.
    # First match wins for each root_name so official suite can override legacy.
    mirrored: set[str] = set()
    for brand_name, root_name in PRIMARY_BRANDING_LINKS:
        if root_name in mirrored:
            # Only skip if destination already exists from a preferred source this run
            dest = ASSETS / root_name
            if dest.is_file():
                continue
        src = BRANDING_DIR / brand_name
        if src.is_file():
            if _copy_if_newer(src, ASSETS / root_name, report) or (ASSETS / root_name).is_file():
                mirrored.add(root_name)

    return report


def sync_documents(search_roots: list[Path] | None = None, report: SyncReport | None = None) -> SyncReport:
    report = report or SyncReport()
    ASSETS.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    latest = find_latest_docs(search_roots)
    versions = [v for _, v in latest.values() if v]
    if versions:
        report.detected_version = max(versions, key=_version_key)

    # Quick Reference PDF + image
    if "quick_ref_pdf" in latest:
        path, ver = latest["quick_ref_pdf"]
        dest_name = f"CPRP_Quick_Reference_v{ver}.pdf" if ver else path.name
        _copy_if_newer(path, ASSETS / dest_name, report)
        _copy_if_newer(path, DOCS_DIR / dest_name, report)
    else:
        report.missing.append("Quick Reference PDF")

    if "quick_ref_img" in latest:
        path, ver = latest["quick_ref_img"]
        dest_name = f"CPRP_Quick_Reference_v{ver}.jpg" if ver else path.name
        _copy_if_newer(path, ASSETS / dest_name, report)
    elif "quick_ref_pdf" in latest:
        # Render JPG from PDF when image missing
        path, ver = latest["quick_ref_pdf"]
        dest = ASSETS / (f"CPRP_Quick_Reference_v{ver}.jpg" if ver else "CPRP_Quick_Reference.jpg")
        if _render_pdf_preview(path, dest, report):
            report.copied.append(f"(rendered) {dest.name}")

    if "rulebook_update" in latest:
        path, ver = latest["rulebook_update"]
        dest_name = f"CPRP_Rulebook_Update_v{ver}.pdf" if ver else path.name
        _copy_if_newer(path, ASSETS / dest_name, report)
        _copy_if_newer(path, DOCS_DIR / dest_name, report)
    else:
        report.missing.append("Rulebook Update PDF")

    if "rulebook_base" in latest:
        path, ver = latest["rulebook_base"]
        dest_name = f"CPRP_Official_Rulebook_v{ver}.pdf" if ver else path.name
        _copy_if_newer(path, ASSETS / dest_name, report)
        _copy_if_newer(path, DOCS_DIR / dest_name, report)
    else:
        report.missing.append("Official Rulebook base PDF")

    return report


def _render_pdf_preview(pdf_path: Path, jpg_path: Path, report: SyncReport) -> bool:
    if jpg_path.is_file() and not _newer(pdf_path, jpg_path):
        report.skipped_current.append(f"{jpg_path.name} (preview current)")
        return False
    try:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(str(pdf_path))
        page = pdf[0]
        bitmap = page.render(scale=2.0)
        pil = bitmap.to_pil()
        if pil.mode != "RGB":
            pil = pil.convert("RGB")
        jpg_path.parent.mkdir(parents=True, exist_ok=True)
        pil.save(jpg_path, "JPEG", quality=90)
        return True
    except Exception as exc:  # noqa: BLE001 — best-effort preview
        report.errors.append(f"preview render failed for {pdf_path.name}: {exc}")
        return False


def sync_cprp_assets(search_roots: list[Path] | None = None) -> SyncReport:
    """Full sync: documents + branding from CPRP Trading and related folders."""
    roots = [Path(r) for r in (search_roots or DEFAULT_SEARCH_ROOTS)]
    report = SyncReport(scanned_roots=[str(r) for r in roots if r.is_dir()])
    if not report.scanned_roots:
        report.errors.append("No search roots found on disk.")
        return report
    sync_documents(roots, report)
    sync_branding(roots, report)
    return report


def list_branding_images() -> list[Path]:
    if not BRANDING_DIR.is_dir():
        return []
    imgs = sorted(
        [
            p
            for p in BRANDING_DIR.iterdir()
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} and p.is_file()
        ],
        key=lambda p: p.name.lower(),
    )
    return imgs


def list_official_brand_suite() -> list[tuple[str, Path]]:
    """Ordered official 2026 brand stills (label, path). Prefer transparent seal PNG."""
    seal_png = BRANDING_DIR / "cprp_official_seal.png"
    seal_jpg = BRANDING_DIR / "cprp_official_seal.jpg"
    seal_path = seal_png if seal_png.is_file() else seal_jpg
    suite = [
        ("Candlestick brand logo", BRANDING_DIR / "cprp_brand_logo_candlestick.jpg"),
        ("Support / Resistance brand logo", BRANDING_DIR / "cprp_brand_logo_support_resistance.jpg"),
        ("Minimal icon", BRANDING_DIR / "cprp_icon_minimal.jpg"),
        ("Horizontal banner", BRANDING_DIR / "cprp_banner_horizontal.jpg"),
        ("Official Seal", seal_path),
    ]
    return [(label, p) for label, p in suite if p.is_file()]


def list_official_brand_animated() -> list[tuple[str, Path]]:
    """Ordered official animated brand media (GIF preferred over MP4)."""
    pairs = [
        ("Candlestick logo (animated)", "cprp_brand_logo_candlestick_anim"),
        ("Support / Resistance logo (animated)", "cprp_brand_logo_support_resistance_anim"),
        ("Minimal icon (animated)", "cprp_icon_minimal_anim"),
        ("Horizontal banner (animated)", "cprp_banner_horizontal_anim"),
        ("Official Seal (animated)", "cprp_official_seal_anim"),
    ]
    out: list[tuple[str, Path]] = []
    for label, stem in pairs:
        gif = BRANDING_DIR / f"{stem}.gif"
        mp4 = BRANDING_DIR / f"{stem}.mp4"
        if gif.is_file():
            out.append((label, gif))
        elif mp4.is_file():
            out.append((label, mp4))
    return out


def list_branding_videos() -> list[Path]:
    """Return looping brand GIFs (preferred) plus any leftover MP4s."""
    if not BRANDING_DIR.is_dir():
        return []
    # Include logo / brand / seal / banner / icon animations
    keywords = ("logo", "brand", "seal", "banner", "icon", "anim")
    gifs = [
        p
        for p in BRANDING_DIR.iterdir()
        if p.suffix.lower() == ".gif"
        and p.is_file()
        and any(k in p.name.lower() for k in keywords)
    ]
    mp4s = [
        p
        for p in BRANDING_DIR.iterdir()
        if p.suffix.lower() == ".mp4" and p.is_file()
    ]
    # GIFs first
    return sorted(gifs, key=lambda p: p.name.lower()) + sorted(
        mp4s, key=lambda p: p.name.lower()
    )


if __name__ == "__main__":
    rep = sync_cprp_assets()
    print("=== CPRP asset sync ===")
    for line in rep.summary_lines():
        print(line.replace("**", ""))
    if rep.copied:
        print("\nCopied:")
        for c in rep.copied:
            print(" ", c)
    if rep.errors:
        print("\nErrors:")
        for e in rep.errors:
            print(" ", e)
