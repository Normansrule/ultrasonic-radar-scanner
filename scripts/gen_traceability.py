#!/usr/bin/env python3
"""Fill the Status column of docs/REQUIREMENTS.md from docs/VALIDATION.md and draw
hardware/diagrams/requirements_status.svg.

A requirement is "Met (recorded)" when every evidence ID is a recorded check (R-…) marked PASS,
"Verified" when every evidence ID passed (including physical T-… tests), otherwise "Open".

Usage: python scripts/gen_traceability.py [--check]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQ = ROOT / "docs" / "REQUIREMENTS.md"
VAL = ROOT / "docs" / "VALIDATION.md"
SVG = ROOT / "hardware" / "diagrams" / "requirements_status.svg"
FONT = "font-family:'DejaVu Sans',Helvetica,Arial,sans-serif"


def validation_results():
    res = {}
    for line in VAL.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| ((?:R|T)-[A-Z]+-\d+) \|", line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        status = cells[3] if m.group(1).startswith("T-") else cells[2]
        res[m.group(1)] = status.upper()
    return res


def rows(text):
    block = text.split("<!-- REQS:BEGIN -->")[1].split("<!-- REQS:END -->")[0]
    out = []
    for line in block.strip().splitlines()[2:]:
        out.append([c.strip() for c in line.strip("|").split("|")])
    return block, out


def status_for(evidence, res):
    ids = [e.strip() for e in evidence.split(",") if e.strip()]
    missing = [i for i in ids if i not in res]
    if missing:
        raise SystemExit(f"unknown validation IDs {missing}")
    if all(res[i] == "PASS" for i in ids):
        return "Verified" if any(i.startswith("T-") for i in ids) else "Met (recorded)"
    return "Open"


def svg(counts, total, groups):
    W, H = 900, 250
    colors = {"Verified": "#2f9e44", "Met (recorded)": "#74c69d", "Open": "#f59f00"}
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Requirement status">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         f'<text x="30" y="38" style="{FONT};font-size:20px;font-weight:bold" fill="#111">Requirements: {total} total</text>',
         f'<text x="30" y="60" style="{FONT};font-size:12.5px" fill="#555">Generated from docs/REQUIREMENTS.md + docs/VALIDATION.md by scripts/gen_traceability.py</text>']
    x, y, bw = 30, 80, W - 60
    for k in ("Verified", "Met (recorded)", "Open"):
        w = bw * counts.get(k, 0) / total
        if w:
            o.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="34" fill="{colors[k]}"/>')
            if w > 70:
                o.append(f'<text x="{x + 10:.1f}" y="{y + 22}" style="{FONT};font-size:13px;font-weight:bold" fill="#fff">{k}: {counts[k]}</text>')
        x += w
    gy = 150
    o.append(f'<text x="30" y="{gy - 10}" style="{FONT};font-size:12.5px;font-weight:bold" fill="#333">by group</text>')
    gx = 30
    gw = (W - 60) / len(groups)
    for g, (met, tot) in groups.items():
        o.append(f'<rect x="{gx:.1f}" y="{gy}" width="{gw - 10:.1f}" height="60" rx="8" fill="#f4f7f5" stroke="#dde5df"/>')
        o.append(f'<text x="{gx + 10:.1f}" y="{gy + 24}" style="{FONT};font-size:13px;font-weight:bold" fill="#1f3b2d">{g}</text>')
        o.append(f'<text x="{gx + 10:.1f}" y="{gy + 46}" style="{FONT};font-size:12.5px" fill="#555">{met}/{tot} met</text>')
        gx += gw
    o.append("</svg>\n")
    return "\n".join(o)


def main():
    res = validation_results()
    text = REQ.read_text(encoding="utf-8")
    block, rs = rows(text)
    lines = block.strip().splitlines()[:2]
    counts, groups = {}, {}
    names = {"F": "Functional", "P": "Performance", "S": "Safety", "I": "Interface", "M": "Mechanical",
             "SW": "Software", "O": "Open source"}
    for r in rs:
        r[4] = status_for(r[3], res)
        counts[r[4]] = counts.get(r[4], 0) + 1
        g = names[r[0].split("-")[1]]
        met, tot = groups.get(g, (0, 0))
        groups[g] = (met + (r[4] != "Open"), tot + 1)
        lines.append("| " + " | ".join(r) + " |")
    new = text.replace(block, "\n" + "\n".join(lines) + "\n")
    out_svg = svg(counts, len(rs), groups)
    if "--check" in sys.argv:
        ok = new == text and SVG.exists() and SVG.read_text() == out_svg
        print("traceability up to date" if ok else "stale - run: python scripts/gen_traceability.py")
        return 0 if ok else 1
    REQ.write_text(new, encoding="utf-8")
    SVG.write_text(out_svg, encoding="utf-8")
    print(f"{len(rs)} requirements: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
