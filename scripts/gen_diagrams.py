#!/usr/bin/env python3
"""
Generate the documentation diagrams. Every picture here is derived from a
source file in the repo, so it cannot silently drift:

  hardware/diagrams/wiring_full.svg     } from the NETLIST table in docs/WIRING.md
  hardware/diagrams/wiring_power.svg    }
  hardware/diagrams/wiring_signal.svg   }
  hardware/diagrams/callout_echo_divider_fuse.svg   illustrated callout (values from WIRING.md)
  hardware/diagrams/build_flow.svg      build-stage gate diagram
  docs/img/eq_*.svg                     equation figures (numbers from tests/radar_math.py)

Usage: python scripts/gen_diagrams.py [--wiring-only]
"""
from __future__ import annotations

import re
import sys
from collections import OrderedDict
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import radar_math as rm  # noqa: E402

DIAG = ROOT / "hardware" / "diagrams"
IMG = ROOT / "docs" / "img"
FONT = "font-family:'DejaVu Sans',Helvetica,Arial,sans-serif"


# =========================================================================== netlist
def parse_table(md: str, tag: str):
    block = md.split(f"<!-- {tag}:BEGIN -->")[1].split(f"<!-- {tag}:END -->")[0]
    rows = [l.strip() for l in block.strip().splitlines() if l.strip().startswith("|")]
    head = [c.strip() for c in rows[0].strip("|").split("|")]
    out = []
    for r in rows[2:]:
        cells = [c.strip() for c in r.strip("|").split("|")]
        out.append(dict(zip(head, cells)))
    return out


def load_netlist():
    return parse_table((ROOT / "docs" / "WIRING.md").read_text(encoding="utf-8"), "NETLIST")


NET_COLORS = {
    "USB_5V": "#e8590c", "USB_GND": "#5c636a", "BAT_RAW": "#b02a2a", "BAT_POS": "#e03131",
    "BAT_NEG": "#343a40", "OUT_5V": "#f08c00", "LOAD_5V": "#d6336c", "GND": "#111418",
    "3V3": "#7048e8", "TRIG": "#1c7ed6", "ECHO_5V": "#e67700", "ECHO_3V": "#2f9e44",
    "SERVO_PWM": "#0c8599", "TFT_MOSI": "#1971c2", "TFT_SCK": "#5f3dc4", "TFT_CS": "#087f5b",
    "TFT_DC": "#9c36b5", "TFT_RST": "#a61e4d",
}
LEFT = ["USBC", "DFR1026", "CELL", "FUSE", "SW", "C1"]
RIGHT = ["ESP32", "SR04", "R1", "R2", "SERVO", "LCD"]
TITLES = {
    "USBC": "USB-C input breakout", "DFR1026": "DFR1026 charger/boost", "CELL": "18650 cell (protected)",
    "FUSE": "3 A inline fuse", "SW": "Latching switch", "C1": "C1 1000 µF",
    "ESP32": "ESP32-WROOM-32 DevKit", "SR04": "HC-SR04", "R1": "R1 2.2 kΩ", "R2": "R2 3.3 kΩ",
    "SERVO": "SG90-size servo", "LCD": "ST7735S 1.8\" LCD",
}
NET_ORDER = ["USB_5V", "USB_GND", "BAT_RAW", "BAT_POS", "BAT_NEG", "OUT_5V", "LOAD_5V", "GND", "3V3",
             "ECHO_5V", "ECHO_3V", "TRIG", "SERVO_PWM", "TFT_MOSI", "TFT_SCK", "TFT_CS", "TFT_DC", "TFT_RST"]


def wiring_svg(rows, title, subtitle):
    comps = OrderedDict()
    for r in rows:
        c, pin = r["Pin"].split(".", 1)
        comps.setdefault(c, [])
        if pin not in comps[c]:
            comps[c].append(pin)
    nets = [n for n in NET_ORDER if any(r["Net"] == n for r in rows)]
    nets += sorted({r["Net"] for r in rows} - set(nets))

    BW, PH, HH, GAP = 212, 21, 30, 16
    mx_left, top = 30, 170
    bus_x0 = mx_left + BW + 46
    bus_dx = 26
    bus_x = {n: bus_x0 + i * bus_dx for i, n in enumerate(nets)}
    right_x = bus_x0 + (len(nets) - 1) * bus_dx + 46
    W = right_x + BW + 30

    pin_pos = {}
    boxes = []
    for side, order, x in (("L", LEFT, mx_left), ("R", RIGHT, right_x)):
        y = top
        for c in order:
            if c not in comps:
                continue
            pins = comps[c]
            h = HH + PH * len(pins) + 6
            boxes.append((c, x, y, h, side, pins))
            for i, p in enumerate(pins):
                py = y + HH + PH * i + PH / 2 + 2
                px = x + BW if side == "L" else x
                pin_pos[f"{c}.{p}"] = (px, py, side)
            y += h + GAP
    H = max(b[2] + b[3] for b in boxes) + 70

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="{escape(title)}">',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         f'<text x="30" y="40" style="{FONT};font-size:22px;font-weight:bold" fill="#111">{escape(title)}</text>',
         f'<text x="30" y="64" style="{FONT};font-size:13px" fill="#555">{escape(subtitle)}</text>']
    # buses
    for n in nets:
        ys = [pin_pos[r["Pin"]][1] for r in rows if r["Net"] == n]
        x = bus_x[n]
        col = NET_COLORS.get(n, "#444")
        o.append(f'<g class="net" data-net="{n}">')
        o.append(f'<line x1="{x}" y1="{min(ys) - 8}" x2="{x}" y2="{max(ys) + 8}" stroke="{col}" stroke-width="3.2" '
                 'stroke-linecap="round"/>')
        o.append(f'<text transform="translate({x + 4},{top - 12}) rotate(-60)" style="{FONT};font-size:11px;'
                 f'font-weight:bold" fill="{col}">{escape(n)}</text>')
        o.append(f'<line x1="{x}" y1="{top - 8}" x2="{x}" y2="{min(ys) - 8}" stroke="{col}" stroke-width="1" '
                 'stroke-dasharray="2 3" opacity="0.5"/>')
        o.append("</g>")
    # pin stubs
    for r in rows:
        px, py, side = pin_pos[r["Pin"]]
        x = bus_x[r["Net"]]
        col = NET_COLORS.get(r["Net"], "#444")
        o.append(f'<g class="net" data-net="{r["Net"]}" data-row="{r["ID"]}">')
        o.append(f'<title>{escape(r["ID"] + " " + r["Pin"] + " → " + r["Net"] + (" — " + r["Notes"] if r["Notes"] else ""))}</title>')
        o.append(f'<line x1="{px}" y1="{py}" x2="{x}" y2="{py}" stroke="{col}" stroke-width="2"/>')
        o.append(f'<circle cx="{x}" cy="{py}" r="4.2" fill="{col}" stroke="#fff" stroke-width="1.2"/>')
        o.append("</g>")
    # boxes on top
    for c, x, y, h, side, pins in boxes:
        o.append(f'<rect x="{x}" y="{y}" width="{BW}" height="{h}" rx="7" fill="#f6f8f7" stroke="#2b3a33" stroke-width="1.6"/>')
        o.append(f'<rect x="{x}" y="{y}" width="{BW}" height="{HH - 4}" rx="7" fill="#1f3b2d"/>')
        o.append(f'<rect x="{x}" y="{y + HH - 12}" width="{BW}" height="8" fill="#1f3b2d"/>')
        o.append(f'<text x="{x + 10}" y="{y + 18}" style="{FONT};font-size:13px;font-weight:bold" fill="#d9f7e3">'
                 f'{escape(TITLES.get(c, c))}</text>')
        for i, p in enumerate(pins):
            py = y + HH + PH * i + PH / 2 + 6
            if side == "L":
                o.append(f'<text x="{x + BW - 10}" y="{py}" text-anchor="end" style="{FONT};font-size:12.5px" '
                         f'fill="#111">{escape(p)}</text>')
            else:
                o.append(f'<text x="{x + 10}" y="{py}" style="{FONT};font-size:12.5px" fill="#111">{escape(p)}</text>')
    o.append(f'<text x="30" y="{H - 38}" style="{FONT};font-size:11.5px" fill="#666">Generated from the NETLIST '
             'table in docs/WIRING.md by scripts/gen_diagrams.py — do not edit by hand.</text>')
    o.append(f'<text x="30" y="{H - 20}" style="{FONT};font-size:11.5px" fill="#666">Dots mark connections; '
             'lines that cross without a dot are not connected. Follow labels, not wire colours.</text>')
    o.append("</svg>\n")
    return "\n".join(o)


# =========================================================================== callout
def callout_svg():
    W, H = 1100, 520
    # 5-band 1 % colour codes: 2.2 k = red red black brown brown; 3.3 k = orange orange black brown brown
    bands = {"R1": ["#d11f1f", "#d11f1f", "#111", "#7a4a1d", "#7a4a1d"],
             "R2": ["#f08c00", "#f08c00", "#111", "#7a4a1d", "#7a4a1d"]}
    vout = rm.divider_vout(5.0, rm.R1_OHM, rm.R2_OHM)

    def resistor(cx, cy, name, vertical=False):
        g = [f'<g transform="translate({cx},{cy}){" rotate(90)" if vertical else ""}">',
             '<line x1="-62" y1="0" x2="62" y2="0" stroke="#a7a9ac" stroke-width="3"/>',
             '<rect x="-34" y="-11" width="68" height="22" rx="10" fill="url(#body)" stroke="#8d7a5a"/>']
        for i, col in enumerate(bands[name]):
            x = -24 + i * 11 + (6 if i == 4 else 0)
            g.append(f'<rect x="{x}" y="-11" width="5" height="22" fill="{col}"/>')
        g.append("</g>")
        return "\n".join(g)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         'aria-label="Callout: ECHO voltage divider and the fuse on battery positive">',
         '<defs>',
         '<linearGradient id="body" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f4dfb6"/>'
         '<stop offset="0.5" stop-color="#e2c38c"/><stop offset="1" stop-color="#b99a62"/></linearGradient>',
         '<linearGradient id="pcb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1d6fb8"/>'
         '<stop offset="1" stop-color="#124a7c"/></linearGradient>',
         '<linearGradient id="cell" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3b82c4"/>'
         '<stop offset="0.45" stop-color="#9cc7ef"/><stop offset="1" stop-color="#1f4e7a"/></linearGradient>',
         '<linearGradient id="holder" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a3a3a"/>'
         '<stop offset="1" stop-color="#111"/></linearGradient>',
         '<linearGradient id="fuse" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b197fc"/>'
         '<stop offset="1" stop-color="#6741d9"/></linearGradient>',
         '<radialGradient id="can" cx="0.4" cy="0.35" r="0.7"><stop offset="0" stop-color="#f1f3f5"/>'
         '<stop offset="1" stop-color="#868e96"/></radialGradient>',
         '<filter id="sh" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="3" '
         'stdDeviation="3" flood-opacity="0.25"/></filter>',
         '</defs>',
         f'<rect width="{W}" height="{H}" fill="#fbfaf7"/>',
         f'<text x="30" y="38" style="{FONT};font-size:22px;font-weight:bold" fill="#111">Two details that protect '
         'the build</text>',
         f'<text x="30" y="62" style="{FONT};font-size:13px" fill="#555">Illustration (not a photo). '
         'Resistor colour bands shown for 5-band 1 % parts.</text>']
    # ---- panel A: divider
    o.append('<g filter="url(#sh)"><rect x="30" y="85" width="500" height="405" rx="14" fill="#fff" stroke="#ddd"/></g>')
    o.append(f'<text x="50" y="115" style="{FONT};font-size:16px;font-weight:bold" fill="#1f3b2d">A · ECHO divider '
             '(5 V → ≈3 V)</text>')
    # HC-SR04 board
    o.append('<g filter="url(#sh)"><rect x="60" y="140" width="190" height="90" rx="6" fill="url(#pcb)"/></g>')
    for cx in (105, 205):
        o.append(f'<circle cx="{cx}" cy="185" r="34" fill="url(#can)" stroke="#495057" stroke-width="2"/>')
        o.append(f'<circle cx="{cx}" cy="185" r="22" fill="#343a40" opacity="0.85"/>')
    for i, lab in enumerate(["VCC", "TRIG", "ECHO", "GND"]):
        x = 106 + i * 30
        o.append(f'<rect x="{x - 3}" y="230" width="6" height="22" fill="#ced4da"/>')
        o.append(f'<text x="{x}" y="225" text-anchor="middle" style="{FONT};font-size:9px;font-weight:bold" fill="#fff">{lab}</text>')
    # echo wire to R1
    o.append('<path d="M 166 252 L 166 300 L 250 300" stroke="#e67700" stroke-width="4" fill="none"/>')
    o.append(resistor(312, 300, "R1"))
    o.append('<path d="M 374 300 L 420 300" stroke="#2f9e44" stroke-width="4" fill="none"/>')
    o.append('<circle cx="420" cy="300" r="7" fill="#2f9e44"/>')
    o.append('<path d="M 420 300 L 490 300" stroke="#2f9e44" stroke-width="4" fill="none"/>')
    o.append(resistor(420, 362, "R2", vertical=True))
    o.append('<path d="M 420 424 L 420 450 L 196 450 L 196 252" stroke="#111" stroke-width="4" fill="none"/>')
    o.append(f'<text x="505" y="287" style="{FONT};font-size:13px;font-weight:bold" fill="#2f9e44" text-anchor="end">'
             'to GPIO26 →</text>')
    o.append(f'<text x="312" y="280" text-anchor="middle" style="{FONT};font-size:12.5px;font-weight:bold" '
             'fill="#333">R1 2.2 kΩ</text>')
    o.append(f'<text x="438" y="366" style="{FONT};font-size:12.5px;font-weight:bold" fill="#333">R2 3.3 kΩ</text>')
    o.append(f'<text x="300" y="472" text-anchor="middle" style="{FONT};font-size:12px" fill="#111">common GND</text>')
    o.append(f'<rect x="275" y="135" width="238" height="100" rx="8" fill="#ebfbee" stroke="#2f9e44"/>')
    o.append(f'<text x="287" y="158" style="{FONT};font-size:13px;font-weight:bold" fill="#1b5e20">Vout = Vin·R2/(R1+R2)</text>')
    o.append(f'<text x="287" y="180" style="{FONT};font-size:13px" fill="#1b5e20">= 5.0 × 3.3 / 5.5 ≈ {vout:.2f} V</text>')
    o.append(f'<text x="287" y="202" style="{FONT};font-size:12px" fill="#1b5e20">Never wire ECHO straight to a</text>')
    o.append(f'<text x="287" y="219" style="{FONT};font-size:12px" fill="#1b5e20">GPIO: the ESP32 is 3.3 V logic.</text>')
    # ---- panel B: fuse
    o.append('<g filter="url(#sh)"><rect x="560" y="85" width="510" height="405" rx="14" fill="#fff" stroke="#ddd"/></g>')
    o.append(f'<text x="580" y="115" style="{FONT};font-size:16px;font-weight:bold" fill="#1f3b2d">B · 3 A fuse on '
             'battery + (mandatory)</text>')
    o.append('<g filter="url(#sh)"><rect x="600" y="150" width="300" height="70" rx="8" fill="url(#holder)"/></g>')
    o.append('<rect x="620" y="162" width="258" height="46" rx="20" fill="url(#cell)"/>')
    o.append('<rect x="872" y="175" width="10" height="20" rx="2" fill="#adb5bd"/>')
    o.append(f'<text x="750" y="190" text-anchor="middle" style="{FONT};font-size:13px;font-weight:bold" fill="#fff">'
             'protected 18650</text>')
    o.append(f'<text x="905" y="160" style="{FONT};font-size:18px;font-weight:bold" fill="#e03131">+</text>')
    o.append(f'<text x="585" y="160" style="{FONT};font-size:18px;font-weight:bold" fill="#111">−</text>')
    # + lead to fuse holder
    o.append('<path d="M 900 185 L 960 185 L 960 270" stroke="#e03131" stroke-width="5" fill="none"/>')
    o.append('<g filter="url(#sh)"><rect x="928" y="270" width="64" height="104" rx="12" fill="#212529"/></g>')
    o.append('<rect x="942" y="296" width="36" height="52" rx="4" fill="url(#fuse)"/>')
    o.append(f'<text x="960" y="327" text-anchor="middle" style="{FONT};font-size:14px;font-weight:bold" fill="#fff">3A</text>')
    o.append('<path d="M 960 374 L 960 440 L 820 440" stroke="#e03131" stroke-width="5" fill="none"/>')
    o.append(f'<text x="812" y="444" text-anchor="end" style="{FONT};font-size:13px;font-weight:bold" fill="#e03131">'
             'to DFR1026 BAT+</text>')
    o.append('<path d="M 600 185 L 580 185 L 580 400 L 640 400" stroke="#111" stroke-width="5" fill="none"/>')
    o.append(f'<text x="648" y="404" style="{FONT};font-size:13px;font-weight:bold" fill="#111">to DFR1026 battery GND</text>')
    o.append(f'<rect x="600" y="245" width="300" height="120" rx="8" fill="#fff5f5" stroke="#e03131"/>')
    for i, t in enumerate(["Fuse first, as close to the holder as practical.",
                           "Insulated holder; heat-shrink every joint.",
                           "Never solder to the cell; never series two cells.",
                           "Strap the HOLDER, not the cell; nothing sharp",
                           "against the cell wrapping."]):
        o.append(f'<text x="612" y="{268 + i * 21}" style="{FONT};font-size:12.5px" fill="#7d1a1a">{escape(t)}</text>')
    o.append("</svg>\n")
    return "\n".join(o)


# =========================================================================== live-link tap
def live_link_svg():
    W, H = 1000, 380
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         'aria-label="Listen-only telemetry tap: ESP32 TX0 and GND to a 3.3 V USB-serial adapter">',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         f'<text x="30" y="38" style="{FONT};font-size:21px;font-weight:bold" fill="#111">Live link — listen-only telemetry tap (optional)</text>',
         f'<text x="30" y="62" style="{FONT};font-size:13px" fill="#555">Two wires. The ESP32\'s own USB port stays unplugged while the battery harness is connected.</text>']
    # ESP32 board
    o.append('<rect x="40" y="95" width="300" height="230" rx="10" fill="#1f2a24" stroke="#0e1511" stroke-width="2"/>')
    o.append(f'<text x="60" y="125" style="{FONT};font-size:15px;font-weight:bold" fill="#d9f7e3">ESP32-WROOM-32 DevKit</text>')
    o.append(f'<text x="60" y="146" style="{FONT};font-size:12px" fill="#9fb3a8">powered by the scanner battery</text>')
    pins = [("TX0 / GPIO1", 185, "#1971c2"), ("GND", 245, "#111418")]
    for name, y, col in pins:
        o.append(f'<rect x="320" y="{y - 9}" width="24" height="18" rx="3" fill="#ced4da"/>')
        o.append(f'<text x="306" y="{y + 5}" text-anchor="end" style="{FONT};font-size:13.5px;font-weight:bold" fill="#e9fbe9">{name}</text>')
    o.append('<rect x="60" y="282" width="34" height="22" rx="4" fill="#adb5bd"/>')
    o.append(f'<text x="104" y="298" style="{FONT};font-size:12px;font-weight:bold" fill="#ffb3b3">own USB port: leave unplugged</text>')
    # adapter
    o.append('<rect x="620" y="110" width="270" height="200" rx="10" fill="#1c4f8a" stroke="#123259" stroke-width="2"/>')
    o.append(f'<text x="640" y="140" style="{FONT};font-size:15px;font-weight:bold" fill="#fff">USB-to-serial adapter</text>')
    o.append(f'<text x="640" y="160" style="{FONT};font-size:12px" fill="#cfe2ff">3.3 V logic (CP2102 / CH340 / FT232)</text>')
    apins = [("RX", 185, True), ("GND", 245, True), ("TX", 210, False), ("VCC", 270, False)]
    for name, y, used in apins:
        o.append(f'<rect x="608" y="{y - 9}" width="24" height="18" rx="3" fill="#ced4da"/>')
        o.append(f'<text x="642" y="{y + 5}" style="{FONT};font-size:13.5px;font-weight:bold" fill="{"#fff" if used else "#9bb8dc"}">{name}{"" if used else "  — not connected"}</text>')
    o.append('<rect x="890" y="195" width="46" height="30" rx="5" fill="#adb5bd"/>')
    o.append('<path d="M 936 210 L 975 210" stroke="#555" stroke-width="5"/>')
    o.append(f'<text x="955" y="187" text-anchor="middle" style="{FONT};font-size:12px" fill="#333">to computer</text>')
    # wires
    o.append('<path d="M 344 185 L 608 185" stroke="#1971c2" stroke-width="4" fill="none"/>')
    o.append('<path d="M 344 245 L 608 245" stroke="#111418" stroke-width="4" fill="none"/>')
    o.append(f'<text x="476" y="176" text-anchor="middle" style="{FONT};font-size:13px;font-weight:bold" fill="#1971c2">L1  data (ESP32 → computer)</text>')
    o.append(f'<text x="476" y="236" text-anchor="middle" style="{FONT};font-size:13px;font-weight:bold" fill="#111">L2  common ground</text>')
    o.append(f'<text x="30" y="{H - 22}" style="{FONT};font-size:12px" fill="#666">115 200 baud, 8N1. The console only listens. '
             'Optional and not yet tested on hardware — see docs/LIVE_LINK.md.</text>')
    o.append("</svg>\n")
    return "\n".join(o)


# =========================================================================== build flow
def build_flow_svg():
    stages = [
        ("1", "Fit coupon", "print 08 first", ["pilot + clearance holes", "servo cut-out + flange", "12 mm switch, M2 nut"]),
        ("2", "Servo-fit subset", "roof + hub + keeper", ["servo drops in, flange flat", "hub axial play 0.2–0.6 mm", "keeper fitted, hub turns"]),
        ("3", "Bench power", "no ESP32 yet", ["fuse in battery +", "OUT 5 V at the switch", "OFF→ON restart (open issue)"]),
        ("4", "Flash + bench run", "harness off to flash", ["splash, grid, sweep", "CENTER_ONLY → horn", "echo at a known distance"]),
        ("5", "Full print", "body + front panel", ["fit all modules", "sweep clears keeper", "charge + run log"]),
    ]
    W, H = 1250, 330
    bw, gap, x0, y0 = 216, 28, 30, 90
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         'aria-label="Build stages with gate checks">',
         '<defs><marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
         '<path d="M0,0 L10,5 L0,10 z" fill="#2f9e44"/></marker></defs>',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         f'<text x="30" y="40" style="{FONT};font-size:22px;font-weight:bold" fill="#111">Build stages — do not skip a gate</text>',
         f'<text x="30" y="64" style="{FONT};font-size:13px" fill="#555">Each stage has a pass/fail gate. Record the '
         'result in docs/VALIDATION.md before moving right. A failed gate means: adjust the named VERIFY variable, re-render, repeat.</text>']
    for i, (num, name, sub, gates) in enumerate(stages):
        x = x0 + i * (bw + gap)
        o.append(f'<rect x="{x}" y="{y0}" width="{bw}" height="210" rx="12" fill="#f3faf5" stroke="#2f9e44" stroke-width="2"/>')
        o.append(f'<circle cx="{x + 26}" cy="{y0 + 28}" r="15" fill="#2f9e44"/>')
        o.append(f'<text x="{x + 26}" y="{y0 + 33}" text-anchor="middle" style="{FONT};font-size:15px;font-weight:bold" '
                 f'fill="#fff">{num}</text>')
        o.append(f'<text x="{x + 50}" y="{y0 + 28}" style="{FONT};font-size:14px;font-weight:bold" fill="#10331f">{escape(name)}</text>')
        o.append(f'<text x="{x + 50}" y="{y0 + 46}" style="{FONT};font-size:11.5px" fill="#4b6355">{escape(sub)}</text>')
        o.append(f'<text x="{x + 14}" y="{y0 + 82}" style="{FONT};font-size:11px;font-weight:bold" fill="#666">GATE</text>')
        for j, g in enumerate(gates):
            yy = y0 + 106 + j * 30
            o.append(f'<rect x="{x + 14}" y="{yy - 12}" width="14" height="14" rx="3" fill="#fff" stroke="#2f9e44"/>')
            o.append(f'<text x="{x + 36}" y="{yy}" style="{FONT};font-size:11.5px" fill="#222">{escape(g)}</text>')
        if i < len(stages) - 1:
            o.append(f'<line x1="{x + bw + 4}" y1="{y0 + 105}" x2="{x + bw + gap - 4}" y2="{y0 + 105}" stroke="#2f9e44" '
                     'stroke-width="3" marker-end="url(#ar)"/>')
    o.append("</svg>\n")
    return "\n".join(o)


# =========================================================================== equation figures
def equation_figures():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 11, "svg.fonttype": "none", "axes.spines.top": False,
                         "axes.spines.right": False})
    IMG.mkdir(parents=True, exist_ok=True)
    green, amber, grey = "#2f9e44", "#e67700", "#868e96"

    # 1. distance vs echo time
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ts = [i * 100 for i in range(0, 131)]
    for T, col, ls in ((0, grey, "--"), (20, green, "-"), (35, amber, "-.")):
        ax.plot([t / 1000 for t in ts], [rm.distance_cm(t, T) for t in ts], color=col, ls=ls, lw=2,
                label=f"{T} °C (v = {rm.speed_of_sound_mps(T):.1f} m/s)")
    t100 = rm.echo_time_us(100.0, 20.0)
    ax.plot([t100 / 1000], [100], "o", color=green)
    ax.annotate(f"100 cm ↔ {t100:.0f} µs at 20 °C", (t100 / 1000, 100), (t100 / 1000 + 1.4, 70),
                arrowprops=dict(arrowstyle="->", color="#333"))
    ax.axhline(200, color="#adb5bd", lw=1)
    ax.text(0.2, 204, "display range 200 cm", color="#666", fontsize=9)
    ax.set_xlabel("ECHO high time t (ms)")
    ax.set_ylabel("distance d (cm)")
    ax.set_title("d = v·t / 2  — the echo travels there and back")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    fig.tight_layout()
    fig.savefig(IMG / "eq_distance.svg")
    plt.close(fig)

    # 2. servo timing
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    for k, (us, col, lab) in enumerate(((rm.angle_to_us(30), grey, "30°"), (rm.angle_to_us(90), green, "90°"),
                                         (rm.angle_to_us(150), amber, "150°"))):
        y0 = k * 1.5
        xs, ys = [0], [y0]
        for f in range(2):
            s = f * 20.0
            xs += [s, s, s + us / 1000, s + us / 1000, s + 20]
            ys += [y0, y0 + 1, y0 + 1, y0, y0]
        ax.plot(xs, ys, color=col, lw=2)
        ax.text(41, y0 + 0.3, f"{lab}: {us} µs → duty {rm.pulse_to_duty(us)} / 65535", color=col, fontsize=9.5)
    ax.annotate("", (0, -0.5), (20, -0.5), arrowprops=dict(arrowstyle="<->", color="#333"))
    ax.text(10, -0.95, "20 ms frame (50 Hz)", ha="center", fontsize=9)
    ax.set_xlim(-1, 68)
    ax.set_ylim(-1.3, 4.3)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("time (ms)")
    ax.set_title("Servo pulse width sets the commanded angle (default map 1000–2000 µs)", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(IMG / "eq_servo_timing.svg")
    plt.close(fig)

    # 3. divider
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    vins = [v / 100 for v in range(0, 561)]
    ax.plot(vins, [rm.divider_vout(v, rm.R1_OHM, rm.R2_OHM) for v in vins], color=green, lw=2, label="nominal 2.2 k / 3.3 k")
    lo, hi = rm.divider_worst_case(5.25, 0.01)
    ax.axhline(3.6, color="#e03131", lw=1, ls="--")
    ax.text(0.1, 3.66, "ESP32 absolute max ≈ 3.6 V (VDD + 0.3)", color="#e03131", fontsize=9)
    ax.axhline(rm.ESP32_VIH, color=grey, lw=1, ls=":")
    ax.text(0.1, rm.ESP32_VIH + 0.06, f"logic-high threshold ≈ {rm.ESP32_VIH:.2f} V (0.75·VDD)", color="#555", fontsize=9)
    ax.plot([5.0], [rm.divider_vout(5.0, rm.R1_OHM, rm.R2_OHM)], "o", color=green)
    ax.annotate(f"5.0 V in → {rm.divider_vout(5.0, rm.R1_OHM, rm.R2_OHM):.2f} V", (5.0, 3.0), (3.2, 1.2),
                arrowprops=dict(arrowstyle="->", color="#333"))
    ax.set_xlabel("ECHO high level Vin (V)")
    ax.set_ylabel("GPIO26 Vout (V)")
    ax.set_title(f"Vout = Vin·R2/(R1+R2)   (worst case at 5.25 V with 1 % parts: {lo:.2f}–{hi:.2f} V)", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(IMG / "eq_divider.svg")
    plt.close(fig)

    # 4. sweep cadence
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    settles = list(range(20, 201, 5))
    for step, col in ((2, grey), (3, green), (5, amber)):
        ax.plot(settles, [rm.sweep_one_way_s(step, s, rm.OVERHEAD_EST_MS) for s in settles], color=col, lw=2,
                label=f"{step}° steps ({rm.readings_per_pass(step)} readings per pass)")
    base = rm.sweep_one_way_s(3, 70, rm.OVERHEAD_EST_MS)
    ax.plot([70], [base], "o", color=green)
    ax.annotate(f"default: 3°, 70 ms → ≈{base:.1f} s one way (estimate)", (70, base), (105, base - 2.2),
                arrowprops=dict(arrowstyle="->", color="#333"))
    ax.set_xlabel("settle time per step (ms)")
    ax.set_ylabel("one-way sweep (s)")
    ax.set_title(f"One-way sweep ≈ moves × (settle + overhead)\noverhead ≈ {rm.OVERHEAD_EST_MS:.0f} ms is an ESTIMATE, not a measurement", fontsize=10.5)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(IMG / "eq_sweep_cadence.svg")
    plt.close(fig)


def main():
    wiring_only = "--wiring-only" in sys.argv
    DIAG.mkdir(parents=True, exist_ok=True)
    rows = load_netlist()
    (DIAG / "wiring_full.svg").write_text(wiring_svg(rows, "Radar V5.1 — full wiring (pin → net)",
                                                     "Power and signal. Hover a dot for the net-list row ID."), encoding="utf-8")
    (DIAG / "wiring_power.svg").write_text(wiring_svg([r for r in rows if r["Kind"] == "POWER"],
                                                      "Radar V5.1 — power wiring",
                                                      "Fuse on battery +, switch cuts the load, separate servo and ESP32 branches."),
                                           encoding="utf-8")
    (DIAG / "wiring_signal.svg").write_text(wiring_svg([r for r in rows if r["Kind"] == "SIGNAL"],
                                                       "Radar V5.1 — signal wiring",
                                                       "HC-SR04 through the ECHO divider, servo PWM, LCD over SPI."),
                                            encoding="utf-8")
    if wiring_only:
        print("wiring diagrams written")
        return
    (DIAG / "callout_echo_divider_fuse.svg").write_text(callout_svg(), encoding="utf-8")
    (DIAG / "build_flow.svg").write_text(build_flow_svg(), encoding="utf-8")
    (DIAG / "live_link_tap.svg").write_text(live_link_svg(), encoding="utf-8")
    equation_figures()
    print("diagrams written:", ", ".join(sorted(p.name for p in DIAG.glob("*.svg"))))


if __name__ == "__main__":
    main()
