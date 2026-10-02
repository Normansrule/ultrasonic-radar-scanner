#!/usr/bin/env python3
"""
Package the repository as a ZIP with one top-level folder
(ultrasonic-radar-scanner/), excluding .git and build/render caches, and write
SHA256SUMS next to it.

Usage: python scripts/make_release_zip.py [--version v5.1.0] [--out dist] [--name ultrasonic-radar-scanner.zip]
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP = "ultrasonic-radar-scanner"
EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", "dist", ".venv", "venv", ".idea", ".vscode", "node_modules"}
EXCLUDE_REL = {"app/web", "app/dist", "firmware/Radar_V5/build"}
EXCLUDE_SUFFIX = {".pyc", ".elf", ".map"}


def files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = Path(dirpath).relative_to(ROOT).as_posix()
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS
                             and f"{rel_dir}/{d}".lstrip("./") not in EXCLUDE_REL)
        for f in sorted(filenames):
            p = Path(dirpath) / f
            if p.suffix in EXCLUDE_SUFFIX or p.name.endswith(".ino.bin") or p.name == ".DS_Store":
                continue
            yield p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="")
    ap.add_argument("--out", default="dist")
    ap.add_argument("--name", default="")
    a = ap.parse_args()
    out = (ROOT / a.out) if not Path(a.out).is_absolute() else Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    name = a.name or (f"{TOP}-{a.version}.zip" if a.version else f"{TOP}.zip")
    zpath = out / name
    n = 0
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files():
            rel = p.relative_to(ROOT)
            if rel.parts[0] == a.out.strip("/").split("/")[0]:
                continue
            info = zipfile.ZipInfo(f"{TOP}/{rel.as_posix()}", date_time=(2026, 10, 2, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if os.access(p, os.X_OK) else 0o644) << 16
            z.writestr(info, p.read_bytes())
            n += 1
    sbom = ROOT / "sbom" / "toolchain.cdx.json"
    if sbom.exists():
        shutil.copy2(sbom, out / "toolchain.cdx.json")
    sums = []
    for f in sorted(out.iterdir()):
        if f.is_file() and f.name != "SHA256SUMS":
            sums.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}")
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    print(f"{zpath.relative_to(ROOT) if zpath.is_relative_to(ROOT) else zpath}: {n} files")
    print((out / "SHA256SUMS").read_text())


if __name__ == "__main__":
    main()
