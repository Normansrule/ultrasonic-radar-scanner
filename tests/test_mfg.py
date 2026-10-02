"""Manufacturing exports stay in step with the docs, and the build packet inputs exist."""
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MFG = ROOT / "manufacturing"


def test_exports_up_to_date():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "export_mfg.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def rows(name):
    with open(MFG / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_wire_list_covers_every_pin():
    pins = {r["pin"] for r in rows("wiring_pins.csv")}
    wired = set()
    for w in rows("wire_list.csv"):
        wired |= {w["from"], w["to"]}
    assert pins == wired


def test_every_wire_joins_one_net_once():
    seen = set()
    for w in rows("wire_list.csv"):
        assert w["from"] != w["to"]
        key = frozenset((w["from"], w["to"]))
        assert key not in seen
        seen.add(key)


def test_bom_has_safety_parts_and_fasteners():
    bom = {r["id"]: r for r in rows("bom.csv")}
    assert "fuse" in bom["E10"]["part"].lower()
    assert "protected" in bom["E7"]["part"].lower()
    assert sum(1 for k in bom if k.startswith("F")) == 7


def test_printed_parts_point_at_real_files():
    parts = rows("printed_parts.csv")
    assert len(parts) == 8
    for p in parts:
        assert (ROOT / p["stl"]).exists() and (ROOT / p["step"]).exists()


def test_build_packet_present():
    assert (MFG / "build_packet.pdf").stat().st_size > 100_000
    for n in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "LICENSE-DejaVu.txt"):
        assert (MFG / "fonts" / n).exists()
