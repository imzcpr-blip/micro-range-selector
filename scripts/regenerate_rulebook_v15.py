#!/usr/bin/env python3
"""Regenerate Official Rulebook v1.5 PDF with corrected grammar and S&P encoding."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PRIMARY = colors.HexColor("#0F172A")
ACCENT = colors.HexColor("#1E3A5F")
HIGHLIGHT = colors.HexColor("#2563EB")
LIGHT = colors.HexColor("#F1F5F9")
SLATE = colors.HexColor("#64748B")
WHITE = colors.white

APP_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = [
    APP_ROOT / "assets" / "CPRP_Official_Rulebook_v1.5.pdf",
    APP_ROOT / "assets" / "docs" / "CPRP_Official_Rulebook_v1.5.pdf",
    Path(r"C:\Users\imzcp\OneDrive\Desktop\CPRP Trading")
    / "Cooper_Precision_Reversion_Protocol_Official_Rulebook_v1.5.pdf",
]


def styles() -> dict:
    getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "T",
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            textColor=PRIMARY,
            spaceAfter=6,
        ),
        "Sub": ParagraphStyle(
            "S",
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            alignment=TA_CENTER,
            textColor=SLATE,
            spaceAfter=8,
        ),
        "H": ParagraphStyle(
            "H",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=ACCENT,
            spaceBefore=10,
            spaceAfter=5,
        ),
        "Body": ParagraphStyle(
            "B",
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            alignment=TA_JUSTIFY,
            textColor=PRIMARY,
            spaceAfter=5,
        ),
        "Bullet": ParagraphStyle(
            "Bu",
            fontName="Helvetica",
            fontSize=9.5,
            leading=12.5,
            leftIndent=12,
            textColor=PRIMARY,
            spaceAfter=2,
        ),
        "Foot": ParagraphStyle(
            "F",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=SLATE,
            spaceBefore=8,
        ),
        "Cell": ParagraphStyle(
            "C", fontName="Helvetica", fontSize=8.5, leading=11, textColor=PRIMARY
        ),
        "CellB": ParagraphStyle(
            "CB", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=PRIMARY
        ),
    }


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(SLATE)
    canvas.drawString(
        0.7 * inch,
        0.45 * inch,
        "Cooper Precision Reversion Protocol Official Rulebook v1.5",
    )
    canvas.drawRightString(
        letter[0] - 0.7 * inch,
        0.45 * inch,
        f"Page {doc.page} | Confidential – For Personal Use | © 2026 Raymon Michael Cooper",
    )
    canvas.restoreState()


def build_story(s: dict) -> list:
    story: list = [
        Paragraph("COOPER PRECISION<br/>REVERSION PROTOCOL", s["Title"]),
        Paragraph(
            "Official Strategy Rulebook<br/>Micro Futures Day Trading System", s["Sub"]
        ),
        Paragraph(
            "“Trade the boundaries. Respect the structure. Control the risk.”", s["Sub"]
        ),
        Spacer(1, 6),
        Paragraph(
            "<b>Strategy Name:</b> Cooper Precision Reversion Protocol (CPRP)<br/>"
            "<b>Creator / Owner:</b> Raymon Michael Cooper<br/>"
            "<b>Version:</b> 1.5 (Final) — Chart Pair Hierarchy Locked<br/>"
            "<b>Original Creation Date:</b> August 4, 2026<br/>"
            "<b>This Edition:</b> August 10, 2026<br/>"
            "<b>Primary Instruments:</b> MES (primary), MNQ, MYM<br/>"
            "<b>Style:</b> Intraday Range / Channel Reversion",
            s["Body"],
        ),
        Paragraph(
            "This document is the authoritative definition of the Cooper Precision Reversion Protocol. "
            "All trading decisions under this system must conform to the rules stated herein. "
            "Deviations void the integrity of the process and the performance record.",
            s["Body"],
        ),
        Paragraph("1. Strategy Overview", s["H"]),
        HRFlowable(width="100%", thickness=1, color=HIGHLIGHT, spaceBefore=0, spaceAfter=6),
        Paragraph(
            "The Cooper Precision Reversion Protocol is a structured, rules-based intraday trading system "
            "designed exclusively for Micro E-mini futures. It identifies confirmed Support and Resistance "
            "ranges or channels (both sideways and trending) and systematically fades the boundaries until "
            "the structure is broken.",
            s["Body"],
        ),
        Paragraph(
            "The protocol is directionally neutral: the same rules apply whether price is oscillating in a "
            "horizontal range or traveling inside a defined channel. The edge is derived from precise "
            "identification of structure, multi-factor confirmation, and absolute risk control.",
            s["Body"],
        ),
        Paragraph("<b>Core Philosophy</b>", s["Body"]),
        Paragraph("• Trade only confirmed structure — never anticipate.", s["Bullet"]),
        Paragraph(
            "• Fade the extremes of the range or channel until the structure fails.",
            s["Bullet"],
        ),
        Paragraph(
            "• Multi-timeframe alignment, volume, price action, and RSI must agree.",
            s["Bullet"],
        ),
        Paragraph(
            "• Hard dollar risk limit on every trade. No exceptions.", s["Bullet"]
        ),
        Paragraph(
            "• When structure breaks, step aside. Do not force trades.", s["Bullet"]
        ),
        Paragraph("2. Instruments &amp; Chart Setup", s["H"]),
        HRFlowable(width="100%", thickness=1, color=HIGHLIGHT, spaceBefore=0, spaceAfter=6),
        Paragraph("<b>Approved Instruments (Micro Futures Only)</b>", s["Body"]),
        Paragraph(
            "• <b>MES</b> — Micro E-mini S&amp;P 500 (Primary)", s["Bullet"]
        ),
        Paragraph("• <b>MNQ</b> — Micro E-mini Nasdaq-100", s["Bullet"]),
        Paragraph("• <b>MYM</b> — Micro E-mini Dow Jones", s["Bullet"]),
        Paragraph(
            "No other instruments are permitted under this protocol.", s["Body"]
        ),
        Paragraph("<b>Approved Chart Pairs (v1.5 Final)</b>", s["Body"]),
        Paragraph("Only the following two working pairs are approved:", s["Body"]),
        Paragraph(
            "• <b>15-minute (Structure) + 5-minute (Execution)</b> — Primary / default for most sessions. "
            "Cleaner RSI behavior, better range definition, and still-responsive entry timing.",
            s["Bullet"],
        ),
        Paragraph(
            "• <b>30-minute (Structure) + 15-minute (Execution)</b> — Preferred when ranges are larger, "
            "slower, or volume is lighter. Highest-quality S/R levels and least noise.",
            s["Bullet"],
        ),
        Paragraph(
            "No chart lower than the 5-minute is used for structure or execution. The former 5-minute + "
            "1-minute pair has been fully retired. Select the pair based on time of day, current volume, "
            "and the size of the developing range. The higher timeframe defines structure; the lower "
            "timeframe refines entry timing.",
            s["Body"],
        ),
        Paragraph(
            "<b>Static Higher Timeframe – Long-Term Trend Context</b>", s["Body"]
        ),
        Paragraph(
            "In addition to the active trading pair, maintain a static 1-Hour chart in a separate window "
            "at all times. The 1-Hour chart provides long-term trend context and higher-timeframe "
            "Support/Resistance levels.",
            s["Body"],
        ),
        Paragraph(
            "• Primary recommendation: 1-Hour (60-minute) chart as the static long-term trend reference.",
            s["Bullet"],
        ),
        Paragraph(
            "• Acceptable alternative: 4-Hour chart for broader bias when preferred.",
            s["Bullet"],
        ),
        Paragraph(
            "• The 1-Hour chart does not generate entries. It is used only for context, filtering, and "
            "situational awareness.",
            s["Bullet"],
        ),
        Paragraph(
            "• When the 1-Hour is cleanly trending, be more selective when fading against that trend "
            "inside the active range or channel.",
            s["Bullet"],
        ),
        Paragraph(
            "• When the 1-Hour is ranging or choppy, standard range-reversion setups on the active pair "
            "generally have higher quality.",
            s["Bullet"],
        ),
        Paragraph("3. Structure Definition – Ranges &amp; Channels", s["H"]),
        HRFlowable(width="100%", thickness=1, color=HIGHLIGHT, spaceBefore=0, spaceAfter=6),
        Paragraph(
            "A valid trading environment exists only when a clear Support/Resistance range or channel "
            "has been confirmed. Both horizontal ranges and sloping channels are valid.",
            s["Body"],
        ),
        Paragraph("<b>Confirmation Requirements for Structure</b>", s["Body"]),
        Paragraph(
            "• At least two clear touches (or near-touches) at both the upper and lower boundary.",
            s["Bullet"],
        ),
        Paragraph(
            "• Price action shows respect for the boundaries (rejection wicks, volume spikes, or clear turns).",
            s["Bullet"],
        ),
        Paragraph(
            "• The structure is visible and unambiguous on the higher timeframe of the chosen pair.",
            s["Bullet"],
        ),
        Paragraph(
            "• Trend or channel direction is noted but does not change the fade logic.",
            s["Bullet"],
        ),
        Paragraph(
            "Once structure is confirmed, the Protocol treats the upper boundary as Resistance (sell zone) "
            "and the lower boundary as Support (buy zone).",
            s["Body"],
        ),
        Paragraph("4. Entry Rules", s["H"]),
        HRFlowable(width="100%", thickness=1, color=HIGHLIGHT, spaceBefore=0, spaceAfter=6),
        Paragraph("<b>Long Entries (Buy Support)</b>", s["Body"]),
        Paragraph(
            "1. Price approaches or tags the confirmed lower boundary (Support).",
            s["Bullet"],
        ),
        Paragraph(
            "2. Price action shows rejection (wick, engulfing candle, or clear reversal candle on the "
            "lower timeframe).",
            s["Bullet"],
        ),
        Paragraph(
            "3. Volume supports the rejection or shows absorption.", s["Bullet"]
        ),
        Paragraph(
            "4. RSI is not in extreme overbought on the higher timeframe and preferably shows bullish "
            "divergence or is rising from oversold.",
            s["Bullet"],
        ),
        Paragraph(
            "5. All factors align → enter long with defined risk.", s["Bullet"]
        ),
        Paragraph("<b>Short Entries (Sell Resistance)</b>", s["Body"]),
        Paragraph(
            "1. Price approaches or tags the confirmed upper boundary (Resistance).",
            s["Bullet"],
        ),
        Paragraph(
            "2. Price action shows rejection at the boundary.", s["Bullet"]
        ),
        Paragraph("3. Volume supports the rejection.", s["Bullet"]),
        Paragraph(
            "4. RSI is not in extreme oversold on the higher timeframe and preferably shows bearish "
            "divergence or is falling from overbought.",
            s["Bullet"],
        ),
        Paragraph(
            "5. All factors align → enter short with defined risk.", s["Bullet"]
        ),
        Paragraph(
            "<b>Important:</b> Entries are taken only when the full confluence is present. If any required "
            "confirmation is missing, there is no trade.",
            s["Body"],
        ),
        Paragraph("<b>RSI Guidance (v1.5)</b>", s["Body"]),
        Paragraph(
            "RSI is secondary confirmation. Prefer divergence at the actual Support or Resistance level "
            "over absolute 70/30 extremes. On 15-minute and 30-minute charts, RSI extremes are useful as "
            "alerts or preparation signals only. If price is still mid-range when RSI reaches an extreme, "
            "do not enter — wait for price to reach a confirmed boundary with supporting price action and "
            "volume. Optional: a faster RSI period (7 or 9) may be displayed on the execution chart purely "
            "for divergence visualization. The structure chart retains the standard 14-period RSI.",
            s["Body"],
        ),
        Paragraph("5. Risk Management &amp; Exits", s["H"]),
        HRFlowable(width="100%", thickness=1, color=HIGHLIGHT, spaceBefore=0, spaceAfter=6),
        Paragraph("<b>Hard Risk Rule (Non-Negotiable)</b>", s["Body"]),
        Paragraph(
            "Every trade must have a hard maximum loss of <b>–$50 to –$100</b> per contract "
            "(or per position). Exit immediately if this threshold is reached. No averaging down. No “hope.”",
            s["Body"],
        ),
        Paragraph("<b>Profit Taking &amp; Trade Management</b>", s["Body"]),
        Paragraph(
            "• The primary target is the opposite boundary of the current range or channel.",
            s["Bullet"],
        ),
        Paragraph(
            "• Partial profits may be taken at logical intermediate levels or at the midpoint of the range.",
            s["Bullet"],
        ),
        Paragraph(
            "• Trail stops only after the trade has moved meaningfully in your favor and structure remains intact.",
            s["Bullet"],
        ),
        Paragraph(
            "• If the opposite boundary is reached with strength, consider a full exit or a scale-out.",
            s["Bullet"],
        ),
        Paragraph("<b>Structure Break Rule</b>", s["Body"]),
        Paragraph(
            "When price closes decisively beyond a confirmed boundary (Support or Resistance broken with "
            "conviction), the current structure is invalidated. Immediately:",
            s["Body"],
        ),
        Paragraph(
            "• Flatten any open position related to that structure (if it is not already stopped).",
            s["Bullet"],
        ),
        Paragraph(
            "• Pause all new trading for a minimum of <b>30 minutes</b> or until a new clear structure forms.",
            s["Bullet"],
        ),
        Paragraph(
            "• Do not force trades during the transition period.", s["Bullet"]
        ),
        Paragraph("6. Pre-Trade Confirmation Checklist", s["H"]),
        HRFlowable(width="100%", thickness=1, color=HIGHLIGHT, spaceBefore=0, spaceAfter=6),
        Paragraph(
            "Before every entry, verify each item. If any item fails, stand aside.",
            s["Body"],
        ),
    ]

    rows = [
        [
            Paragraph("<b>#</b>", s["CellB"]),
            Paragraph("<b>Confirmation Item</b>", s["CellB"]),
            Paragraph("<b>Status</b>", s["CellB"]),
        ],
        [
            Paragraph("1", s["Cell"]),
            Paragraph(
                "Clear, confirmed S/R range or channel on the higher timeframe",
                s["Cell"],
            ),
            Paragraph("☐", s["Cell"]),
        ],
        [
            Paragraph("2", s["Cell"]),
            Paragraph(
                "Price is at or near the boundary (Support for long / Resistance for short)",
                s["Cell"],
            ),
            Paragraph("☐", s["Cell"]),
        ],
        [
            Paragraph("3", s["Cell"]),
            Paragraph(
                "Price-action rejection is visible on the lower timeframe", s["Cell"]
            ),
            Paragraph("☐", s["Cell"]),
        ],
        [
            Paragraph("4", s["Cell"]),
            Paragraph(
                "Volume supports the rejection or absorption", s["Cell"]
            ),
            Paragraph("☐", s["Cell"]),
        ],
        [
            Paragraph("5", s["Cell"]),
            Paragraph(
                "RSI condition is favorable (not an opposing extreme; divergence preferred)",
                s["Cell"],
            ),
            Paragraph("☐", s["Cell"]),
        ],
        [
            Paragraph("6", s["Cell"]),
            Paragraph(
                "Hard-stop distance fits within the –$50 to –$100 risk limit",
                s["Cell"],
            ),
            Paragraph("☐", s["Cell"]),
        ],
        [
            Paragraph("7", s["Cell"]),
            Paragraph(
                "No recent structure break (or the 30-minute pause has completed)",
                s["Cell"],
            ),
            Paragraph("☐", s["Cell"]),
        ],
    ]
    t = Table(rows, colWidths=[0.4 * inch, 5.3 * inch, 0.7 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("BACKGROUND", (0, 1), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.6, ACCENT),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, SLATE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t)

    story.extend(
        [
            Paragraph("7. Operational Discipline", s["H"]),
            HRFlowable(
                width="100%", thickness=1, color=HIGHLIGHT, spaceBefore=0, spaceAfter=6
            ),
            Paragraph(
                "• Trade only during periods of reasonable liquidity for the chosen micro contract.",
                s["Bullet"],
            ),
            Paragraph(
                "• Prefer MES as the primary instrument; use MNQ or MYM only when conditions are clearly superior.",
                s["Bullet"],
            ),
            Paragraph(
                "• Maintain a complete trade journal for every execution (entry reason, checklist status, "
                "outcome, and lessons).",
                s["Bullet"],
            ),
            Paragraph(
                "• Review performance weekly against these rules. Strategy integrity takes priority over "
                "short-term P&amp;L.",
                s["Bullet"],
            ),
            Paragraph(
                "• Never increase risk beyond the hard dollar limit to “make up” losses.",
                s["Bullet"],
            ),
            Paragraph(
                "• The Protocol is complete as written. Additional indicators or discretionary overrides "
                "are not part of the system.",
                s["Bullet"],
            ),
            Paragraph("8. Version History", s["H"]),
            HRFlowable(
                width="100%", thickness=1, color=HIGHLIGHT, spaceBefore=0, spaceAfter=6
            ),
        ]
    )

    vrows = [
        [
            Paragraph("<b>Version</b>", s["CellB"]),
            Paragraph("<b>Date</b>", s["CellB"]),
            Paragraph("<b>Changes</b>", s["CellB"]),
        ],
        [
            Paragraph("1.0", s["Cell"]),
            Paragraph("Aug 4, 2026", s["Cell"]),
            Paragraph(
                "Initial formalization of Micro Range Reversion Strategy rules.",
                s["Cell"],
            ),
        ],
        [
            Paragraph("1.1", s["Cell"]),
            Paragraph("Aug 5, 2026", s["Cell"]),
            Paragraph(
                "Minor clarifications to structure confirmation and risk language.",
                s["Cell"],
            ),
        ],
        [
            Paragraph("1.2", s["Cell"]),
            Paragraph("Aug 8, 2026", s["Cell"]),
            Paragraph(
                "Official rename to Cooper Precision Reversion Protocol. Branding alignment.",
                s["Cell"],
            ),
        ],
        [
            Paragraph("1.3", s["Cell"]),
            Paragraph("Aug 9, 2026", s["Cell"]),
            Paragraph(
                "Added official guidance on a static 1-Hour chart for long-term trend context.",
                s["Cell"],
            ),
        ],
        [
            Paragraph("1.5", s["Cell"]),
            Paragraph("Aug 10, 2026", s["Cell"]),
            Paragraph(
                "Final chart-pair hierarchy locked (15m+5m default, 30m+15m secondary). 5m+1m pair fully "
                "retired. RSI clarified as secondary confirmation with mid-range alert rule. Grammar and "
                "wording polished for clarity.",
                s["Cell"],
            ),
        ],
    ]
    vt = Table(vrows, colWidths=[0.7 * inch, 1.1 * inch, 4.6 * inch])
    vt.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("BACKGROUND", (0, 1), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.6, ACCENT),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, SLATE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(vt)
    story.extend(
        [
            Spacer(1, 12),
            Paragraph(
                "<b>Disclaimer:</b> Futures trading involves substantial risk of loss and is not suitable "
                "for all investors. This rulebook defines a personal trading protocol. It does not constitute "
                "investment advice, a solicitation, or a recommendation. Past performance is not indicative "
                "of future results. The creator accepts no liability for trading decisions made by others "
                "using these rules.",
                s["Foot"],
            ),
            Paragraph("— End of Official Rulebook —", s["Foot"]),
            Paragraph(
                "Cooper Precision Reversion Protocol | Raymon Michael Cooper | 2026",
                s["Foot"],
            ),
        ]
    )
    return story


def main() -> None:
    s = styles()
    story = build_story(s)
    for path in OUTPUTS:
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(path),
            pagesize=letter,
            leftMargin=0.7 * inch,
            rightMargin=0.7 * inch,
            topMargin=0.6 * inch,
            bottomMargin=0.65 * inch,
        )
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        print(f"Wrote {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
