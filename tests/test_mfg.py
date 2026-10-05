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


def test_seven_wires():
    wires = rows("wire_list.csv")
    assert [w["wire"] for w in wires] == [f"W{i}" for i in range(1, 8)]
    for w in wires:
        assert w["from"] != w["to"]


def test_bom_core_parts():
    bom = {r["id"]: r for r in rows("bom.csv")}
    assert "ESP32-2432S028R" in bom["E1"]["part"]
    assert "RCWL-1601" in bom["E2"]["part"]
    assert "SG90" in bom["E3"]["part"]
    assert bom["E6"]["optional"] == "yes"
    assert all(r["est_usd"] for r in bom.values())


def test_printed_parts_point_at_real_files():
    parts = rows("printed_parts.csv")
    assert len(parts) == 5
    for p in parts:
        assert (ROOT / p["stl"]).exists() and (ROOT / p["step"]).exists()


def test_build_packet_present():
    assert (MFG / "build_packet.pdf").stat().st_size > 100_000
    for n in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "LICENSE-DejaVu.txt"):
        assert (MFG / "fonts" / n).exists()
