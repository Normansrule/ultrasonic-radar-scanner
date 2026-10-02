#!/usr/bin/env python3
"""
Pixel-level Python port of the firmware's drawing code (renderFrame() in
firmware/Radar_V5/Radar_V5.ino) used to make the README sweep GIF.

The targets are SYNTHETIC. The GIF shows what the drawing code produces; it is
not a capture of a real screen and says nothing about real sensor behaviour.

Text uses the Adafruit GFX 5x7 "classic" font read from your installed Adafruit
GFX library (glcdfont.c). Set ADAFRUIT_GFX_DIR if it is not in the default
Arduino libraries folder; without it a fallback font is used.

Usage: python scripts/sim_display.py
Output: hardware/diagrams/radar_sweep.gif, hardware/diagrams/radar_frame.png
"""
from __future__ import annotations

import math
import os
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import radar_math as rm  # noqa: E402

W, H = 160, 128
FAN_CX, FAN_CY, FAN_R = 80, 125, 88
TRAIL_STEPS = 4
TTL_MS = 9000
STEP_MS = round(rm.step_time_ms())          # ESTIMATED loop time per reading
SCALE = 3


def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def to888(c):
    r, g, b = (c >> 11) & 0x1F, (c >> 5) & 0x3F, c & 0x1F
    return (r * 255 // 31, g * 255 // 63, b * 255 // 31)


COL_BG = rgb565(0, 0, 0)
COL_GRID = rgb565(0, 90, 20)
COL_GRID_TEXT = rgb565(0, 150, 40)
COL_SWEEP = rgb565(80, 255, 110)
COL_TEXT = rgb565(170, 255, 180)


def scale_green(k):
    k = max(0.0, min(1.0, k))
    return rgb565(int(40 + 160 * k), int(90 + 165 * k), int(40 + 100 * k))


def lround(v):
    return int(math.floor(v + 0.5)) if v >= 0 else -int(math.floor(-v + 0.5))


# ------------------------------------------------------------------ GFX font
def load_glcdfont():
    cands = [os.environ.get("ADAFRUIT_GFX_DIR", "")]
    home = Path.home()
    cands += [home / "Arduino/libraries/Adafruit_GFX_Library", home / "Arduino/libraries/Adafruit-GFX-Library",
              home / "Documents/Arduino/libraries/Adafruit_GFX_Library"]
    for c in cands:
        if not c:
            continue
        f = Path(c) / "glcdfont.c"
        if f.exists():
            body = f.read_text(errors="ignore").split("{", 1)[1].split("}", 1)[0]
            return [int(x, 16) for x in re.findall(r"0x[0-9A-Fa-f]{2}", body)]
    return None


class Canvas:
    def __init__(self):
        self.px = [[COL_BG] * W for _ in range(H)]
        self.font = FONT
        self.cx = self.cy = 0
        self.size = 1
        self.color = COL_TEXT

    def pixel(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            self.px[y][x] = c

    def fill(self, c):
        for row in self.px:
            row[:] = [c] * W

    def vline(self, x, y, h, c):
        for yy in range(y, y + h):
            self.pixel(x, yy, c)

    def line(self, x0, y0, x1, y1, c):  # Adafruit_GFX::writeLine (Bresenham)
        steep = abs(y1 - y0) > abs(x1 - x0)
        if steep:
            x0, y0, x1, y1 = y0, x0, y1, x1
        if x0 > x1:
            x0, x1, y0, y1 = x1, x0, y1, y0
        dx, dy = x1 - x0, abs(y1 - y0)
        err = dx // 2
        ystep = 1 if y0 < y1 else -1
        while x0 <= x1:
            self.pixel(y0, x0, c) if steep else self.pixel(x0, y0, c)
            err -= dy
            if err < 0:
                y0 += ystep
                err += dx
            x0 += 1

    def fill_circle(self, x0, y0, r, c):  # Adafruit_GFX::fillCircle
        self.vline(x0, y0 - r, 2 * r + 1, c)
        f, ddx, ddy, x, y = 1 - r, 1, -2 * r, 0, r
        px, py, delta = x, y, 1
        while x < y:
            if f >= 0:
                y -= 1
                ddy += 2
                f += ddy
            x += 1
            ddx += 2
            f += ddx
            if x < y + 1:
                self.vline(x0 + x, y0 - y, 2 * y + delta, c)
                self.vline(x0 - x, y0 - y, 2 * y + delta, c)
            if y != py:
                self.vline(x0 + py, y0 - px, 2 * px + delta, c)
                self.vline(x0 - py, y0 - px, 2 * px + delta, c)
                py = y
            px = x

    def text(self, s):
        s = str(s)
        for ch in s:
            o = ord(ch)
            if self.font:
                for i in range(5):
                    col = self.font[o * 5 + i]
                    for j in range(8):
                        if col & (1 << j):
                            for a in range(self.size):
                                for b in range(self.size):
                                    self.pixel(self.cx + i * self.size + a, self.cy + j * self.size + b, self.color)
            self.cx += 6 * self.size
        return s

    def image(self):
        im = Image.new("RGB", (W, H))
        im.putdata([to888(c) for row in self.px for c in row])
        if not self.font:  # fallback text overlay
            pass
        return im


FONT = load_glcdfont()


def polar(deg, r):
    a = math.radians(deg)
    return FAN_CX + lround(r * math.cos(a)), FAN_CY - lround(r * math.sin(a))


def render(g: Canvas, deg, cm, dets, trail, now):
    g.fill(COL_BG)
    for q in range(1, 5):
        r = FAN_R * q / 4
        px, py = polar(rm.SWEEP_MIN_DEG, r)
        for d in range(rm.SWEEP_MIN_DEG + 2, rm.SWEEP_MAX_DEG + 1, 2):
            x, y = polar(d, r)
            g.line(px, py, x, y, COL_GRID)
            px, py = x, y
        g.size, g.color, g.cx, g.cy = 1, COL_GRID_TEXT, FAN_CX + 3, FAN_CY - int(r) + 2
        g.text(int(rm.MAX_RANGE_CM * q / 4))
    for d in range(rm.SWEEP_MIN_DEG, rm.SWEEP_MAX_DEG + 1, 30):
        x, y = polar(d, FAN_R)
        g.line(FAN_CX, FAN_CY, x, y, COL_GRID)
    for i, dd in enumerate(dets):
        if dd is None:
            continue
        dcm, stamp = dd
        age = now - stamp
        if age > TTL_MS:
            dets[i] = None
            continue
        k = 1 - age / TTL_MS
        x, y = polar(rm.SWEEP_MIN_DEG + i * rm.SWEEP_STEP_DEG, FAN_R * dcm / rm.MAX_RANGE_CM)
        g.fill_circle(x, y, 2, scale_green(0.25 + 0.75 * k))
    for t in range(TRAIL_STEPS - 1, -1, -1):
        if trail[t] < 0:
            continue
        x, y = polar(trail[t], FAN_R)
        g.line(FAN_CX, FAN_CY, x, y, scale_green(0.15 * (TRAIL_STEPS - t) / TRAIL_STEPS))
    x, y = polar(deg, FAN_R)
    g.line(FAN_CX, FAN_CY, x, y, COL_SWEEP)
    # header
    g.size, g.color = 1, COL_GRID_TEXT
    g.cx, g.cy = 4, 2
    g.text("ANGLE")
    g.cx, g.cy = 84, 2
    g.text("DIST")
    g.cx, g.cy = 130, 2
    g.text("EDU")
    g.size, g.color = 2, COL_TEXT
    g.cx, g.cy = 4, 13
    g.text(f"{deg:03d}")
    g.size, g.cx, g.cy = 1, 42, 20
    g.text("deg")
    g.size, g.cx, g.cy = 2, 84, 13
    if cm is None:
        g.text("---")
    else:
        g.text(f"{lround(cm):3d}")
        g.size, g.cx, g.cy = 1, 122, 20
        g.text("cm")


# ------------------------------------------------------------------ synthetic scene
def scene_cm(deg, k):
    noise = ((k * 7919 + deg * 104729) % 31 - 15) / 10.0     # deterministic +/-1.5 cm
    if 36 <= deg <= 66:
        return 150 + noise + 0.25 * (deg - 51)                # a wall, slightly angled
    if 93 <= deg <= 102:
        return 62 + noise                                     # a chair leg
    if 123 <= deg <= 138:
        return 115 + noise                                    # a box
    return None                                               # nothing within 200 cm


def frame_image(g: Canvas):
    im = g.image().resize((W * SCALE, H * SCALE), Image.NEAREST)
    pad, cap = 18, 44
    out = Image.new("RGB", (im.width + 2 * pad, im.height + 2 * pad + cap), (24, 28, 26))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle([6, 6, out.width - 7, im.height + 2 * pad - 6], radius=14, fill=(12, 14, 13),
                        outline=(60, 70, 64), width=2)
    out.paste(im, (pad, pad))
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    except OSError:
        f = ImageFont.load_default()
    d.text((pad, im.height + 2 * pad + 4), "Simulated from the firmware drawing code on SYNTHETIC targets.",
           fill=(190, 200, 194), font=f)
    d.text((pad, im.height + 2 * pad + 22), "Not a capture of real hardware. Angle = commanded servo position.",
           fill=(150, 160, 154), font=f)
    return out


def main():
    out_dir = ROOT / "hardware" / "diagrams"
    out_dir.mkdir(parents=True, exist_ok=True)
    if FONT is None:
        print("warning: Adafruit GFX glcdfont.c not found - header text will be missing (set ADAFRUIT_GFX_DIR)")
    n_bins = rm.readings_per_pass()
    dets = [None] * n_bins
    trail = [-1] * TRAIL_STEPS
    deg, direction, now = rm.SWEEP_MIN_DEG, 1, 0
    moves_per_trip = 2 * rm.steps_one_way()
    frames, k = [], 0
    g = Canvas()
    for step in range(2 * moves_per_trip):         # warm-up trip, then the recorded trip
        cm = scene_cm(deg, k)
        now += STEP_MS
        b = (deg - rm.SWEEP_MIN_DEG) // rm.SWEEP_STEP_DEG
        dets[b] = (cm, now) if cm is not None else None
        render(g, deg, cm, dets, trail, now)
        if step >= moves_per_trip:
            frames.append(frame_image(g))
        trail = [deg] + trail[:-1]
        nxt = deg + direction * rm.SWEEP_STEP_DEG
        if nxt > rm.SWEEP_MAX_DEG or nxt < rm.SWEEP_MIN_DEG:
            direction = -direction
            nxt = deg + direction * rm.SWEEP_STEP_DEG
        deg = nxt
        k += 1
    frames[len(frames) // 3].save(out_dir / "radar_frame.png", optimize=True)
    pal = [f.convert("P", palette=Image.ADAPTIVE, colors=64) for f in frames]
    pal[0].save(out_dir / "radar_sweep.gif", save_all=True, append_images=pal[1:],
                duration=STEP_MS, loop=0, optimize=True, disposal=1)
    print(f"{len(frames)} frames at {STEP_MS} ms (estimated step time) -> hardware/diagrams/radar_sweep.gif")


if __name__ == "__main__":
    main()
