#!/usr/bin/env python3
"""
Render preview images of the CadQuery model with a small pure-numpy rasteriser
(no GPU, no display server), so the pictures in the README always come from the
same source as the STL/STEP files.

Outputs (hardware/diagrams/):
  parts_labeled.png   the four printed parts, exploded, with labels
  assembly_section.png  cut through the middle: where the three modules sit
  plate_P1.png / plate_P2.png / plate_S1_fit_coupon.png   top-down plate previews

Usage: python scripts/render_previews.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cad"))
import build_radar as M  # noqa: E402

OUT = ROOT / "hardware" / "diagrams"
SS = 2  # supersampling

PART_COLORS = {
    "01_shell": (214, 206, 188),
    "02_bezel": (48, 52, 56),
    "03_base": (70, 74, 78),
    "04_head": (110, 200, 160),
    "05_fit_coupon": (200, 160, 60),
}
REF_COLOR = (185, 190, 196)
REF_SPECIAL = {"ref_sensor": (70, 120, 200), "ref_cyd": (232, 200, 60),
               "ref_servo_sg90": (40, 80, 170), "ref_servo_horn": (235, 235, 235)}


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def mesh(shape, tol=0.15):
    shp = shape.val() if hasattr(shape, "val") else shape
    v, t = shp.tessellate(tol, 0.3)
    return np.array([(p.x, p.y, p.z) for p in v], float), np.array(t, int)


def view_matrix(az_deg, el_deg):
    az, el = math.radians(az_deg), math.radians(el_deg)
    # rotate about Z (azimuth) then tilt about X (elevation); camera looks along -Y' toward +Y'
    rz = np.array([[math.cos(az), -math.sin(az), 0], [math.sin(az), math.cos(az), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, math.cos(el), -math.sin(el)], [0, math.sin(el), math.cos(el)]])
    return rx @ rz


def render(items, az=-35, el=25, size=(1400, 900), bg=(250, 250, 248), pad=40, top_down=False):
    """items: list of (verts, tris, rgb). Returns (PIL.Image, project_fn)."""
    W, H = size[0] * SS, size[1] * SS
    R = np.eye(3) if top_down else view_matrix(az, el)
    pts = [(v @ R.T) for v, _, _ in items]
    if top_down:
        # screen x = X, screen y = -Y, depth = -Z
        proj = [np.stack([p[:, 0], -p[:, 1], -p[:, 2]], 1) for p in pts]
    else:
        # screen x = X', screen y = -Z', depth = Y' (bigger = farther)
        proj = [np.stack([p[:, 0], -p[:, 2], p[:, 1]], 1) for p in pts]
    allp = np.vstack(proj)
    mn, mx = allp[:, :2].min(0), allp[:, :2].max(0)
    scale = min((W - 2 * pad * SS) / (mx[0] - mn[0]), (H - 2 * pad * SS) / (mx[1] - mn[1]))
    off = np.array([W, H]) / 2 - (mn + mx) / 2 * scale

    def to_px(p3):
        p = (np.atleast_2d(p3) @ R.T)
        if top_down:
            q = np.stack([p[:, 0], -p[:, 1]], 1)
        else:
            q = np.stack([p[:, 0], -p[:, 2]], 1)
        return (q * scale + off) / SS

    zbuf = np.full((H, W), np.inf)
    cbuf = np.zeros((H, W, 3))
    nbuf = np.zeros((H, W), int)
    light = np.array([-0.45, -0.75, 0.55]) if not top_down else np.array([-0.3, 0.4, 0.85])
    light /= np.linalg.norm(light)
    fid = 1
    for (v, t, rgb), pr in zip(items, proj):
        wv = v[t]                                   # (n,3,3) world
        nrm = np.cross(wv[:, 1] - wv[:, 0], wv[:, 2] - wv[:, 0])
        ln = np.linalg.norm(nrm, axis=1)
        ok = ln > 1e-12
        nrm[ok] /= ln[ok, None]
        shade = 0.35 + 0.65 * np.clip(nrm @ light, 0, 1)
        sp = pr[t].copy()
        sp[:, :, :2] = sp[:, :, :2] * scale + off
        col = np.array(rgb, float) / 255.0
        # quantised normal id to find creases
        nid = (np.round(nrm * 4) + 5) @ np.array([1, 11, 121])
        for i in range(len(t)):
            if not ok[i]:
                continue
            a, b, c = sp[i]
            x0 = int(max(math.floor(min(a[0], b[0], c[0])), 0))
            x1 = int(min(math.ceil(max(a[0], b[0], c[0])), W - 1))
            y0 = int(max(math.floor(min(a[1], b[1], c[1])), 0))
            y1 = int(min(math.ceil(max(a[1], b[1], c[1])), H - 1))
            if x1 < x0 or y1 < y0:
                continue
            xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(d) < 1e-12:
                continue
            w0 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / d
            w1 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / d
            w2 = 1 - w0 - w1
            inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not inside.any():
                continue
            z = w0 * a[2] + w1 * b[2] + w2 * c[2]
            sub = zbuf[y0:y1 + 1, x0:x1 + 1]
            upd = inside & (z < sub)
            sub[upd] = z[upd]
            cbuf[y0:y1 + 1, x0:x1 + 1][upd] = col * shade[i]
            nbuf[y0:y1 + 1, x0:x1 + 1][upd] = fid * 2000 + nid[i]
        fid += 1

    hit = np.isfinite(zbuf)
    img = np.where(hit[..., None], cbuf, np.array(bg) / 255.0)
    # outline: part/normal-id changes and depth jumps
    edge = np.zeros_like(hit)
    zf = np.where(hit, zbuf, 1e9)
    for dy, dx in ((0, 1), (1, 0)):
        n1, n2 = nbuf, np.roll(np.roll(nbuf, -dy, 0), -dx, 1)
        z1, z2 = zf, np.roll(np.roll(zf, -dy, 0), -dx, 1)
        edge |= (n1 != n2) & (hit | np.roll(np.roll(hit, -dy, 0), -dx, 1))
        edge |= np.abs(z1 - z2) > 2.0 * SS
    img[edge] = img[edge] * 0.35
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    im = im.resize(size, Image.LANCZOS)
    return im, to_px


def label(draw, xy, anchor_xy, text, f):
    draw.line([anchor_xy, xy], fill=(90, 90, 90), width=2)
    draw.ellipse([anchor_xy[0] - 4, anchor_xy[1] - 4, anchor_xy[0] + 4, anchor_xy[1] + 4], fill=(90, 90, 90))
    tw = draw.textlength(text, font=f)
    x = xy[0] - tw - 6 if xy[0] < anchor_xy[0] else xy[0] + 6
    draw.text((x, xy[1] - f.size // 2 - 2), text, fill=(20, 20, 20), font=f)


def title(im, text, sub):
    d = ImageDraw.Draw(im)
    d.text((28, 20), text, fill=(15, 15, 15), font=font(30))
    d.text((28, 58), sub, fill=(90, 90, 90), font=font(18))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    parts = M.build_all()
    refs = {n: f() for n, f in M.REFERENCE_BUILDERS.items()}

    # ---------------- exploded view with labels ----------------
    explode = {"01_shell": (0, 0, 0), "02_bezel": (0, -70, -4), "03_base": (0, 0, -45), "04_head": (0, 0, 55)}
    names = {"01_shell": "01 shell", "02_bezel": "02 bezel (CYD presses on)",
             "03_base": "03 base (press-fit)", "04_head": "04 head (sensor presses in)"}
    items, anchors = [], {}
    for n, dv in explode.items():
        v, t = mesh(parts[n])
        v = v + np.array(dv)
        items.append((v, t, PART_COLORS[n]))
        anchors[n] = v.mean(0)
    im, to_px = render(items, az=-38, el=22, size=(1400, 1060), pad=110)
    d = ImageDraw.Draw(im)
    f = font(22)
    for n, c in anchors.items():
        a = to_px(c)[0]
        side = -1 if n == "02_bezel" else 1
        dx = {"01_shell": 300, "03_base": 230}.get(n, 190)
        label(d, (a[0] + side * dx, a[1] + (60 if n == "03_base" else -20)), tuple(a), names[n], f)
    title(im, "Radar V6 - four printed parts",
          "Rendered from cad/build_radar.py - geometry only, not a photo of a printed unit")
    im.save(OUT / "parts_labeled.png", optimize=True)

    # ---------------- section: where the modules sit ----------------
    items = []
    cut = M.box(-200, 0, -200, 200, -10, 200)
    for n in M.REQUIRED_PARTS:
        v, t = mesh(parts[n].cut(cut))
        items.append((v, t, PART_COLORS[n]))
    for n, r in refs.items():
        v, t = mesh(r.cut(cut))
        items.append((v, t, REF_SPECIAL.get(n, REF_COLOR)))
    im, _ = render(items, az=90, el=8, size=(1200, 900), pad=70)
    title(im, "Radar V6 - section through the middle",
          "CYD (yellow) on the bezel, SG90 (blue) hanging under the roof, sensor in the head")
    im.save(OUT / "assembly_section.png", optimize=True)

    # ---------------- plates ----------------
    rep = json.loads((ROOT / "cad" / "geometry_report.json").read_text())
    bed_w, bed_d, _ = M.A1_MINI_BED
    for pname, members in {**M.PLATES, **M.OPTIONAL_PLATE, **M.STAGE_PLATES}.items():
        items = []
        # bed as a thin slab
        bed = np.array([[0, 0, -1], [bed_w, 0, -1], [bed_w, bed_d, -1], [0, bed_d, -1]], float)
        items.append((bed, np.array([[0, 1, 2], [0, 2, 3]]), (228, 230, 226)))
        for n in members:
            pp = M.to_print_pose(n, parts[n])
            v, t = mesh(pp)
            info = rep["plates"][pname][n]
            if info["turned_90"]:
                v = np.stack([-v[:, 1], v[:, 0], v[:, 2]], 1)
            v = v + np.array([info["center_xy"][0], info["center_xy"][1], 0])
            items.append((v, t, PART_COLORS[n]))
        im, to_px = render(items, size=(900, 900), pad=40, top_down=True, bg=(245, 245, 243))
        d = ImageDraw.Draw(im)
        for n in members:
            c = rep["plates"][pname][n]["center_xy"]
            p = to_px(np.array([c[0], c[1], 60]))[0]
            txt = n.split("_", 1)[0] + " " + n.split("_", 1)[1].replace("_", " ")
            tw = d.textlength(txt, font=font(18))
            d.rectangle([p[0] - tw / 2 - 5, p[1] - 13, p[0] + tw / 2 + 5, p[1] + 13], fill=(255, 255, 255))
            d.text((p[0] - tw / 2, p[1] - 11), txt, fill=(10, 10, 10), font=font(18))
        d.text((20, 12), f"Plate {pname} - Bambu Lab A1 mini (180 x 180 mm)", fill=(15, 15, 15), font=font(24))
        im.save(OUT / f"plate_{pname}.png", optimize=True)
    print("previews written to", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
