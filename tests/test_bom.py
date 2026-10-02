"""BOM fastener counts must add up to their listed uses."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOM = (ROOT / "docs" / "BOM.md").read_text(encoding="utf-8")


def fasteners():
    block = BOM.split("<!-- FASTENERS:BEGIN -->")[1].split("<!-- FASTENERS:END -->")[0]
    rows = [l for l in block.strip().splitlines() if l.startswith("|")][2:]
    out = {}
    for r in rows:
        qty, item, used = [c.strip() for c in r.strip("|").split("|")]
        out[item] = (int(qty), used)
    return out


F = fasteners()


def test_m2_only():
    for item in F:
        assert not re.search(r"\bM[3-9]\b|M[3-9]×", item), item


def test_m2x8_breakdown_sums():
    qty, used = F["M2×8 screw"]
    assert qty == 12
    assert sum(int(n) for n in re.findall(r"(\d+) [a-z]", used)) == 12


def test_counts_match_design():
    assert F["M2×6 screw"][0] == 2        # two horn arm holes (HORN_SCREW_R, +/-X)
    assert F["M2×12 screw"][0] == 4       # four HC-SR04 corner holes
    assert F["M2×20 screw"][0] == 1       # one mast cross-bolt
    assert F["M2 hex nut"][0] >= 4 + 1    # sensor nuts + cross-bolt nut
    assert 6 <= F["M2 washer"][0] <= 10


def test_safety_parts_present():
    for needle in ("3 A fuse", "Protected 18650", "5.1 kΩ pull-downs on both CC1 and CC2",
                   "≥2 A at 5 V", "1000 µF"):
        assert needle in BOM, needle


def test_excluded_features_stated():
    assert "Wi-Fi" in BOM and "fuel" in BOM
