#!/usr/bin/env python3
"""
Generate the documentation diagrams. Every picture here is derived from a
source file in the repo, so it cannot silently drift:

  hardware/diagrams/wiring_full.svg     } from the NETLIST table in docs/WIRING.md
  hardware/diagrams/wiring_power.svg    }
  hardware/diagrams/wiring_signal.svg   }
  hardware/diagrams/wiring_picture.svg  illustrated 7-wire picture   } NETLIST too
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
    "3V3": "#7048e8", "GND": "#111418", "TRIG": "#1c7ed6", "ECHO": "#2f9e44",
    "SERVO_PWM": "#e67700", "VIN_5V": "#e03131",
}
LEFT = ["CN1", "P3", "P1"]
RIGHT = ["SENSOR", "SERVO"]
TITLES = {
    "CN1": "CYD connector CN1", "P3": "CYD connector P3", "P1": "CYD connector P1",
    "SENSOR": "RCWL-1601 / HC-SR04P", "SERVO": "SG90 micro servo",
}
NET_ORDER = ["VIN_5V", "3V3", "GND", "TRIG", "ECHO", "SERVO_PWM"]


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
        y = top if side == "L" else top + PH // 2  # offset so left and right stubs never share a row
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


# =========================================================================== wiring picture
def wiring_picture_svg(rows):
    """Illustrated picture: CYD back with its three connectors, the sensor and the servo.
    Wire ends come from the NETLIST, so the picture cannot disagree with the table."""
    W, H = 1180, 640
    pins = {  # pin -> (x, y) of the wire end
        "CN1.GND": (288, 238), "CN1.IO22": (288, 262), "CN1.IO27": (288, 286), "CN1.3V3": (288, 310),
        "P3.GND": (288, 408), "P3.IO35": (288, 432), "P3.IO22": (288, 456), "P3.IO21": (288, 480),
        "P1.VIN": (288, 536), "P1.TX": (288, 560), "P1.RX": (288, 584), "P1.GND": (288, 608),
        "SENSOR.VCC": (842, 288), "SENSOR.TRIG": (842, 312), "SENSOR.ECHO": (842, 336), "SENSOR.GND": (842, 360),
        "SERVO.GND": (842, 470), "SERVO.+5V": (842, 494), "SERVO.SIGNAL": (842, 518),
    }
    used = {r["Pin"] for r in rows}
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         'aria-label="Seven wires: CYD connectors CN1, P3 and P1 to the ultrasonic sensor and the servo">',
         '<defs>',
         '<linearGradient id="cyd" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f2cf3a"/>'
         '<stop offset="1" stop-color="#d9ac12"/></linearGradient>',
         '<linearGradient id="pcb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a7cc7"/>'
         '<stop offset="1" stop-color="#17528a"/></linearGradient>',
         '<radialGradient id="can" cx="0.4" cy="0.35" r="0.7"><stop offset="0" stop-color="#f1f3f5"/>'
         '<stop offset="1" stop-color="#868e96"/></radialGradient>',
         '<linearGradient id="servo" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3b6fd8"/>'
         '<stop offset="1" stop-color="#1c3f8f"/></linearGradient>',
         '<filter id="sh" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="3" '
         'stdDeviation="3" flood-opacity="0.22"/></filter>',
         '</defs>',
         f'<rect width="{W}" height="{H}" fill="#fbfaf7"/>',
         f'<text x="30" y="40" style="{FONT};font-size:23px;font-weight:bold" fill="#111">7 wires. No breadboard, no '
         'resistors, no soldering to the board.</text>',
         f'<text x="30" y="66" style="{FONT};font-size:13.5px" fill="#555">Back of the Cheap Yellow Display (CYD). '
         'Illustration, not a photo — pin order on your connectors may differ: follow the silkscreen.</text>']
    # CYD board
    o.append('<g filter="url(#sh)"><rect x="40" y="95" width="270" height="535" rx="14" fill="url(#cyd)" '
             'stroke="#a8840c" stroke-width="2"/></g>')
    o.append(f'<text x="60" y="128" style="{FONT};font-size:17px;font-weight:bold" fill="#3d2f00">CYD (back)</text>')
    o.append(f'<text x="60" y="148" style="{FONT};font-size:12px" fill="#5c4700">ESP32-2432S028R</text>')
    o.append('<rect x="60" y="160" width="74" height="30" rx="5" fill="#adb5bd" stroke="#6c757d"/>')
    o.append(f'<text x="144" y="181" style="{FONT};font-size:12px;font-weight:bold" fill="#3d2f00">USB → charger ≥ 1 A</text>')
    for name, y0, labels in (("CN1", 222, ["GND", "IO22", "IO27", "3.3V"]),
                             ("P3", 392, ["GND", "IO35", "IO22", "IO21"]),
                             ("P1", 520, ["VIN", "TX", "RX", "GND"])):
        o.append(f'<rect x="198" y="{y0}" width="90" height="{4 * 24 + 8}" rx="5" fill="#f8f9fa" stroke="#495057" stroke-width="1.5"/>')
        o.append(f'<text x="188" y="{y0 + 18}" text-anchor="end" style="{FONT};font-size:15px;font-weight:bold" fill="#3d2f00">{name}</text>')
        for i, lab in enumerate(labels):
            pin = f"{name}.{lab.replace('3.3V', '3V3')}"
            y = y0 + 16 + 24 * i
            on = pin in used
            o.append(f'<rect x="272" y="{y - 6}" width="16" height="12" rx="2" fill="{"#495057" if on else "#dee2e6"}"/>')
            o.append(f'<text x="264" y="{y + 4}" text-anchor="end" style="{FONT};font-size:12px;'
                     f'font-weight:{"bold" if on else "normal"}" fill="{"#111" if on else "#adb5bd"}">{lab}</text>')
    o.append(f'<text x="60" y="618" style="{FONT};font-size:11px" fill="#5c4700">grey pins: leave unconnected</text>')
    # sensor
    o.append('<g filter="url(#sh)"><rect x="842" y="150" width="300" height="230" rx="10" fill="url(#pcb)"/></g>')
    for cx in (920, 1064):
        o.append(f'<circle cx="{cx}" cy="208" r="48" fill="url(#can)" stroke="#495057" stroke-width="2"/>')
        o.append(f'<circle cx="{cx}" cy="208" r="32" fill="#343a40" opacity="0.85"/>')
    o.append(f'<text x="1128" y="320" text-anchor="end" style="{FONT};font-size:14px;font-weight:bold" fill="#fff">RCWL-1601</text>')
    o.append(f'<text x="1128" y="338" text-anchor="end" style="{FONT};font-size:14px;font-weight:bold" fill="#fff">/ HC-SR04P</text>')
    o.append(f'<text x="1128" y="362" text-anchor="end" style="{FONT};font-size:12px" fill="#cfe2ff">3.3 V version</text>')
    # servo
    o.append('<rect x="836" y="456" width="22" height="76" rx="4" fill="#212529"/>')  # servo plug
    for y, col in ((470, "#6b3f1d"), (494, "#e03131"), (518, "#f08c00")):  # servo's own cable
        o.append(f'<path d="M 858 {y} C 920 {y} 930 494 990 494" stroke="{col}" stroke-width="3" fill="none"/>')
    o.append('<g filter="url(#sh)"><rect x="990" y="440" width="150" height="110" rx="8" fill="url(#servo)"/></g>')
    o.append('<rect x="968" y="472" width="194" height="12" rx="3" fill="#2a56b4"/>')
    o.append('<circle cx="1105" cy="440" r="20" fill="#2a56b4"/><circle cx="1105" cy="440" r="7" fill="#f8f9fa"/>')
    o.append(f'<text x="1065" y="525" text-anchor="middle" style="{FONT};font-size:14px;font-weight:bold" fill="#fff">SG90 servo</text>')
    for pin, (x, y) in pins.items():
        if pin.startswith("SENSOR."):
            o.append(f'<rect x="{x - 14}" y="{y - 6}" width="14" height="12" rx="2" fill="#ced4da" stroke="#868e96"/>')
            o.append(f'<text x="{x + 8}" y="{y + 4}" style="{FONT};font-size:12px;font-weight:bold" '
                     f'fill="#fff">{pin.split(".")[1]}</text>')
        elif pin.startswith("SERVO."):
            o.append(f'<text x="{x - 22}" y="{y - 4}" text-anchor="end" style="{FONT};font-size:11px;font-weight:bold" '
                     f'fill="#333">{pin.split(".")[1]}</text>')
    # wires from the NETLIST
    by_wire = OrderedDict()
    for r in rows:
        by_wire.setdefault(r["Wire"], []).append(r)
    lanes = {w: 420 + i * 34 for i, w in enumerate(by_wire)}
    for w, ends in by_wire.items():
        a = next(e for e in ends if e["Pin"].split(".")[0] in LEFT)
        b = next(e for e in ends if e["Pin"].split(".")[0] in RIGHT)
        (x1, y1), (x2, y2) = pins[a["Pin"]], pins[b["Pin"]]
        x2 -= 14 if b["Pin"].startswith("SENSOR.") else 6
        col = NET_COLORS.get(a["Net"], "#444")
        lx = lanes[w]
        o.append(f'<g class="wire net" data-net="{a["Net"]}" data-wire="{w}"><title>{escape(w + ": " + a["Pin"] + " → " + b["Pin"] + " (" + a["Net"] + ")")}</title>')
        d = (f'M {x1} {y1} L {lx - 12} {y1} Q {lx} {y1} {lx} {y1 + (12 if y2 > y1 else -12)} '
             f'L {lx} {y2 + (-12 if y2 > y1 else 12)} Q {lx} {y2} {lx + 12} {y2} L {x2} {y2}')
        o.append(f'<path d="{d}" stroke="#fbfaf7" stroke-width="9" fill="none" stroke-linejoin="round"/>')
        o.append(f'<path d="{d}" stroke="{col}" stroke-width="4.5" fill="none" stroke-linejoin="round"/>')
        o.append(f'<rect x="{lx - 17}" y="{(y1 + y2) / 2 - 10}" width="34" height="20" rx="10" fill="{col}"/>')
        o.append(f'<text x="{lx}" y="{(y1 + y2) / 2 + 4.5}" text-anchor="middle" style="{FONT};font-size:12px;'
                 f'font-weight:bold" fill="#fff">{w}</text></g>')
    # legend
    for i, n in enumerate(NET_ORDER):
        x = 360 + i * 125
        o.append(f'<rect x="{x}" y="94" width="22" height="8" rx="4" fill="{NET_COLORS[n]}"/>')
        o.append(f'<text x="{x + 28}" y="103" style="{FONT};font-size:12px" fill="#333">{n}</text>')
    o.append(f'<text x="360" y="128" style="{FONT};font-size:12px" fill="#666">Generated from the NETLIST table in '
             'docs/WIRING.md by scripts/gen_diagrams.py.</text>')
    o.append("</svg>\n")
    return "\n".join(o)


# =========================================================================== build flow
def build_flow_svg():
    stages = [
        ("1", "Fit coupon", "print 05 first (≈ 20 min)", ["CYD pegs: snug, not loose", "sensor cans press in", "servo screw pilots bite"]),
        ("2", "Bench: wire + flash", "nothing printed yet", ["P1 VIN ≈ 5 V (meter)", "grid + sweep on screen", "echo at a known distance"]),
        ("3", "Print", "P1 shell, P2 bezel/base/head", ["no supports needed", "bezel slides in grooves", "base clicks in"]),
        ("4", "Assemble", "CENTER_ONLY = true first", ["servo at 90°, fit head", "head turns ±60° freely", "cables don't snag"]),
        ("5", "Run + record", "CENTER_ONLY = false", ["sweep matches roof ticks", "no resets at servo start", "log in VALIDATION.md"]),
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
    ax.set_ylabel("IO35 Vout (V)")
    ax.set_title(f"FALLBACK ONLY (5 V HC-SR04): Vout = Vin·R2/(R1+R2)\nworst case at 5.25 V with 1 % parts: {lo:.2f}–{hi:.2f} V", fontsize=10.5)
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
    (DIAG / "wiring_full.svg").write_text(wiring_svg(rows, "Radar V6 — wiring (pin → net)",
                                                     "7 wires. Hover a dot for the net-list row ID."), encoding="utf-8")
    (DIAG / "wiring_picture.svg").write_text(wiring_picture_svg(rows), encoding="utf-8")
    if wiring_only:
        print("wiring diagrams written")
        return
    (DIAG / "build_flow.svg").write_text(build_flow_svg(), encoding="utf-8")
    equation_figures()
    print("diagrams written:", ", ".join(sorted(p.name for p in DIAG.glob("*.svg"))))


if __name__ == "__main__":
    main()
