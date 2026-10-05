#!/usr/bin/env python3
"""
Export the manufacturing data as spreadsheet-friendly CSV files and draw the
"what you need" picture — all generated from the documentation, so nothing is
typed twice:

  manufacturing/bom.csv            every purchased part (from docs/BOM.md)
  manufacturing/printed_parts.csv  every printed part, plate, size, PLA estimate (from cad/geometry_report.json)
  manufacturing/wiring_pins.csv    pin-by-pin net list (from docs/WIRING.md)
  manufacturing/wire_list.csv      the 7 wires W1-W7, one row per physical wire
  hardware/diagrams/bom_overview.svg   visual parts kit for the README

Usage: python scripts/export_mfg.py [--check]
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
MFG = ROOT / "manufacturing"
DIAG = ROOT / "hardware" / "diagrams"
FONT = "font-family:'DejaVu Sans',Helvetica,Arial,sans-serif"
PLA_G_PER_CM3 = 1.24

CATEGORY = {"E1": "Electronics", "E2": "Electronics", "E3": "Electronics",
            "E4": "Cables", "E5": "Cables", "E6": "Optional"}
STAGE = {"E1": 2, "E2": 2, "E3": 2, "E4": 2, "E5": 2, "E6": 5}


def plain(md: str) -> str:
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md)
    s = s.replace("**", "").replace("`", "")
    s = re.sub(r"(?<!\w)\*(\S[^*]*?)\*(?!\w)", r"\1", s)
    return s.strip()


def md_table(text: str, start_marker: str, end_marker: str | None = None):
    if end_marker:
        block = text.split(start_marker)[1].split(end_marker)[0]
    else:
        block = text.split(start_marker, 1)[1].split("\n## ", 1)[0]
    rows = [l for l in block.strip().splitlines() if l.startswith("|")]
    head = [c.strip() for c in rows[0].strip("|").split("|")]
    return [dict(zip(head, [c.strip() for c in r.strip("|").split("|")])) for r in rows[2:]]


def bom_rows():
    text = (ROOT / "docs" / "BOM.md").read_text(encoding="utf-8")
    out = []
    for r in md_table(text, "## Electronics"):
        rid = r["#"]
        out.append({"id": rid, "category": CATEGORY.get(rid, "Other"), "qty": plain(r["Qty"]).split(" ")[0],
                    "part": plain(r["Part"]), "check_before_buying": plain(r["What to check before you buy"]),
                    "reference_candidate": plain(r["Reference candidate"]), "est_usd": r["Est. US$"],
                    "needed_from_stage": STAGE.get(rid, ""), "optional": "yes" if "optional" in r["Qty"] else "no"})
    for i, r in enumerate(md_table(text, "<!-- FASTENERS:BEGIN -->", "<!-- FASTENERS:END -->"), start=1):
        out.append({"id": f"F{i}", "category": "Fasteners (included with the servo)", "qty": r["Qty"],
                    "part": plain(r["Item"]), "check_before_buying": plain(r["Used for"]),
                    "reference_candidate": "SG90 accessory bag", "est_usd": "0",
                    "needed_from_stage": 4, "optional": "yes" if "optional" in r["Item"] else "no"})
    return out


def wiring_rows():
    text = (ROOT / "docs" / "WIRING.md").read_text(encoding="utf-8")
    return md_table(text, "<!-- NETLIST:BEGIN -->", "<!-- NETLIST:END -->")


def wire_list(rows):
    """One row per physical wire (the Wire column of the NETLIST)."""
    wires: dict[str, list[dict]] = {}
    for r in rows:
        wires.setdefault(r["Wire"], []).append(r)
    out = []
    for w, ends in wires.items():
        a, b = ends
        out.append({"wire": w, "net": a["Net"], "kind": a["Kind"], "from": a["Pin"], "to": b["Pin"],
                    "notes": "; ".join(x for x in (plain(a["Notes"]), plain(b["Notes"])) if x), "done": ""})
    return out


def printed_rows():
    rep = json.loads((ROOT / "cad" / "geometry_report.json").read_text())
    plate_of = {}
    for pname, members in rep["plates"].items():
        for part in members:
            if pname in ("P1", "P2", "S1_fit_coupon"):
                plate_of[part] = pname
    out = []
    for part, info in rep["parts"].items():
        b = info["print_bbox"]
        cm3 = info["volume_mm3"] / 1000
        out.append({"part": part,
                    "role": "print first - test piece" if part.startswith("05") else "required",
                    "plate": plate_of.get(part, ""), "print_size_mm": f"{b['x']:.1f} x {b['y']:.1f} x {b['z']:.1f}",
                    "solid_volume_cm3": f"{cm3:.1f}", "pla_g_upper_bound": f"{cm3 * PLA_G_PER_CM3:.1f}",
                    "orientation": info["print_note"], "stl": f"cad/stl/{part}.stl", "step": f"cad/step/{part}.step"})
    return out


def to_csv(rows) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


# --------------------------------------------------------------------------- BOM picture
def icon(kind: str, x: float, y: float) -> str:
    g = [f'<g transform="translate({x},{y})">']
    if kind == "CYD":
        g += ['<rect x="0" y="0" width="150" height="104" rx="8" fill="#e8c22a" stroke="#a8840c" stroke-width="2"/>',
              '<rect x="10" y="10" width="118" height="84" rx="3" fill="#0b1a10"/>',
              '<path d="M69 86 L69 30" stroke="#2f9e44" stroke-width="1.5"/>',
              '<path d="M69 86 A 50 50 0 0 1 24 64" stroke="#2f9e44" stroke-width="1.2" fill="none"/>',
              '<path d="M69 86 A 50 50 0 0 0 114 64" stroke="#2f9e44" stroke-width="1.2" fill="none"/>',
              '<path d="M69 86 L 100 46 L 112 58 Z" fill="#69db7c" opacity="0.7"/>',
              '<rect x="134" y="40" width="12" height="22" rx="2" fill="#adb5bd"/>']
    elif kind == "SENSOR":
        g += ['<rect x="0" y="14" width="150" height="70" rx="6" fill="#1f63a8"/>',
              '<circle cx="38" cy="49" r="27" fill="#ced4da" stroke="#495057" stroke-width="2"/>',
              '<circle cx="38" cy="49" r="18" fill="#343a40"/>',
              '<circle cx="112" cy="49" r="27" fill="#ced4da" stroke="#495057" stroke-width="2"/>',
              '<circle cx="112" cy="49" r="18" fill="#343a40"/>',
              *[f'<rect x="{57 + i * 11}" y="84" width="4" height="14" fill="#adb5bd"/>' for i in range(4)]]
    elif kind == "SERVO":
        g += ['<rect x="30" y="30" width="90" height="62" rx="5" fill="#2a56b4"/>',
              '<rect x="14" y="44" width="122" height="10" rx="3" fill="#1c3f8f"/>',
              '<circle cx="95" cy="30" r="14" fill="#1c3f8f"/>',
              '<rect x="50" y="10" width="68" height="10" rx="5" fill="#f8f9fa" stroke="#adb5bd"/>',
              '<path d="M30 80 C 10 80, 10 96, 0 96" stroke="#e67700" stroke-width="3" fill="none"/>']
    elif kind == "CABLE":
        g += [*[f'<path d="M10 {30 + i * 8} C 60 {30 + i * 8}, 80 {60 + i * 8}, 140 {60 + i * 8}" stroke="{c}" '
                f'stroke-width="3" fill="none"/>' for i, c in enumerate(("#111", "#e03131", "#1c7ed6", "#2f9e44"))],
              '<rect x="0" y="22" width="16" height="36" rx="2" fill="#f8f9fa" stroke="#495057"/>',
              '<rect x="134" y="52" width="16" height="36" rx="2" fill="#212529"/>']
    elif kind == "PINS":
        g += [*[f'<rect x="{30 + i * 34}" y="20" width="10" height="62" rx="2" fill="#212529"/>'
                f'<rect x="{33 + i * 34}" y="6" width="4" height="90" fill="#ced4da"/>' for i in range(3)]]
    elif kind == "CAP":
        g += ['<rect x="50" y="10" width="50" height="70" rx="8" fill="#1c3f8f"/>',
              '<rect x="88" y="10" width="12" height="70" fill="#adb5bd"/>',
              '<rect x="62" y="80" width="3" height="18" fill="#adb5bd"/><rect x="84" y="80" width="3" height="18" fill="#adb5bd"/>']
    g.append("</g>")
    return "\n".join(g)


def price(e: str) -> str:
    e = e.strip()
    return f"< ${e[1:].strip()}" if e.startswith("<") else f"≈ ${e}"


def bom_svg(bom) -> str:
    cards = [("E1", "CYD", "CYD board", ["ESP32 + 2.8\" touch", "screen in one"]),
             ("E2", "SENSOR", "Sensor", ["RCWL-1601 or", "HC-SR04P (3.3 V)"]),
             ("E3", "SERVO", "SG90 servo", ["positional 180°,", "horn + 2 screws"]),
             ("E4", "CABLE", "Cables", ["JST 1.25 mm 4-pin", "→ Dupont female"]),
             ("E5", "PINS", "Jumper pins", ["male-male, join", "the servo plug"]),
             ("E6", "CAP", "Capacitor", ["470–1000 µF,", "optional"])]
    qty = {b["id"]: b["qty"] for b in bom}
    est = {b["id"]: b.get("est_usd", "") for b in bom}
    W, H = 1200, 360
    cw = (W - 60) / len(cards)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         'aria-label="Parts kit: five parts to buy, one optional">',
         f'<rect width="{W}" height="{H}" fill="#fbfaf7"/>',
         f'<text x="30" y="42" style="{FONT};font-size:24px;font-weight:bold" fill="#111">The whole kit — 5 parts to buy, '
         '1 optional</text>',
         f'<text x="30" y="68" style="{FONT};font-size:13px" fill="#555">Plus a USB cable, a ≥ 1 A charger and ≈ 120 g PLA. '
         'Prices are rough single-unit estimates (US$), not quotes. Generated from docs/BOM.md.</text>']
    for i, (rid, kind, name, sub) in enumerate(cards):
        x = 30 + i * cw
        opt = rid == "E6"
        dash = ' stroke-dasharray="6 5"'
        o.append(f'<rect x="{x}" y="90" width="{cw - 14}" height="250" rx="14" fill="#fff" stroke="{"#ced4da" if opt else "#cfe8d6"}" '
                 f'stroke-width="1.6"{dash if opt else ""}/>')
        o.append(icon(kind, x + (cw - 14) / 2 - 75, 112))
        o.append(f'<text x="{x + 14}" y="256" style="{FONT};font-size:15px;font-weight:bold" fill="#1f3b2d">'
                 f'<tspan fill="#2f9e44">{escape(qty.get(rid, "1"))}×</tspan> {escape(name)}</text>')
        for j, line in enumerate(sub):
            o.append(f'<text x="{x + 14}" y="{278 + j * 17}" style="{FONT};font-size:12px" fill="#555">{escape(line)}</text>')
        o.append(f'<text x="{x + 14}" y="326" style="{FONT};font-size:12.5px;font-weight:bold" fill="#868e96">'
                 f'{rid} · {escape(price(est.get(rid, "")))}</text>')
    o.append("</svg>\n")
    return "\n".join(o)


def main():
    outputs = {
        MFG / "bom.csv": to_csv(bom_rows()),
        MFG / "printed_parts.csv": to_csv(printed_rows()),
        MFG / "wiring_pins.csv": to_csv([{k.lower(): plain(v) for k, v in r.items()} for r in wiring_rows()]),
        MFG / "wire_list.csv": to_csv(wire_list(wiring_rows())),
        DIAG / "bom_overview.svg": bom_svg(bom_rows()),
    }
    if "--check" in sys.argv:
        stale = [str(p.relative_to(ROOT)) for p, t in outputs.items() if not p.exists() or p.read_text(encoding="utf-8") != t]
        print("manufacturing exports up to date" if not stale else f"stale: {stale} - run python scripts/export_mfg.py")
        return 1 if stale else 0
    MFG.mkdir(exist_ok=True)
    for p, t in outputs.items():
        p.write_text(t, encoding="utf-8")
    print("wrote " + ", ".join(str(p.relative_to(ROOT)) for p in outputs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
