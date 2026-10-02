"""The committed CAD build products must come from the current source and pass
every RECORDED geometry check. Regenerate with: python scripts/render_cad.py"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = json.loads((ROOT / "cad" / "geometry_report.json").read_text())
PARTS = ["01_body", "02_front_panel", "03_roof", "04_rotor_hub", "05_turret_keeper",
         "06_sensor_head", "07_keeper_shim_0p4mm", "08_fit_test_coupon"]


def test_all_recorded_checks_pass():
    failed = [c for c in REPORT["checks"] if not c["pass"]]
    assert not failed, failed
    assert REPORT["summary"]["passed"] == REPORT["summary"]["total"] >= 70


def test_every_part_exported():
    for p in PARTS:
        assert (ROOT / "cad" / "stl" / f"{p}.stl").exists(), p
        assert (ROOT / "cad" / "step" / f"{p}.step").exists(), p
    assert (ROOT / "cad" / "step" / "assembly_v5.step").exists()
    assert (ROOT / "cad" / "3mf" / "radar_v5_a1mini_multiplate.3mf").exists()
    for plate in ("P1", "P2", "P3_optional_shim", "S1_fit_coupon", "S2_servo_fit_subset"):
        assert (ROOT / "cad" / "3mf" / f"plate_{plate}.3mf").exists(), plate


def test_stl_files_match_report_hashes():
    """Fails if an STL was edited by hand or not regenerated after a CAD change."""
    for rel, digest in REPORT["sha256"].items():
        if rel.endswith(".stl"):
            got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
            assert got == digest, f"{rel} differs from cad/geometry_report.json - re-run scripts/render_cad.py"


def test_plates_contain_required_parts():
    assert set(REPORT["plates"]["P1"]) == {"01_body", "02_front_panel"}
    assert set(REPORT["plates"]["P2"]) == {"03_roof", "04_rotor_hub", "05_turret_keeper",
                                           "06_sensor_head", "08_fit_test_coupon"}


def test_sweep_was_checked():
    assert REPORT["sweep"], "sweep clearance check was skipped"
    assert all(v < 0.5 for v in REPORT["sweep"]["max_overlap_mm3"].values())
