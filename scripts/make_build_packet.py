#!/usr/bin/env python3
"""
Make manufacturing/build_packet.pdf — a printable build traveller with tick boxes:
cover, safety, parts checklist, printed parts + plates, print settings, the
point-to-point wire list, flashing, staged assembly gates, the physical test
sheet and a sign-off. Everything is read from the repository (CSV exports,
VALIDATION.md, renders), so re-running keeps it in step with the docs.

Usage: python scripts/make_build_packet.py [--out manufacturing/build_packet.pdf]
Needs: reportlab (requirements-site.txt). SVG diagrams are rasterised with CairoSVG
when it is installed; otherwise the committed PNG copies in hardware/diagrams/png/ are used.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

ROOT = Path(__file__).resolve().parents[1]
MFG = ROOT / "manufacturing"
DIAG = ROOT / "hardware" / "diagrams"
PNG = DIAG / "png"
VERSION = json.loads((ROOT / "app" / "package.json").read_text())["version"]

pdfmetrics.registerFont(TTFont("DV", str(MFG / "fonts" / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVB", str(MFG / "fonts" / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DV", boldItalic="DVB")

GREEN = colors.HexColor("#1f9d55")
DEEP = colors.HexColor("#10331f")
AMBER = colors.HexColor("#b86e00")
LIGHT = colors.HexColor("#eef5f0")
LINE = colors.HexColor("#c9d4cd")
BOX = "☐"

S = {
    "h1": ParagraphStyle("h1", fontName="DVB", fontSize=22, leading=27, textColor=DEEP, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="DVB", fontSize=14.5, leading=19, textColor=DEEP, spaceBefore=6, spaceAfter=6),
    "h3": ParagraphStyle("h3", fontName="DVB", fontSize=11, leading=14, textColor=DEEP, spaceBefore=4, spaceAfter=3),
    "p": ParagraphStyle("p", fontName="DV", fontSize=9.2, leading=12.5, alignment=TA_LEFT),
    "small": ParagraphStyle("small", fontName="DV", fontSize=7.6, leading=9.6),
    "cell": ParagraphStyle("cell", fontName="DV", fontSize=7.8, leading=9.8),
    "cellb": ParagraphStyle("cellb", fontName="DVB", fontSize=7.8, leading=9.8),
    "warn": ParagraphStyle("warn", fontName="DV", fontSize=9, leading=12, textColor=colors.HexColor("#5c3400")),
}


def P(text, style="p"):
    return Paragraph(text, S[style])


def read_csv(name):
    with open(MFG / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def diagram(name: str) -> Path:
    """PNG for a diagram; rasterises the SVG with CairoSVG when available."""
    PNG.mkdir(parents=True, exist_ok=True)
    src = DIAG / f"{name}.svg"
    out = PNG / f"{name}.png"
    try:
        import cairosvg  # noqa: PLC0415
        cairosvg.svg2png(url=str(src), write_to=str(out), output_width=2000)
    except ImportError:
        if not out.exists():
            raise SystemExit(f"{out} missing and CairoSVG not installed - pip install CairoSVG")
    return out


def img(path: Path, width_mm: float):
    from PIL import Image as PILImage  # noqa: PLC0415
    with PILImage.open(path) as im:
        w, h = im.size
    return Image(str(path), width=width_mm * mm, height=width_mm * mm * h / w)


def table(data, widths, header=True, zebra=True, font=7.8):
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    st = [("FONT", (0, 0), (-1, -1), "DV", font), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("GRID", (0, 0), (-1, -1), 0.4, LINE), ("LEFTPADDING", (0, 0), (-1, -1), 3),
          ("RIGHTPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 2.2),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), DEEP), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
               ("FONT", (0, 0), (-1, 0), "DVB", font)]
    if zebra:
        for r in range(1, len(data)):
            if r % 2 == 0:
                st.append(("BACKGROUND", (0, r), (-1, r), LIGHT))
    t.setStyle(TableStyle(st))
    return t


def callout(text, color=AMBER):
    t = Table([[P(text, "warn")]], colWidths=[180 * mm])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, color), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff6e5")),
                           ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t


def physical_tests():
    rows = []
    for line in (ROOT / "docs" / "VALIDATION.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| (T-[A-Z]+-\d+) \| (.*?) \| (.*?) \|", line)
        if m:
            clean = lambda s: re.sub(r"[`*]", "", s)  # noqa: E731
            rows.append((m.group(1), clean(m.group(2)), clean(m.group(3))))
    return rows


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("DV", 7.5)
    canvas.setFillColor(colors.HexColor("#6b7a71"))
    canvas.drawString(15 * mm, 9 * mm, f"Ultrasonic Radar Scanner · Radar V6 build packet · release {VERSION} · "
                                       "educational sonar — not a safety device")
    canvas.drawRightString(195 * mm, 9 * mm, f"page {doc.page}")
    canvas.restoreState()


def build(out: Path):
    story = []
    # ------------------------------------------------------------------ cover
    story += [P("Ultrasonic Radar Scanner", "h1"),
              P(f"<b>Build packet</b> — Radar V6 “Mini” · repository release {VERSION} · generated {date.today().isoformat()}"),
              Spacer(1, 4 * mm), img(DIAG / "hero.png", 150), Spacer(1, 3 * mm),
              callout("<b>Honest scope.</b> An educational ultrasonic (sonar) instrument with a radar-<i>style</i> display — "
                      "not radio-frequency radar and not a safety, obstacle-avoidance or people-detection device. It sweeps "
                      "about 120°; the angle shown is the commanded servo position. At the time this packet was generated, "
                      "no unit had been printed, wired or powered — your build is part of the validation."),
              Spacer(1, 5 * mm)]
    info = [["Unit / serial", ""], ["Builder", ""], ["Start date", ""], ["Printer + filament", ""],
            ["Firmware (version / SHA-256)", ""], ["Notes", ""]]
    t = Table(info, colWidths=[55 * mm, 125 * mm], rowHeights=[9 * mm] * len(info))
    t.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "DV", 9), ("GRID", (0, 0), (-1, -1), 0.5, LINE),
                           ("BACKGROUND", (0, 0), (0, -1), LIGHT), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [t, PageBreak()]

    # ------------------------------------------------------------------ safety + overview
    story += [P("1 · Safety rules (read before wiring)", "h2")]
    for r in ["Wire only with USB <b>unplugged</b>. Check every wire against the list before plugging in.",
              "Use a <b>3.3 V-capable</b> sensor (RCWL-1601 / HC-SR04P). A 5 V-only HC-SR04 needs the 2.2 kΩ / 3.3 kΩ "
              "divider on ECHO (docs/WIRING.md, fallback).",
              "Measure <b>P1 VIN ≈ 5 V</b> with a multimeter before connecting the servo to it.",
              "Leave P1 TX/RX and P3 IO21/IO22 unconnected.",
              "Power from a charger or power bank rated ≥ 1 A. Unplug if anything gets hot or smells.",
              "Keep fingers and hair clear of the turning head; it is a toy-grade servo, not a guarded mechanism."]:
        story.append(P(f"{BOX}&nbsp;&nbsp;{r}"))
    story += [Spacer(1, 4 * mm), P("Build stages — each has a gate; record results before moving on", "h3"),
              img(diagram("build_flow"), 180), PageBreak()]

    # ------------------------------------------------------------------ parts
    story += [P("2 · Parts checklist", "h2"), img(diagram("bom_overview"), 180), Spacer(1, 3 * mm)]
    data = [["✓", "ID", "Qty", "Part", "Check before you buy"]]
    for b in read_csv("bom.csv"):
        data.append([BOX, b["id"], P(b["qty"], "cell"), P(b["part"], "cellb"), P(b["check_before_buying"], "cell")])
    story += [table(data, [6, 10, 16, 52, 96]), PageBreak()]

    # ------------------------------------------------------------------ printing
    story += [P("3 · Printed parts", "h2"),
              P("Files: <b>cad/3mf/</b> (Bambu A1 mini plates), <b>cad/stl/</b> (already in print orientation), "
                "<b>cad/step/</b> (editable). Print the fit coupon first and adjust any VERIFY value in "
                "cad/build_radar.py before the long prints. PLA, 0.20 mm layers, 3 walls, 15–20 % gyroid, "
                "<b>no supports</b>.")]
    data = [["✓", "Part", "Role", "Plate", "Print size (mm)", "PLA ≤ g", "Orientation"]]
    for p in read_csv("printed_parts.csv"):
        data.append([BOX, P(p["part"], "cellb"), P(p["role"], "cell"), p["plate"].replace("_fit_coupon", ""),
                     p["print_size_mm"], p["pla_g_upper_bound"], P(p["orientation"], "cell")])
    story += [table(data, [6, 33, 27, 12, 30, 14, 58]), Spacer(1, 3 * mm)]
    plates = Table([[img(DIAG / "plate_S1_fit_coupon.png", 57), img(DIAG / "plate_P1.png", 57), img(DIAG / "plate_P2.png", 57)]],
                   colWidths=[60 * mm] * 3)
    story += [plates]
    coupon = [["✓", "Coupon test", "Pass when", "Size chosen"],
              [BOX, "CYD pegs 2.8 / 2.9 / 3.0 mm", "board presses on and stays; no cracking", ""],
              [BOX, "Sensor can holes 16.0 / 16.2 / 16.4 mm", "cans press in and hold, PCB not stressed", ""],
              [BOX, "Servo screw pilots 1.6 / 1.8 / 2.0 mm", "the SG90 screw bites and holds without splitting", ""]]
    story += [Spacer(1, 3 * mm), KeepTogether([P("Fit coupon (stage 1)", "h3"), table(coupon, [6, 62, 80, 32])]), PageBreak()]

    # ------------------------------------------------------------------ wiring
    story += [P("4 · Wiring — point to point", "h2"),
              P("Cut, label and fit each wire, then tick it. Follow the <b>labels</b> on the modules, not wire colours. "
                "Seven wires; USB unplugged. Source of truth: docs/WIRING.md."),
              Spacer(1, 2 * mm)]
    data = [["✓", "Wire", "From", "To", "Net", "Notes"]]
    for w in read_csv("wire_list.csv"):
        data.append([BOX, w["wire"], P(w["from"], "cellb"), P(w["to"], "cellb"), w["net"], P(w["notes"], "cell")])
    story += [table(data, [6, 11, 34, 34, 24, 71]), Spacer(1, 3 * mm),
              callout("Not connected on purpose: P1 TX/RX (USB serial), P3 GND/IO22/IO21, and the CYD's SD card and "
                      "speaker. The servo plug and the cables often both end in female sockets — join them with "
                      "male-male pins."),
              Spacer(1, 3 * mm), img(diagram("wiring_picture"), 180), PageBreak()]

    # ------------------------------------------------------------------ firmware + assembly
    story += [P("5 · Firmware", "h2")]
    for r in ["Connect the CYD to the computer with a data-capable USB cable (sensor and servo may stay connected).",
              "EITHER open the web page → <b>Flash firmware</b> (Chrome/Edge) and install the release build, "
              "OR compile: <i>arduino-cli compile --upload --profile esp32-core3 -p &lt;port&gt; firmware/Radar_V6</i>.",
              "For assembly, first flash with <b>CENTER_ONLY = true</b> (servo holds 90°), then set it back to false.",
              "Splash shows “EDU SONAR … NOT a safety device”, then the green fan and the sweep."]:
        story.append(P(f"{BOX}&nbsp;&nbsp;{r}"))
    story += [Spacer(1, 3 * mm), P("6 · Assembly gates", "h2"), img(DIAG / "parts_labeled.png", 120)]
    gates = [("Stage 2 — bench (nothing printed yet)", ["P1 VIN ≈ 5 V measured with USB in",
                                                        "Grid, sweep and readings appear; touch −/+ changes range",
                                                        "Echo at 30 / 100 / 150 cm recorded",
                                                        "No resets when the servo starts (else add the capacitor)"]),
             ("Stage 3 — print", ["P1 shell and P2 bezel/base/head printed without supports",
                                  "Bezel slides into the shell grooves without forcing"]),
             ("Stage 4 — assemble", ["CYD pressed onto the bezel pegs, screen through the window",
                                     "Servo screwed under the roof with its own 2 screws",
                                     "CENTER_ONLY: horn pressed into the head foot, head facing the scan side",
                                     "Sensor cans pressed into the head; cable through the slot with slack",
                                     "Bezel slid in, base pressed in; USB socket reachable"]),
             ("Stage 5 — run", ["CENTER_ONLY = false; head sweeps 30°–150° without touching anything",
                                "Screen direction matches the head (else REVERSE_SERVO)",
                                "Roof ticks match the screen angle (CALIBRATE_SERVO)"])]
    for title, items in gates:
        story.append(KeepTogether([P(title, "h3")] + [P(f"{BOX}&nbsp;&nbsp;{i}") for i in items]))
    story += [PageBreak()]

    # ------------------------------------------------------------------ tests + sign-off
    story += [P("7 · Physical test sheet", "h2"),
              P("Copy results into docs/VALIDATION.md (or open a pull request) — that is how the design becomes validated.")]
    data = [["Test", "What", "Pass criterion", "Result", "Date / initials"]]
    for tid, what, crit in physical_tests():
        data.append([P(tid, "cellb"), P(what, "cell"), P(crit, "cell"), "", ""])
    story += [table(data, [17, 70, 50, 25, 18], zebra=False), Spacer(1, 4 * mm)]
    so = Table([["All gates passed and recorded", BOX], ["Labelled “educational — not a safety device”", BOX],
                ["Signature / date", ""]], colWidths=[120 * mm, 60 * mm], rowHeights=[9 * mm] * 3)
    so.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "DV", 9.5), ("GRID", (0, 0), (-1, -1), 0.5, LINE),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BACKGROUND", (0, 0), (0, -1), LIGHT)]))
    story.append(KeepTogether([P("Sign-off", "h3"), so]))

    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm,
                            bottomMargin=16 * mm, title="Ultrasonic Radar Scanner — build packet",
                            author="ultrasonic-radar-scanner", subject=f"Radar V6, release {VERSION}")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(MFG / "build_packet.pdf"))
    a = ap.parse_args()
    build(Path(a.out).resolve())
