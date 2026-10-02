"""Every requirement has a verification method and evidence that exists in VALIDATION.md,
and the Status column / status graphic are up to date."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_traceability_up_to_date():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "gen_traceability.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_requirement_is_verifiable():
    text = (ROOT / "docs" / "REQUIREMENTS.md").read_text()
    block = text.split("<!-- REQS:BEGIN -->")[1].split("<!-- REQS:END -->")[0]
    ids = []
    for line in block.strip().splitlines()[2:]:
        rid, req, method, evidence, status = [c.strip() for c in line.strip("|").split("|")]
        ids.append(rid)
        assert re.fullmatch(r"RQ-(F|P|S|I|M|SW|O)-\d\d", rid), rid
        assert set(m.strip() for m in method.split(",")) <= {"I", "A", "D", "T"}, rid
        assert evidence, rid
    assert len(ids) == len(set(ids))


def test_every_physical_test_traces_to_a_requirement():
    val = (ROOT / "docs" / "VALIDATION.md").read_text()
    req = (ROOT / "docs" / "REQUIREMENTS.md").read_text()
    tests = set(re.findall(r"^\| (T-[A-Z]+-\d+) \|", val, re.M))
    orphans = sorted(t for t in tests if t not in req)
    assert not orphans, f"physical tests not linked to any requirement: {orphans}"
