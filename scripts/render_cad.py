#!/usr/bin/env python3
"""
Regenerate every CAD build product from cad/build_radar.py so the files in
cad/ can never drift from the source:

  cad/step/<part>.step            assembly position (design coordinates)
  cad/step/assembly.step          all printed parts in place
  cad/stl/<part>.stl              print orientation, resting on z = 0
  cad/3mf/radar_a1mini_multiplate.3mf   ONE file, plates P1 + P2 (experimental Bambu plate metadata)
  cad/3mf/plate_P1.3mf, plate_P2.3mf, plate_S1_fit_coupon.3mf   core-spec fallbacks
  cad/geometry_report.json        RECORDED geometry checks (not physical validation)

Usage:  python scripts/render_cad.py [--skip-sweep]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import sys
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cad"))

import cadquery as cq  # noqa: E402
import build_radar as M  # noqa: E402

CAD = ROOT / "cad"
STL_TOL, STL_ANG = 0.03, 0.15
PLATE_MARGIN = 6.0      # keep parts this far from the bed edge
PART_GAP = 6.0          # minimum gap between parts on a plate
BAMBU_PLATE_STRIDE = M.A1_MINI_BED[0] * 1.2   # Bambu Studio lays plates out bed-width x 1.2 apart


# ---------------------------------------------------------------- geometry helpers
def solid(wp: cq.Workplane) -> cq.Shape:
    v = wp.val()
    return v if isinstance(v, cq.Shape) else wp.findSolid()


def inter_volume(a: cq.Shape, b: cq.Shape) -> float:
    try:
        return float(a.intersect(b).Volume())
    except Exception:
        return float("nan")


def bbox(shape: cq.Shape):
    x0, x1, y0, y1, z0, z1 = M.tight_bbox(shape)
    r = lambda v: round(v, 3)  # noqa: E731
    return dict(xmin=r(x0), xmax=r(x1), ymin=r(y0), ymax=r(y1), zmin=r(z0), zmax=r(z1),
                x=r(x1 - x0), y=r(y1 - y0), z=r(z1 - z0))


def tessellate(shape: cq.Shape):
    verts, tris = shape.tessellate(STL_TOL, STL_ANG)
    return [(v.x, v.y, v.z) for v in verts], [tuple(t) for t in tris]


# ---------------------------------------------------------------- plate layout
def shelf_pack(items, bed_w, bed_d):
    """items: list of (name, w, d). First-fit shelf packing, tallest first, parts
    may turn 90 degrees about Z. Returns {name: (cx, cy, rotated)} in bed coordinates,
    or raises RuntimeError if something does not fit."""
    usable_w, usable_d = bed_w - 2 * PLATE_MARGIN, bed_d - 2 * PLATE_MARGIN
    items = sorted(items, key=lambda t: -max(t[1], t[2]))
    shelves = []  # [y0, height, x_cursor]
    placed = {}
    for name, w, d in items:
        done = False
        for (ww, dd, rot) in ((w, d, False), (d, w, True)):
            for sh in shelves:
                if sh[2] + ww <= usable_w + 1e-6 and dd <= sh[1] + 1e-6:
                    placed[name] = (PLATE_MARGIN + sh[2] + ww / 2, PLATE_MARGIN + sh[0] + dd / 2, rot)
                    sh[2] += ww + PART_GAP
                    done = True
                    break
            if done:
                break
        if done:
            continue
        y0 = shelves[-1][0] + shelves[-1][1] + PART_GAP if shelves else 0.0
        for (ww, dd, rot) in ((w, d, False), (d, w, True)):
            if ww <= usable_w + 1e-6 and y0 + dd <= usable_d + 1e-6:
                shelves.append([y0, dd, ww + PART_GAP])
                placed[name] = (PLATE_MARGIN + ww / 2, PLATE_MARGIN + y0 + dd / 2, rot)
                done = True
                break
        if not done:
            raise RuntimeError(f"{name} does not fit on the plate")
    return placed


# ---------------------------------------------------------------- 3MF writer
CT = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
 <Default Extension="config" ContentType="text/xml"/>
</Types>
"""
RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
"""


def write_3mf(path: Path, objects, plates=None, bambu=False, title=""):
    """objects: list of dict(name, verts, tris, tx, ty, plate)."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"'
             + (' xmlns:BambuStudio="http://schemas.bambulab.com/package/2021"' if bambu else "") + '>']
    meta = {"Title": title, "Designer": "ultrasonic-radar-scanner / render_cad.py",
            "Description": "Generated from cad/build_radar.py. Educational sonar - not a safety device.",
            "CreationDate": _dt.date.today().isoformat(), "LicenseTerms": "MIT"}
    if bambu:
        meta["Application"] = "BambuStudio-01.10.00.00"
        meta["BambuStudio:3mfVersion"] = "1"
    for k, v in meta.items():
        lines.append(f' <metadata name="{k}">{escape(v)}</metadata>')
    lines.append(" <resources>")
    for i, o in enumerate(objects, start=1):
        lines.append(f'  <object id="{i}" name="{escape(o["name"])}" type="model">')
        lines.append("   <mesh>\n    <vertices>")
        lines.extend(f'     <vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in o["verts"])
        lines.append("    </vertices>\n    <triangles>")
        lines.extend(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in o["tris"])
        lines.append("    </triangles>\n   </mesh>\n  </object>")
    lines.append(" </resources>\n <build>")
    for i, o in enumerate(objects, start=1):
        lines.append(f'  <item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 {o["tx"]:.4f} {o["ty"]:.4f} 0"'
                     + (' printable="1"' if bambu else "") + "/>")
    lines.append(" </build>\n</model>\n")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", "\n".join(lines))
        if bambu and plates:
            cfg = ['<?xml version="1.0" encoding="UTF-8"?>', "<config>"]
            for i, o in enumerate(objects, start=1):
                cfg += [f'  <object id="{i}">',
                        f'    <metadata key="name" value="{escape(o["name"])}"/>',
                        '    <metadata key="extruder" value="1"/>',
                        f'    <part id="{i}" subtype="normal_part">',
                        f'      <metadata key="name" value="{escape(o["name"])}"/>',
                        "    </part>", "  </object>"]
            for p_idx, (pname, members) in enumerate(plates.items(), start=1):
                cfg += ["  <plate>", f'    <metadata key="plater_id" value="{p_idx}"/>',
                        f'    <metadata key="plater_name" value="{pname}"/>',
                        '    <metadata key="locked" value="false"/>']
                for i, o in enumerate(objects, start=1):
                    if o["name"] in members:
                        cfg += ["    <model_instance>",
                                f'      <metadata key="object_id" value="{i}"/>',
                                '      <metadata key="instance_id" value="0"/>',
                                f'      <metadata key="identify_id" value="{100 + i}"/>',
                                "    </model_instance>"]
                cfg.append("  </plate>")
            cfg.append("</config>\n")
            z.writestr("Metadata/model_settings.config", "\n".join(cfg))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-sweep", action="store_true", help="skip the slow sweep-clearance check")
    args = ap.parse_args()

    for d in ("step", "stl", "3mf"):
        (CAD / d).mkdir(parents=True, exist_ok=True)

    report = {"generated": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
              "status": "RECORDED geometry checks only - nothing here is physical validation",
              "cadquery": cq.__version__, "parts": {}, "plates": {}, "interference": {},
              "sweep": {}, "checks": []}

    def check(name, ok, detail=""):
        report["checks"].append({"check": name, "pass": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))

    print("building parts ...")
    parts = M.build_all()
    shapes = {n: solid(p) for n, p in parts.items()}
    refs = {n: solid(f()) for n, f in M.REFERENCE_BUILDERS.items()}

    # ---- exports ----------------------------------------------------------
    printed = {}
    for n, wp in parts.items():
        cq.exporters.export(wp, str(CAD / "step" / f"{n}.step"))
        pp = M.to_print_pose(n, wp)
        printed[n] = solid(pp)
        cq.exporters.export(pp, str(CAD / "stl" / f"{n}.stl"), tolerance=STL_TOL, angularTolerance=STL_ANG)
        s = shapes[n]
        nsol = len(wp.solids().vals())
        report["parts"][n] = {"assembly_bbox": bbox(s), "print_bbox": bbox(printed[n]),
                              "volume_mm3": round(s.Volume(), 1), "valid": s.isValid(), "solids": nsol,
                              "print_note": M.PRINT_POSES[n].note}
        check(f"{n}: valid single solid", s.isValid() and nsol == 1, f"solids={nsol}")

    asm = cq.Assembly(name="radar")
    for n in M.REQUIRED_PARTS:
        asm.add(parts[n], name=n)
    asm.save(str(CAD / "step" / "assembly.step"))

    # ---- nominal dimension checks ---------------------------------------------
    for n, nom in M.NOMINAL.items():
        got = sorted(report["parts"][n]["print_bbox"][k] for k in "xyz")
        ok = all(abs(a - b) <= 0.6 for a, b in zip(got, sorted(nom)))
        check(f"{n}: matches design size {tuple(round(v, 1) for v in nom)}", ok, "got " + " x ".join(f"{v:.1f}" for v in got))

    # ---- plates -------------------------------------------------------------
    bed_w, bed_d, bed_h = M.A1_MINI_BED
    all_plates = {**M.PLATES, **M.OPTIONAL_PLATE, **M.STAGE_PLATES}
    positions = {}
    for pname, members in all_plates.items():
        items = []
        for n in members:
            b = report["parts"][n]["print_bbox"]
            items.append((n, b["x"], b["y"]))
            check(f"{pname}/{n}: height fits A1 mini", b["z"] <= bed_h, f"z={b['z']:.1f}")
        try:
            pos = shelf_pack(items, bed_w, bed_d)
            check(f"{pname}: parts fit {bed_w:.0f}x{bed_d:.0f} with {PLATE_MARGIN} mm margin", True)
        except RuntimeError as e:
            check(f"{pname}: parts fit bed", False, str(e))
            raise
        ext = []
        for n, (cx, cy, rot) in pos.items():
            b = report["parts"][n]["print_bbox"]
            w, d = (b["y"], b["x"]) if rot else (b["x"], b["y"])
            ext.append((cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2))
        dx = bed_w / 2 - (min(e[0] for e in ext) + max(e[1] for e in ext)) / 2
        dy = bed_d / 2 - (min(e[2] for e in ext) + max(e[3] for e in ext)) / 2
        pos = {n: (cx + dx, cy + dy, rot) for n, (cx, cy, rot) in pos.items()}
        positions[pname] = pos
        report["plates"][pname] = {n: {"center_xy": [round(v[0], 2), round(v[1], 2)], "turned_90": v[2]}
                                   for n, v in pos.items()}

    # ---- 3MF ------------------------------------------------------------------
    mesh_cache = {n: tessellate(printed[n]) for n in parts}

    def objs_for(pname, x_off=0.0):
        out = []
        for n, (cx, cy, rot) in positions[pname].items():
            v, t = mesh_cache[n]
            if rot:
                v = [(-y, x, z) for x, y, z in v]
            out.append(dict(name=n, verts=v, tris=t, tx=cx + x_off, ty=cy, plate=pname))
        return out

    try:
        import trimesh
        for n, (v, t) in mesh_cache.items():
            tm = trimesh.Trimesh(vertices=v, faces=t, process=True)
            check(f"{n}: print mesh watertight, outward normals", tm.is_watertight and tm.volume > 0,
                  f"volume {tm.volume:.0f} mm^3")
    except ImportError:
        print("trimesh not installed - skipping mesh checks")

    for old in (CAD / "3mf").glob("*.3mf"):
        old.unlink()
    multi = objs_for("P1") + objs_for("P2", BAMBU_PLATE_STRIDE)
    write_3mf(CAD / "3mf" / "radar_a1mini_multiplate.3mf", multi, plates=M.PLATES, bambu=True,
              title="Radar V6 - A1 mini plates P1 + P2")
    for pname in all_plates:
        write_3mf(CAD / "3mf" / f"plate_{pname}.3mf", objs_for(pname), title=f"Radar V6 - plate {pname}")

    # ---- static interference (assembly) -------------------------------------
    allshapes = {**shapes, **refs}
    for a, b in M.INTERFERENCE_PAIRS:
        v = inter_volume(allshapes[a], allshapes[b])
        report["interference"][f"{a} x {b}"] = round(v, 3)
        allow = M.INTERFERENCE_ALLOW.get((a, b))
        if allow:
            check(f"press fit only: {a} x {b}", 0 < v <= allow, f"{v:.3f} mm^3, designed <= {allow}")
        else:
            check(f"no overlap: {a} x {b}", v < 0.5, f"{v:.3f} mm^3")
    a, b = M.PEG_PAIR
    v = inter_volume(allshapes[a], allshapes[b])
    report["interference"][f"{a} x {b} (pegs in holes)"] = round(v, 3)
    check("CYD sits on the bezel pegs without overlap", v < 0.5, f"{v:.3f} mm^3")

    def dist(a, b):
        try:
            return round(allshapes[a].distance(allshapes[b]), 3)
        except Exception:
            return float("nan")

    clear = {
        "horn foot -> roof (mm)": round(M.Z_FOOT0 - M.H, 3),
        "head bottom -> roof (mm)": round(M.Z_HEAD0 - M.H, 3),
        "screen glass -> bezel back (mm)": round(M.CYD_STANDOFF - (M.CYD_GLASS_TOP - M.CYD_PCB_T), 3),
        "servo gear boss below roof top (mm)": round(M.H - (M.Z_FLANGE_BOT + M.SERVO_BOSS_ABOVE), 3),
        "CYD -> servo min distance": dist("ref_cyd", "ref_servo_sg90"),
        "CYD -> base min distance": dist("ref_cyd", "03_base"),
        "CYD -> shell min distance": dist("ref_cyd", "01_shell"),
        "servo -> base min distance": dist("ref_servo_sg90", "03_base"),
    }
    report["clearances"] = clear
    for k, v in clear.items():
        check(f"clearance >= 0: {k}", v == v and v >= 0, f"{v}")

    # ---- sweep clearance: head rotated through the commanded travel + margin ----
    if not args.skip_sweep:
        ax = cq.Vector(M.SWEEP_AXIS[0], M.SWEEP_AXIS[1], 0)
        worst = {}
        angles = list(range(-M.SWEEP_MARGIN_DEG, M.SWEEP_MARGIN_DEG + 1, 15))
        for label, names in M.SWEEP_MOVERS.items():
            mover = cq.Workplane().add(allshapes[names[0]])
            for n in names[1:]:
                mover = mover.union(cq.Workplane().add(allshapes[n]))
            mover = solid(mover)
            for deg in angles:
                mv = mover.rotate(ax, ax + cq.Vector(0, 0, 1), deg)
                for fname in M.SWEEP_FIXED:
                    if label == "horn" and fname == "ref_servo_sg90":
                        continue  # the horn rides on the spline
                    key = f"{label} vs {fname}"
                    worst[key] = max(worst.get(key, 0.0), inter_volume(mv, allshapes[fname]))
        report["sweep"] = {"angles_deg_from_centre": angles,
                           "max_overlap_mm3": {k: round(v, 3) for k, v in worst.items()}}
        for k, v in worst.items():
            check(f"sweep +/-{M.SWEEP_MARGIN_DEG} deg clear: {k}", v < 0.5, f"max {v:.3f} mm^3")

    # ---- checksums ----------------------------------------------------------
    sums = {}
    for f in sorted((CAD / "stl").glob("*.stl")) + sorted((CAD / "step").glob("*.step")) + sorted((CAD / "3mf").glob("*.3mf")):
        sums[str(f.relative_to(ROOT))] = hashlib.sha256(f.read_bytes()).hexdigest()
    report["sha256"] = sums
    report["summary"] = {"total": len(report["checks"]),
                         "passed": sum(c["pass"] for c in report["checks"])}
    (CAD / "geometry_report.json").write_text(json.dumps(report, indent=2) + "\n")
    s = report["summary"]
    print(f"\n{s['passed']}/{s['total']} recorded geometry checks passed -> cad/geometry_report.json")
    return 0 if s["passed"] == s["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
