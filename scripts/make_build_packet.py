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
    canvas.drawString(15 * mm, 9 * mm, f"Ultrasonic Radar Scanner · Radar V5.1 build packet · release {VERSION} · "
                                       "educational sonar — not a safety device")
    canvas.drawRightString(195 * mm, 9 * mm, f"page {doc.page}")
    canvas.restoreState()


def build(out: Path):
    story = []
    # ------------------------------------------------------------------ cover
    story += [P("Ultrasonic Radar Scanner", "h1"),
              P(f"<b>Build packet</b> — Radar V5.1 hardware baseline · repository release {VERSION} · generated {date.today().isoformat()}"),
              Spacer(1, 4 * mm), img(DIAG / "exploded_v5.png", 165), Spacer(1, 3 * mm),
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
    story += [P("1 · Safety rules (read before buying anything)", "h2")]
    for r in ["The <b>3 A fuse on the battery positive lead is mandatory</b>; fit it before anything else touches the cell.",
              "Never connect a bare cell to the ESP32 VIN or to the servo — only the charger module's 5 V output feeds the scanner.",
              "Never solder to the cell; never put two cells in series; use a <b>protected</b> 18650 (≥ 2.1 A charge, ≥ 3 A discharge).",
              "Secure the <b>holder</b>, not the cell; nothing sharp against the cell wrapping; heat-shrink every power joint.",
              "HC-SR04 ECHO (5 V) reaches GPIO26 <b>only</b> through the 2.2 kΩ / 3.3 kΩ divider.",
              "Unplug the whole ESP32 harness before connecting a programming cable; never USB and external 5 V together.",
              "Do not charge unattended while prototyping; stop if anything gets hot, smells, swells or hisses."]:
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
                "cad/build_radar_v5.py before the long prints. PLA, 0.20 mm layers, 3 walls, 15–20 % gyroid, "
                "<b>no supports</b>.")]
    data = [["✓", "Part", "Role", "Plate", "Print size (mm)", "PLA ≤ g", "Orientation"]]
    for p in read_csv("printed_parts.csv"):
        data.append([BOX, P(p["part"], "cellb"), P(p["role"], "cell"), p["plate"].replace("_optional_shim", ""),
                     p["print_size_mm"], p["pla_g_upper_bound"], P(p["orientation"], "cell")])
    story += [table(data, [6, 33, 27, 12, 30, 14, 58]), Spacer(1, 3 * mm)]
    plates = Table([[img(DIAG / "plate_S1_fit_coupon.png", 57), img(DIAG / "plate_P1.png", 57), img(DIAG / "plate_P2.png", 57)]],
                   colWidths=[60 * mm] * 3)
    story += [plates]
    coupon = [["✓", "Coupon test", "Pass when", "Size chosen"],
              [BOX, "Pilot holes 1.60 / 1.70 / 1.80 mm", "smallest that taps M2 cleanly and holds", ""],
              [BOX, "Clearance holes 2.15 / 2.25 / 2.35 mm", "smallest an M2 drops through", ""],
              [BOX, "Servo cut-out + flange pilots", "servo drops in, flange flat, holes align", ""],
              [BOX, "12 mm switch hole", "switch fits, nut tightens", ""],
              [BOX, "M2 nut pocket", "nut presses in and stays", ""]]
    story += [Spacer(1, 3 * mm), KeepTogether([P("Fit coupon (stage 1)", "h3"), table(coupon, [6, 62, 80, 32])]), PageBreak()]

    # ------------------------------------------------------------------ wiring
    story += [P("4 · Wiring — point to point", "h2"),
              P("Cut, label and fit each wire, then tick it. Follow the <b>labels</b> on the modules, not wire colours. "
                "Power wires first (stage 3, no ESP32), then signals (stage 4). Source of truth: docs/WIRING.md."),
              Spacer(1, 2 * mm)]
    data = [["✓", "Wire", "From", "To", "Net", "Wire type", "Notes"]]
    for w in read_csv("wire_list.csv"):
        data.append([BOX, w["wire"], P(w["from"], "cellb"), P(w["to"], "cellb"), w["net"], P(w["wire_type"], "cell"),
                     P(w["notes"], "cell")])
    story += [table(data, [6, 11, 32, 32, 22, 27, 50]), Spacer(1, 3 * mm),
              callout("Not in the list on purpose: the rear USB-C data lines (power only), the LCD's SD-card pins, and the "
                      "optional live-link tap (TX0 + GND to a 3.3 V adapter, adapter VCC unconnected — docs/LIVE_LINK.md)."),
              Spacer(1, 2 * mm), img(diagram("callout_echo_divider_fuse"), 150),
              PageBreak(), P("Wiring diagram", "h3"), img(diagram("wiring_full"), 180), PageBreak()]

    # ------------------------------------------------------------------ firmware + assembly
    story += [P("5 · Firmware", "h2")]
    for r in ["Switch OFF. Unplug J1 and every jumper from the ESP32 (the whole harness).",
              "Connect the ESP32's own USB data port to the computer.",
              "EITHER open the web app → <b>Flash firmware</b> (Chrome/Edge) and install the release build, "
              "OR compile: <i>arduino-cli compile --upload --profile esp32-core3 -p &lt;port&gt; firmware/Radar_V5</i>.",
              "Unplug the data cable. Re-connect the harness (J1 last), checking labels. Switch ON.",
              "Splash shows “EDU SONAR … NOT a safety device”, then the green fan and the sweep."]:
        story.append(P(f"{BOX}&nbsp;&nbsp;{r}"))
    story += [Spacer(1, 3 * mm), P("6 · Assembly gates", "h2")]
    gates = [("Stage 2 — servo-fit subset", ["Servo through the roof, flange flat, 2× M2×8",
                                              "Horn in hub with 2× M2×6; hub on spline with pointer at 90° (CENTER_ONLY)",
                                              "Keeper fitted with 2× M2×8; hub turns freely 30°–150°",
                                              "Axial play 0.2–0.6 mm (else 0.4 mm shim or change HUB_BOTTOM_ABOVE_ROOF)"]),
             ("Stage 3 — bench power (no ESP32)", ["No shorts with the cell out", "≈5 V at OUT_5V and LOAD_5V with switch ON",
                                                   "LOAD_5V = 0 V with switch OFF", "Charges from USB-C with switch OFF",
                                                   "OFF→ON restart after 5 s, 60 s, 10 min (open issue)"]),
             ("Stage 4 — flash + bench run", ["Display orientation/colours correct (else TFT_* settings)",
                                               "Sweep direction matches head (else REVERSE_SERVO)",
                                               "Echo at 30 / 100 / 150 cm recorded", "Travel calibrated, no buzzing at ends"]),
             ("Stage 5 — final assembly", ["LCD in locators, panel on with 4× M2×8", "ESP32, cell holder, USB-C, DFR1026 secured",
                                           "Sensor header-up, 4× M2×12; mast + M2×20 cross-bolt",
                                           "Sensor cable slack reaches 30° and 150° without tugging",
                                           "Roof on with 4× M2×8; rubber feet; rear label legible"])]
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
                            author="ultrasonic-radar-scanner", subject=f"Radar V5.1, release {VERSION}")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(MFG / "build_packet.pdf"))
    a = ap.parse_args()
    build(Path(a.out).resolve())
