"""The committed CAD build products must come from the current source and pass
every RECORDED geometry check. Regenerate with: python scripts/render_cad.py"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = json.loads((ROOT / "cad" / "geometry_report.json").read_text())
PARTS = ["01_shell", "02_bezel", "03_base", "04_head", "05_fit_coupon"]


def test_all_recorded_checks_pass():
    failed = [c for c in REPORT["checks"] if not c["pass"]]
    assert not failed, failed
    assert REPORT["summary"]["passed"] == REPORT["summary"]["total"] >= 40


def test_every_part_exported():
    assert sorted(REPORT["parts"]) == PARTS
    for p in PARTS:
        assert (ROOT / "cad" / "stl" / f"{p}.stl").exists(), p
        assert (ROOT / "cad" / "step" / f"{p}.step").exists(), p
    assert (ROOT / "cad" / "step" / "assembly.step").exists()
    assert (ROOT / "cad" / "3mf" / "radar_a1mini_multiplate.3mf").exists()
    for plate in ("P1", "P2", "S1_fit_coupon"):
        assert (ROOT / "cad" / "3mf" / f"plate_{plate}.3mf").exists(), plate


def test_stl_files_match_report_hashes():
    """Fails if an STL was edited by hand or not regenerated after a CAD change."""
    for rel, digest in REPORT["sha256"].items():
        if rel.endswith(".stl"):
            got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
            assert got == digest, f"{rel} differs from cad/geometry_report.json - re-run scripts/render_cad.py"


def test_plates_contain_required_parts():
    assert set(REPORT["plates"]["P1"]) == {"01_shell"}
    assert set(REPORT["plates"]["P2"]) == {"02_bezel", "03_base", "04_head"}
    assert set(REPORT["plates"]["S1_fit_coupon"]) == {"05_fit_coupon"}


def test_four_printed_parts_fit_an_a1_mini_and_need_no_supports():
    for p in PARTS[:4]:
        b = REPORT["parts"][p]["print_bbox"]
        assert max(b["x"], b["y"]) <= 168 and b["z"] <= 180, p
        assert "support" not in REPORT["parts"][p]["print_note"] or "no supports" in REPORT["parts"][p]["print_note"]


def test_sweep_was_checked():
    assert REPORT["sweep"], "sweep clearance check was skipped"
    assert all(v < 0.5 for v in REPORT["sweep"]["max_overlap_mm3"].values())
