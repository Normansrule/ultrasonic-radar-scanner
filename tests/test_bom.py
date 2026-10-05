"""The BOM stays minimal, honest about prices, and consistent with the design."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOM = (ROOT / "docs" / "BOM.md").read_text(encoding="utf-8")


def table(start, end=None):
    block = BOM.split(start, 1)[1]
    block = block.split(end)[0] if end else block.split("\n## ", 1)[0]
    rows = [l for l in block.strip().splitlines() if l.startswith("|")]
    head = [c.strip() for c in rows[0].strip("|").split("|")]
    return [dict(zip(head, [c.strip() for c in r.strip("|").split("|")])) for r in rows[2:]]


ELEC = table("## Electronics")
FAST = table("<!-- FASTENERS:BEGIN -->", "<!-- FASTENERS:END -->")


def test_five_required_items_one_optional():
    required = [r for r in ELEC if "optional" not in r["Qty"]]
    optional = [r for r in ELEC if "optional" in r["Qty"]]
    assert len(required) == 5 and len(optional) == 1


def test_core_modules_present():
    text = " ".join(r["Part"] for r in ELEC)
    for needle in ("ESP32-2432S028R", "RCWL-1601", "HC-SR04P", "SG90"):
        assert needle in text, needle


def test_sensor_must_be_3v3_capable():
    sensor = next(r for r in ELEC if "RCWL-1601" in r["Part"])
    assert "3 V" in sensor["What to check before you buy"] and "fallback" in sensor["What to check before you buy"]


def test_no_battery_no_loose_screws():
    for word in ("18650", "fuse", "M2", "M3"):
        assert not any(word in r["Part"] for r in ELEC), word
    for r in FAST:
        assert "SG90" in r["Item"], r  # only the screws that come with the servo


def test_prices_are_labelled_estimates():
    assert "estimates" in BOM.split("## Electronics")[0]
    for r in ELEC:
        assert re.fullmatch(r"(<\s*)?\d+(–\d+)?", r["Est. US$"]), r
