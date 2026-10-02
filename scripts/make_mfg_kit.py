#!/usr/bin/env python3
"""
Package the manufacturing kit: everything a builder or a small batch maker needs,
without the source tree.

  ultrasonic-radar-scanner-mfg-kit-<version>/
    README_FIRST.txt            what is inside, in build order
    build_packet.pdf            printable traveller with tick boxes
    bom.csv, printed_parts.csv, wiring_pins.csv, wire_list.csv
    3mf/  stl/  step/           print-ready plates, single parts, editable CAD
    diagrams/                   wiring (SVG + PNG), ECHO/fuse callout, parts kit, plates, exploded view
    firmware/                   ESP32 images (only when --firmware-dir has them)
    LICENSE, CREDITS.md, REQUIREMENTS.md, VALIDATION.md

Usage: python scripts/make_mfg_kit.py --version v5.2.0 --out dist [--firmware-dir dist]
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DIAGRAMS = ["wiring_full.svg", "wiring_power.svg", "wiring_signal.svg", "callout_echo_divider_fuse.svg",
            "bom_overview.svg", "build_flow.svg", "live_link_tap.svg", "exploded_v5.png", "assembly_v5.png",
            "layout_v5.png", "plate_P1.png", "plate_P2.png", "plate_S1_fit_coupon.png", "plate_S2_servo_fit_subset.png",
            "png/wiring_full.png", "png/callout_echo_divider_fuse.png", "png/bom_overview.png", "png/build_flow.png"]

README = """ULTRASONIC RADAR SCANNER - MANUFACTURING KIT {version}
Radar V5.1 hardware baseline. Educational ultrasonic (sonar) instrument with a
radar-style display - NOT radio-frequency radar, NOT a safety device.
Nothing in this kit had been physically validated when it was generated:
record your results (VALIDATION.md test IDs) and share them.

BUILD ORDER
 1. build_packet.pdf ........ print it; it is your checklist for every step
 2. bom.csv ................. buy the parts (check each "check_before_buying")
 3. 3mf/plate_S1_fit_coupon.3mf  print the fit coupon FIRST, tune hole sizes
 4. 3mf/plate_S2_servo_fit_subset.3mf  roof + hub + keeper, test the servo fit
 5. wire_list.csv ........... power wires first (no ESP32), then signals
 6. firmware/ ............... flash radar_v5_esp32_*_merged.bin at 0x0
                              (*_app.bin is the app alone, at 0x10000)
                              (or use the web app's Flash page)
 7. 3mf/radar_v5_a1mini_multiplate.3mf  print the rest (plates P1 + P2)
 8. build_packet.pdf sections 6-7  assembly gates and the physical test sheet

FILES
 3mf/   Bambu Lab A1 mini plates (any slicer opens the plate_*.3mf files)
 stl/   each part alone, already in print orientation, PLA, no supports
 step/  each part in assembled position + assembly_v5.step (editable CAD)
 diagrams/  wiring, ECHO divider + fuse callout, parts kit, plates, views

SAFETY (non-negotiable)
 - 3 A fuse on the battery positive lead.
 - Never connect a bare cell to ESP32 VIN or the servo.
 - ECHO reaches GPIO26 only through the 2.2k / 3.3k divider.
 - Never connect the ESP32's own USB while the battery harness is connected.
 - Do not charge unattended while prototyping.

Source, docs, apps: {repo}
Licence: MIT (see LICENSE). Datasheets and credits: CREDITS.md.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--out", default="dist")
    ap.add_argument("--firmware-dir", default="")
    ap.add_argument("--repo", default="https://github.com/Normansrule/ultrasonic-radar-scanner")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    top = f"ultrasonic-radar-scanner-mfg-kit-{a.version}"
    zpath = out / f"{top}.zip"
    files: list[tuple[Path, str]] = [
        (ROOT / "manufacturing" / "build_packet.pdf", "build_packet.pdf"),
        *[(ROOT / "manufacturing" / n, n) for n in ("bom.csv", "printed_parts.csv", "wiring_pins.csv", "wire_list.csv")],
        *[(p, f"3mf/{p.name}") for p in sorted((ROOT / "cad" / "3mf").glob("*.3mf"))],
        *[(p, f"stl/{p.name}") for p in sorted((ROOT / "cad" / "stl").glob("*.stl"))],
        *[(p, f"step/{p.name}") for p in sorted((ROOT / "cad" / "step").glob("*.step"))],
        *[(ROOT / "hardware" / "diagrams" / n, f"diagrams/{Path(n).name}") for n in DIAGRAMS],
        (ROOT / "LICENSE", "LICENSE"), (ROOT / "CREDITS.md", "CREDITS.md"),
        (ROOT / "docs" / "REQUIREMENTS.md", "REQUIREMENTS.md"), (ROOT / "docs" / "VALIDATION.md", "VALIDATION.md"),
    ]
    if a.firmware_dir:
        for p in sorted(Path(a.firmware_dir).glob("radar_v5_esp32*.bin")):
            files.append((p, f"firmware/{p.name}"))
    missing = [str(p) for p, _ in files if not p.exists()]
    if missing:
        raise SystemExit(f"missing kit files: {missing}")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(f"{top}/README_FIRST.txt", README.format(version=a.version, repo=a.repo))
        for src, arc in files:
            info = zipfile.ZipInfo(f"{top}/{arc}", date_time=(2026, 10, 2, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, src.read_bytes())
    print(f"{zpath.name}: {len(files) + 1} files, {zpath.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
