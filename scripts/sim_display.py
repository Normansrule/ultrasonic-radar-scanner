#!/usr/bin/env python3
"""
Python port of the firmware's screen (drawScene() in firmware/Radar_V6/Radar_V6.ino),
used for the README GIF, the screen texture in the renders and layout checks.

The targets are SYNTHETIC: this shows what the drawing code produces, not a
capture of a real screen. Text uses the Adafruit GFX 5x7 font read from your
installed Adafruit GFX library (set ADAFRUIT_GFX_DIR if it is elsewhere).

Usage: python scripts/sim_display.py
Output: hardware/diagrams/radar_sweep.gif, hardware/diagrams/radar_frame.png,
        hardware/diagrams/screen_texture.png (raw 320x240 frame for renders)
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

W, H = 320, 240
FAN_CX, FAN_CY, FAN_R = 160, 236, 176
TRAIL_STEPS = 6
TTL_MS = rm.DETECTION_TTL_MS
STEP_MS = round(rm.step_time_ms())
SCALE = 2


def q565(r, g, b):  # quantise like RGB565
    return ((r >> 3) * 255 // 31, (g >> 2) * 255 // 63, (b >> 3) * 255 // 31)


C_BG = q565(2, 10, 6)
C_GRID = q565(0, 80, 36)
C_GRID_TXT = q565(40, 160, 90)
C_SWEEP = q565(120, 255, 160)
C_TEXT = q565(200, 255, 215)
C_DIM = q565(90, 150, 115)
C_WARN = q565(255, 190, 60)
C_BTN = q565(20, 60, 36)


def glow(k):
    k = max(0.0, min(1.0, k))
    return q565(int(20 + 150 * k), int(60 + 195 * k), int(30 + 120 * k))


def lround(v):
    return int(math.floor(v + 0.5)) if v >= 0 else -int(math.floor(-v + 0.5))


def load_glcdfont():
    home = Path.home()
    for c in [os.environ.get("ADAFRUIT_GFX_DIR", ""), home / "Arduino/libraries/Adafruit_GFX_Library",
              home / "Arduino/libraries/Adafruit-GFX-Library", home / "Documents/Arduino/libraries/Adafruit_GFX_Library"]:
        if c and (Path(c) / "glcdfont.c").exists():
            body = (Path(c) / "glcdfont.c").read_text(errors="ignore").split("{", 1)[1].split("}", 1)[0]
            return [int(x, 16) for x in re.findall(r"0x[0-9A-Fa-f]{2}", body)]
    return None


FONT = load_glcdfont()


class Screen:
    def __init__(self):
        self.im = Image.new("RGB", (W, H), C_BG)
        self.d = ImageDraw.Draw(self.im)

    def text(self, x, y, s, size, color):
        if not FONT:
            return
        for ch in str(s):
            o = ord(ch)
            for i in range(5):
                col = FONT[o * 5 + i]
                for j in range(8):
                    if col & (1 << j):
                        self.d.rectangle([x + i * size, y + j * size, x + i * size + size - 1, y + j * size + size - 1], fill=color)
            x += 6 * size


def P(deg, r):
    a = math.radians(deg)
    return FAN_CX + lround(r * math.cos(a)), FAN_CY - lround(r * math.sin(a))


def draw_scene(deg, cm, dets, trail, now, range_cm=200.0, paused=False):
    s = Screen()
    d = s.d
    for q in range(1, 5):
        r = FAN_R * q / 4
        pts = [P(a, r) for a in range(rm.SWEEP_MIN_DEG, rm.SWEEP_MAX_DEG + 1, 2)]
        d.line(pts, fill=C_GRID, width=1)
        s.text(FAN_CX + 4, FAN_CY - int(r) + 3, int(range_cm * q / 4), 1, C_GRID_TXT)
    for a in range(rm.SWEEP_MIN_DEG, rm.SWEEP_MAX_DEG + 1, 30):
        d.line([(FAN_CX, FAN_CY), P(a, FAN_R)], fill=C_GRID)
    for t in range(TRAIL_STEPS):
        if trail[t] < 0:
            break
        a0 = deg if t == 0 else trail[t - 1]
        d.polygon([(FAN_CX, FAN_CY), P(a0, FAN_R), P(trail[t], FAN_R)], fill=glow(0.22 * (TRAIL_STEPS - t) / TRAIL_STEPS))
    for i, v in enumerate(dets):
        if v is None:
            continue
        dcm, stamp = v
        age = now - stamp
        if age > TTL_MS:
            continue
        k = 1 - age / TTL_MS
        x, y = P(rm.SWEEP_MIN_DEG + i * rm.SWEEP_STEP_DEG, FAN_R * dcm / range_cm)
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=glow(0.25 * k))
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=glow(0.35 + 0.65 * k))
    d.line([(FAN_CX, FAN_CY), P(deg, FAN_R)], fill=C_SWEEP)
    d.ellipse([FAN_CX - 4, FAN_CY - 4, FAN_CX + 4, FAN_CY + 4], fill=C_SWEEP)
    s.text(8, 6, "ANGLE (commanded)", 1, C_DIM)
    s.text(128, 6, "DISTANCE", 1, C_DIM)
    s.text(236, 6, "RANGE", 1, C_DIM)
    s.text(282, 6, "PAUSE" if paused else "LIVE", 1, C_WARN if paused else C_DIM)
    s.text(8, 20, f"{deg:3d}", 3, C_TEXT)
    s.text(64, 26, "o", 2, C_TEXT)
    if cm is None:
        s.text(128, 20, "---", 3, C_TEXT)
    else:
        s.text(128, 20, f"{lround(cm):3d}", 3, C_TEXT)
        s.text(184, 26, "cm", 2, C_TEXT)
    s.text(236, 24, int(range_cm), 2, C_TEXT)
    s.text(236 + 6 * 2 * len(str(int(range_cm))), 24, " cm", 1, C_TEXT)
    for x, label in ((6, "-"), (258, "+")):
        d.rounded_rectangle([x, 198, x + 55, 233], radius=8, fill=C_BTN, outline=C_GRID)
        s.text(x + 19, 205, label, 3, C_TEXT)
    return s.im


def scene_cm(deg, k):
    noise = ((k * 7919 + deg * 104729) % 31 - 15) / 10.0
    if 36 <= deg <= 66:
        return 150 + noise + 0.25 * (deg - 51)
    if 93 <= deg <= 102:
        return 62 + noise
    if 123 <= deg <= 138:
        return 115 + noise
    return None


def framed(im):
    big = im.resize((W * SCALE, H * SCALE), Image.NEAREST)
    pad, cap = 22, 46
    out = Image.new("RGB", (big.width + 2 * pad, big.height + 2 * pad + cap), (232, 216, 64))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle([4, 4, out.width - 5, big.height + 2 * pad - 4], radius=18, fill=(20, 22, 21))
    out.paste(big, (pad, pad))
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except OSError:
        f = ImageFont.load_default()
    d.text((pad, big.height + 2 * pad + 4), "Simulated from the firmware drawing code on SYNTHETIC targets.", fill=(40, 40, 30), font=f)
    d.text((pad, big.height + 2 * pad + 23), "Not a capture of real hardware. Angle = commanded servo position.", fill=(70, 70, 50), font=f)
    return out


def main():
    out_dir = ROOT / "hardware" / "diagrams"
    out_dir.mkdir(parents=True, exist_ok=True)
    if FONT is None:
        print("warning: Adafruit GFX glcdfont.c not found - text will be missing (set ADAFRUIT_GFX_DIR)")
    dets = [None] * rm.readings_per_pass()
    trail = [-1] * TRAIL_STEPS
    deg, direction, now, k = rm.SWEEP_MIN_DEG, 1, 0, 0
    trip = 2 * rm.steps_one_way()
    frames, raw = [], None
    for step in range(2 * trip):
        cm = scene_cm(deg, k)
        now += STEP_MS
        b = (deg - rm.SWEEP_MIN_DEG) // rm.SWEEP_STEP_DEG
        dets[b] = (cm, now) if cm is not None else None
        im = draw_scene(deg, cm, dets, trail, now)
        if step >= trip:
            frames.append(framed(im))
            if step == trip + trip // 3:
                raw = im
        trail = [deg] + trail[:-1]
        nxt = deg + direction * rm.SWEEP_STEP_DEG
        if nxt > rm.SWEEP_MAX_DEG or nxt < rm.SWEEP_MIN_DEG:
            direction = -direction
            nxt = deg + direction * rm.SWEEP_STEP_DEG
        deg = nxt
        k += 1
    frames[len(frames) // 3].save(out_dir / "radar_frame.png", optimize=True)
    raw.save(out_dir / "screen_texture.png", optimize=True)
    pal = [f.convert("P", palette=Image.ADAPTIVE, colors=96) for f in frames]
    pal[0].save(out_dir / "radar_sweep.gif", save_all=True, append_images=pal[1:], duration=STEP_MS, loop=0,
                optimize=True, disposal=1)
    print(f"{len(frames)} frames at {STEP_MS} ms (estimated step time) -> hardware/diagrams/radar_sweep.gif")


if __name__ == "__main__":
    main()
