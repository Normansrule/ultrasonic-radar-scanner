#!/usr/bin/env python3
"""
Export the manufacturing data as spreadsheet-friendly CSV files and draw the
"what you need" picture — all generated from the documentation, so nothing is
typed twice:

  manufacturing/bom.csv            every purchased part + fastener (from docs/BOM.md)
  manufacturing/printed_parts.csv  every printed part, plate, size, PLA estimate (from cad/geometry_report.json)
  manufacturing/wiring_pins.csv    pin-by-pin net list (from docs/WIRING.md)
  manufacturing/wire_list.csv      point-to-point wires W01…, one row per physical wire to cut and fit
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

CATEGORY = {
    **{f"E{i}": "Electronics" for i in (1, 2, 3, 4)},
    **{f"E{i}": "Power and protection" for i in (5, 6, 7, 8, 9, 10, 11)},
    "E12": "Passive parts", "E13": "Passive parts",
    "E14": "Wiring and mounting", "E15": "Wiring and mounting", "E16": "Wiring and mounting",
    "E17": "Cables", "E18": "Cables", "E19": "Consumables", "E20": "Optional (live link)",
}
STAGE = {"E1": 4, "E2": 5, "E3": 2, "E4": 5, "E5": 3, "E6": 3, "E7": 3, "E8": 3, "E9": 3, "E10": 3,
         "E11": 3, "E12": 4, "E13": 4, "E14": 3, "E15": 4, "E16": 5, "E17": 3, "E18": 4, "E19": 1, "E20": 5}


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
        out.append({"id": rid, "category": CATEGORY.get(rid, "Other"), "qty": plain(r["Qty"]),
                    "part": plain(r["Part"]), "check_before_buying": plain(r["What to check before you buy"]),
                    "reference_candidate": plain(r["Reference candidate"]),
                    "needed_from_stage": STAGE.get(rid, ""), "optional": "yes" if "optional" in r["Qty"] else "no"})
    for i, r in enumerate(md_table(text, "<!-- FASTENERS:BEGIN -->", "<!-- FASTENERS:END -->"), start=1):
        out.append({"id": f"F{i}", "category": "Fasteners (M2 only)", "qty": r["Qty"], "part": plain(r["Item"]),
                    "check_before_buying": plain(r["Used for"]), "reference_candidate": "ISO metric M2",
                    "needed_from_stage": 2, "optional": "no"})
    return out


def wiring_rows():
    text = (ROOT / "docs" / "WIRING.md").read_text(encoding="utf-8")
    return md_table(text, "<!-- NETLIST:BEGIN -->", "<!-- NETLIST:END -->")


def wire_list(rows):
    """Star wiring from the first pin listed on each net (matches WIRING.md's star points)."""
    nets: dict[str, list[dict]] = {}
    for r in rows:
        nets.setdefault(r["Net"], []).append(r)
    wires, n = [], 0
    for net, members in nets.items():
        src = members[0]
        for dst in members[1:]:
            n += 1
            a, b = src["Wire"], dst["Wire"]
            if a == "leads" and b == "leads":
                kind = "component leads"
            elif "leads" in (a, b):
                kind = f"{b if a == 'leads' else a} to component lead"
            else:
                kind = b or a
            wires.append({"wire": f"W{n:02d}", "net": net, "kind": src["Kind"], "from": src["Pin"], "to": dst["Pin"],
                          "wire_type": kind, "notes": plain(dst["Notes"]), "done": ""})
    return wires


def printed_rows():
    rep = json.loads((ROOT / "cad" / "geometry_report.json").read_text())
    plate_of = {}
    for pname, members in rep["plates"].items():
        for part in members:
            if pname in ("P1", "P2", "P3_optional_shim"):
                plate_of[part] = pname
    out = []
    for part, info in rep["parts"].items():
        b = info["print_bbox"]
        cm3 = info["volume_mm3"] / 1000
        out.append({"part": part,
                    "role": "optional" if part.startswith("07") else ("print first - test piece" if part.startswith("08") else "required"),
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
    if kind == "Electronics":
        g += ['<rect x="4" y="10" width="44" height="30" rx="3" fill="#1c6f3a"/>',
              *[f'<rect x="{8 + i * 8}" y="4" width="3" height="8" fill="#adb5bd"/>' for i in range(5)],
              *[f'<rect x="{8 + i * 8}" y="38" width="3" height="8" fill="#adb5bd"/>' for i in range(5)],
              '<rect x="16" y="17" width="20" height="16" rx="2" fill="#0d2a18"/>']
    elif kind == "Power and protection":
        g += ['<rect x="4" y="14" width="40" height="22" rx="9" fill="#3b82c4"/>',
              '<rect x="44" y="20" width="5" height="10" rx="1" fill="#868e96"/>',
              '<path d="M24 16 L18 26 H25 L21 35 L31 23 H24 Z" fill="#ffd43b"/>']
    elif kind == "Passive parts":
        g += ['<line x1="2" y1="25" x2="50" y2="25" stroke="#adb5bd" stroke-width="2"/>',
              '<rect x="12" y="18" width="28" height="14" rx="6" fill="#e2c38c"/>',
              '<rect x="17" y="18" width="3" height="14" fill="#d11f1f"/><rect x="23" y="18" width="3" height="14" fill="#d11f1f"/>',
              '<rect x="29" y="18" width="3" height="14" fill="#111"/>']
    elif kind == "Wiring and mounting":
        g += ['<path d="M4 34 C 16 6, 30 46, 48 14" stroke="#e03131" stroke-width="3.5" fill="none"/>',
              '<path d="M4 40 C 18 14, 32 52, 48 22" stroke="#111" stroke-width="3.5" fill="none"/>']
    elif kind == "Cables":
        g += ['<rect x="6" y="16" width="18" height="14" rx="3" fill="#495057"/>',
              '<path d="M24 23 C 34 23, 34 36, 46 36" stroke="#495057" stroke-width="4" fill="none"/>']
    elif kind == "Consumables":
        g += ['<circle cx="26" cy="25" r="19" fill="#2f9e44"/><circle cx="26" cy="25" r="7" fill="#fff"/>']
    elif kind.startswith("Fasteners"):
        g += ['<rect x="10" y="8" width="18" height="8" rx="2" fill="#868e96"/>',
              '<rect x="16" y="16" width="6" height="28" fill="#adb5bd"/>',
              *[f'<line x1="15" y1="{20 + i * 5}" x2="23" y2="{18 + i * 5}" stroke="#6c757d" stroke-width="1.2"/>' for i in range(5)],
              '<polygon points="34,20 42,15 50,20 50,30 42,35 34,30" fill="#868e96"/><circle cx="42" cy="25" r="3.5" fill="#fff"/>']
    else:
        g += ['<rect x="6" y="10" width="40" height="30" rx="6" fill="#ced4da"/>']
    g.append("</g>")
    return "\n".join(g)


def bom_svg(bom) -> str:
    order = ["Electronics", "Power and protection", "Passive parts", "Wiring and mounting", "Cables",
             "Consumables", "Fasteners (M2 only)", "Optional (live link)"]
    groups = {k: [b for b in bom if b["category"] == k] for k in order}
    W, colw, rowh, top = 1200, 290, 22, 110
    cols = 4
    heights = []
    for k in order:
        heights.append(70 + rowh * len(groups[k]))
    rows_of = [heights[i:i + cols] for i in range(0, len(order), cols)]
    H = top + sum(max(r) + 24 for r in rows_of) + 40
    short = {
        "E1": "ESP32-WROOM-32 DevKit, 30-pin", "E2": "HC-SR04 ultrasonic sensor", "E3": "SG90 positional servo + horn",
        "E4": "1.8\" ST7735S LCD (Waveshare)", "E5": "DFRobot DFR1026 charger/boost", "E6": "USB-C breakout, 5.1 kΩ CC×2",
        "E7": "Protected 18650 cell", "E8": "18650 holder with leads", "E9": "12 mm latching switch ≥2 A",
        "E10": "3 A fuse + inline holder", "E11": "1000 µF ≥10 V capacitor", "E12": "2.2 kΩ 1 % resistor",
        "E13": "3.3 kΩ 1 % resistor", "E14": "jumper leads + 22 AWG wire", "E15": "Keyed 2-pin plug (J1)",
        "E16": "Heat-shrink, tape, ties, feet", "E17": "5 V 3 A USB-C supply + cable", "E18": "USB data cable (ESP32)",
        "E19": "PLA filament", "E20": "3.3 V USB-serial adapter",
    }
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         'aria-label="Parts kit overview">',
         f'<rect width="{W}" height="{H}" fill="#fbfaf7"/>',
         f'<text x="30" y="42" style="{FONT};font-size:24px;font-weight:bold" fill="#111">What you need — the parts kit</text>',
         f'<text x="30" y="68" style="{FONT};font-size:13px" fill="#555">Generated from docs/BOM.md by scripts/export_mfg.py · '
         'quantities in brackets · full details and checks in manufacturing/bom.csv</text>']
    y = top - 20
    i = 0
    for r in rows_of:
        x = 30
        for h in r:
            k = order[i]
            items = groups[k]
            o.append(f'<rect x="{x}" y="{y}" width="{colw - 16}" height="{h}" rx="12" fill="#fff" stroke="#e1e6e2"/>')
            o.append(icon(k, x + 12, y + 8))
            o.append(f'<text x="{x + 72}" y="{y + 37}" style="{FONT};font-size:14.5px;font-weight:bold" fill="#1f3b2d">{escape(k)}</text>')
            for j, b in enumerate(items):
                label = short.get(b["id"], b["part"])
                q = b["qty"].replace("(optional)", "").strip()
                o.append(f'<text x="{x + 16}" y="{y + 78 + j * rowh}" style="{FONT};font-size:12.5px" fill="#222">'
                         f'<tspan fill="#2f9e44" font-weight="bold">[{escape(q)}]</tspan> {escape(label)}</text>')
            x += colw
            i += 1
        y += max(r) + 24
    o.append(f'<text x="30" y="{H - 18}" style="{FONT};font-size:12px" fill="#888">Plus the six printed parts and the fit coupon '
             '(manufacturing/printed_parts.csv). Recheck every listing before buying; safety parts are not optional.</text>')
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
