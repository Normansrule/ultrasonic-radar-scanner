#!/usr/bin/env python3
"""
Write sbom/toolchain.cdx.json — a CycloneDX 1.5 software bill of materials for
the toolchain, generated ONLY from the two pin files:

  firmware/Radar_V5/sketch.yaml   ESP32 cores + Arduino libraries (per profile)
  requirements.txt                Python tooling
  app/package.json + package-lock.json   desktop-app toolchain (Electron, electron-builder, KaTeX)

Usage: python scripts/gen_sbom.py          (write)
       python scripts/gen_sbom.py --check  (fail if the committed SBOM is stale)
"""
from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sbom" / "toolchain.cdx.json"

LIB_REPOS = {
    "Adafruit GFX Library": ("https://github.com/adafruit/Adafruit-GFX-Library", "BSD-2-Clause"),
    "Adafruit ST7735 and ST7789 Library": ("https://github.com/adafruit/Adafruit-ST7735-Library", "MIT"),
    "Adafruit BusIO": ("https://github.com/adafruit/Adafruit_BusIO", "MIT"),
}


def parse_sketch_yaml(text: str):
    """Tiny parser for the fixed layout of sketch.yaml (no PyYAML dependency)."""
    platforms, libs = set(), set()
    for m in re.finditer(r"platform:\s*([\w:]+)\s*\(([\d.]+)\)", text):
        platforms.add((m.group(1), m.group(2)))
    for m in re.finditer(r"^\s*-\s*([A-Za-z][^(\n]+?)\s*\(([\d.]+)\)\s*$", text, re.M):
        if not m.group(1).startswith("platform"):
            libs.add((m.group(1).strip(), m.group(2)))
    return sorted(platforms), sorted(libs)


def parse_requirements(text: str):
    out = []
    for line in text.splitlines():
        line = line.split("#")[0].strip()
        if "==" in line:
            n, v = line.split("==", 1)
            out.append((n.strip(), v.strip()))
    return sorted(out, key=lambda t: t[0].lower())


def build():
    platforms, libs = parse_sketch_yaml((ROOT / "firmware" / "Radar_V5" / "sketch.yaml").read_text())
    reqs = parse_requirements((ROOT / "requirements.txt").read_text())
    comps = []
    for name, ver in platforms:
        comps.append({"type": "framework", "name": name, "version": ver,
                      "purl": f"pkg:github/espressif/arduino-esp32@{ver}",
                      "externalReferences": [{"type": "distribution",
                                              "url": "https://github.com/espressif/arduino-esp32"}],
                      "licenses": [{"license": {"id": "LGPL-2.1-or-later"}}],
                      "properties": [{"name": "role", "value": "firmware toolchain"}]})
    for name, ver in libs:
        url, lic = LIB_REPOS.get(name, ("", "NOASSERTION"))
        slug = url.rsplit("/", 1)[-1] if url else name.replace(" ", "_")
        c = {"type": "library", "name": name, "version": ver,
             "purl": f"pkg:github/adafruit/{slug}@{ver}",
             "properties": [{"name": "role", "value": "firmware library"}]}
        if url:
            c["externalReferences"] = [{"type": "vcs", "url": url}]
        c["licenses"] = [{"license": {"id": lic}}] if lic != "NOASSERTION" else [{"expression": "NOASSERTION"}]
        comps.append(c)
    for name, ver in reqs:
        comps.append({"type": "library", "name": name, "version": ver,
                      "purl": f"pkg:pypi/{name.lower()}@{ver}",
                      "properties": [{"name": "role", "value": "python tooling"}]})
    pkg = json.loads((ROOT / "app" / "package.json").read_text())
    lock = json.loads((ROOT / "app" / "package-lock.json").read_text())
    for name, ver in sorted(pkg.get("devDependencies", {}).items()):
        entry = lock["packages"].get(f"node_modules/{name}", {})
        c = {"type": "framework" if name == "electron" else "library", "name": name, "version": ver,
             "purl": f"pkg:npm/{name}@{ver}",
             "properties": [{"name": "role", "value": "desktop app toolchain"}]}
        if entry.get("integrity"):
            algo, b64 = entry["integrity"].split("-", 1)
            c["hashes"] = [{"alg": {"sha512": "SHA-512", "sha256": "SHA-256", "sha1": "SHA-1"}.get(algo, algo.upper()),
                            "content": __import__("base64").b64decode(b64).hex()}]
        if entry.get("license"):
            c["licenses"] = [{"license": {"id": entry["license"]}}]
        comps.append(c)
    # deterministic serial number so --check is stable
    serial = uuid.uuid5(uuid.NAMESPACE_URL, json.dumps(comps, sort_keys=True))
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{serial}", "version": 1,
        "metadata": {"component": {"type": "application", "name": "ultrasonic-radar-scanner", "version": "5.1",
                                   "licenses": [{"license": {"id": "MIT"}}]},
                     "properties": [{"name": "generated-from", "value": "firmware/Radar_V5/sketch.yaml, requirements.txt, app/package-lock.json"}]},
        "components": comps,
    }


def main():
    text = json.dumps(build(), indent=2) + "\n"
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text() != text:
            print("sbom/toolchain.cdx.json is stale - run: python scripts/gen_sbom.py")
            return 1
        print("SBOM up to date")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(build()['components'])} components)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
