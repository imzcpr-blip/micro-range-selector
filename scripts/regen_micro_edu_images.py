"""Regenerate Micro E-mini education images with correct CME $/point values."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
EDU = ROOT / "assets" / "education"


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    for p in (
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_ticks() -> Path:
    out = EDU / "micro_tick_values.png"
    w, h = 1200, 720
    bg, card, gold = (10, 22, 40), (15, 27, 45), (201, 168, 76)
    text, muted = (232, 237, 245), (139, 155, 180)
    green, blue, orange = (74, 222, 128), (96, 165, 250), (251, 146, 60)

    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    f_title, f_sub = font(36, True), font(18, False)
    f_head, f_row, f_cell = font(20, True), font(22, True), font(22, False)
    f_note, f_foot = font(16, False), font(14, False)

    d.rounded_rectangle([40, 40, w - 40, h - 40], radius=24, fill=card, outline=gold, width=3)
    d.text((80, 70), "Micro E-mini Contract Specs (CME)", fill=gold, font=f_title)
    d.text(
        (80, 120),
        "CPRP approved instruments only  |  Source: CME Group / Ironbeam contract specs",
        fill=muted,
        font=f_sub,
    )

    headers = ["Symbol", "Index", "$ / Point", "Min Tick", "Tick Value"]
    cols_x = [80, 220, 480, 700, 920]
    y0 = 190
    for x, hdr in zip(cols_x, headers):
        d.text((x, y0), hdr, fill=gold, font=f_head)
    d.line([(70, y0 + 40), (w - 70, y0 + 40)], fill=(60, 70, 90), width=2)

    rows = [
        ("MES", "S&P 500", "$5.00", "0.25 pt", "$1.25", green),
        ("MNQ", "Nasdaq-100", "$2.00", "0.25 pt", "$0.50", blue),
        ("MYM", "Dow Jones", "$0.50", "1.00 pt", "$0.50", orange),
    ]
    for i, (sym, idx, pt, tick, tv, col) in enumerate(rows):
        y = y0 + 70 + i * 70
        d.text((cols_x[0], y), sym, fill=col, font=f_row)
        d.text((cols_x[1], y), idx, fill=text, font=f_cell)
        d.text((cols_x[2], y), pt, fill=text, font=f_cell)
        d.text((cols_x[3], y), tick, fill=text, font=f_cell)
        d.text((cols_x[4], y), tv, fill=text, font=f_cell)

    notes_y = 480
    d.text((80, notes_y), "Tick value = min tick size x dollars per point", fill=muted, font=f_note)
    d.text(
        (80, notes_y + 32),
        "MES: 0.25 x $5.00 = $1.25/tick   |   MNQ: 0.25 x $2.00 = $0.50/tick   |   MYM: 1.0 x $0.50 = $0.50/tick",
        fill=text,
        font=f_note,
    )
    d.text(
        (80, notes_y + 70),
        "Always verify live contract specs with your broker and CME before trading.",
        fill=muted,
        font=f_note,
    )
    d.text(
        (80, notes_y + 110),
        "Educational reference. Specs can change. Not financial advice.  (c) CPRP Strategies",
        fill=muted,
        font=f_foot,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    return out


def draw_sizing() -> Path:
    out = EDU / "micro_position_sizing.png"
    w, h = 1200, 760
    bg, card, gold = (10, 22, 40), (15, 27, 45), (201, 168, 76)
    text, muted = (232, 237, 245), (139, 155, 180)
    green, blue, orange = (74, 222, 128), (96, 165, 250), (251, 146, 60)
    red = (248, 113, 113)

    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    f_title, f_sub = font(34, True), font(17, False)
    f_head, f_row, f_cell = font(18, True), font(22, True), font(20, False)
    f_note, f_foot, f_formula = font(16, False), font(14, False), font(18, True)

    d.rounded_rectangle([40, 40, w - 40, h - 40], radius=24, fill=card, outline=red, width=3)
    d.text((80, 70), "CPRP Position Sizing vs Hard Stop", fill=red, font=f_title)
    d.text(
        (80, 118),
        "Hard risk: max loss -$50 to -$100 per trade  |  1 micro contract baseline",
        fill=muted,
        font=f_sub,
    )
    d.rounded_rectangle([80, 160, w - 80, 220], radius=12, fill=(20, 32, 52), outline=gold, width=1)
    d.text(
        (100, 178),
        "Stop distance (points)  =  Hard stop ($)  /  $ per point",
        fill=gold,
        font=f_formula,
    )

    headers = ["Symbol", "$ / Point", "Stop @ $50", "Stop @ $75", "Stop @ $100", "Tick $"]
    cols_x = [80, 220, 380, 560, 760, 980]
    y0 = 250
    for x, hdr in zip(cols_x, headers):
        d.text((x, y0), hdr, fill=gold, font=f_head)
    d.line([(70, y0 + 36), (w - 70, y0 + 36)], fill=(60, 70, 90), width=2)

    rows = [
        ("MES", "$5.00", "10.0 pts", "15.0 pts", "20.0 pts", "$1.25", green),
        ("MNQ", "$2.00", "25.0 pts", "37.5 pts", "50.0 pts", "$0.50", blue),
        ("MYM", "$0.50", "100 pts", "150 pts", "200 pts", "$0.50", orange),
    ]
    for i, (sym, pt, s50, s75, s100, tv, col) in enumerate(rows):
        y = y0 + 60 + i * 62
        d.text((cols_x[0], y), sym, fill=col, font=f_row)
        d.text((cols_x[1], y), pt, fill=text, font=f_cell)
        d.text((cols_x[2], y), s50, fill=text, font=f_cell)
        d.text((cols_x[3], y), s75, fill=text, font=f_cell)
        d.text((cols_x[4], y), s100, fill=text, font=f_cell)
        d.text((cols_x[5], y), tv, fill=text, font=f_cell)

    ny = 520
    bullets = [
        "If structure stop would exceed -$100, stand aside or wait for tighter structure — do not enlarge risk.",
        "Prefer MES when uncertain: fewer points of room needed per dollar of risk ($5/pt vs $2/pt vs $0.50/pt).",
        "Never average down. Exit at the hard limit. Protocol risk is non-negotiable.",
    ]
    for i, b in enumerate(bullets):
        d.text((80, ny + i * 36), "-  " + b, fill=text, font=f_note)

    d.text(
        (80, 680),
        "Educational sizing guide for CPRP. Verify with your broker / CME. Not financial advice.  (c) CPRP Strategies",
        fill=muted,
        font=f_foot,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    return out


if __name__ == "__main__":
    a = draw_ticks()
    b = draw_sizing()
    print("Wrote", a, a.stat().st_size)
    print("Wrote", b, b.stat().st_size)
