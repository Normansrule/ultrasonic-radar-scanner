#!/usr/bin/env python3
"""Draw the app icon (a radar-style fan on a dark rounded square) at every size
the web app and the desktop app need.

  site/assets/icons/icon-192.png, icon-512.png, icon-maskable-512.png
  app/build/icon.png (1024), app/build/icon.ico

Usage: python scripts/gen_icons.py
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]


def draw(size: int, maskable: bool = False) -> Image.Image:
    S = size * 4  # supersample
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad = 0 if maskable else int(S * 0.06)
    radius = 0 if maskable else int(S * 0.22)
    d.rounded_rectangle([pad, pad, S - pad, S - pad], radius=radius, fill=(10, 20, 15, 255))
    safe = 0.62 if maskable else 0.80          # maskable icons keep content in the inner circle
    cx, cy = S / 2, S / 2 + S * safe * 0.30
    R = S * safe * 0.62
    green = (60, 220, 110, 255)
    dim = (40, 150, 80, 255)
    w = max(2, int(S * 0.012))
    for q in (1, 2, 3, 4):
        r = R * q / 4
        d.arc([cx - r, cy - r, cx + r, cy + r], start=-150, end=-30, fill=dim if q < 4 else green, width=w)
    for deg in (30, 60, 90, 120, 150):
        a = math.radians(deg)
        d.line([cx, cy, cx + R * math.cos(a), cy - R * math.sin(a)], fill=dim, width=max(1, w // 2))
    # sweep wedge
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.pieslice([cx - R, cy - R, cx + R, cy + R], start=-118, end=-92, fill=(80, 255, 130, 110))
    glow = glow.filter(ImageFilter.GaussianBlur(S * 0.01))
    im.alpha_composite(glow)
    a = math.radians(92)
    d.line([cx, cy, cx + R * math.cos(a), cy - R * math.sin(a)], fill=(170, 255, 190, 255), width=w * 2)
    for deg, frac in ((55, 0.72), (98, 0.36), (130, 0.58)):
        a = math.radians(deg)
        x, y = cx + R * frac * math.cos(a), cy - R * frac * math.sin(a)
        r = S * 0.028
        d.ellipse([x - r, y - r, x + r, y + r], fill=(150, 255, 170, 255))
    return im.resize((size, size), Image.LANCZOS)


def main():
    icons = ROOT / "site" / "assets" / "icons"
    icons.mkdir(parents=True, exist_ok=True)
    draw(192).save(icons / "icon-192.png", optimize=True)
    draw(512).save(icons / "icon-512.png", optimize=True)
    draw(512, maskable=True).save(icons / "icon-maskable-512.png", optimize=True)
    build = ROOT / "app" / "build"
    build.mkdir(parents=True, exist_ok=True)
    big = draw(1024)
    big.save(build / "icon.png", optimize=True)
    big.save(build / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icons written: site/assets/icons/, app/build/icon.png, app/build/icon.ico")


if __name__ == "__main__":
    main()
