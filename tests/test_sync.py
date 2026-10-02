"""Keeps docs/WIRING.md, the firmware and tests/radar_math.py in agreement, and
encodes the wiring safety rules as checks. Run: python -m pytest tests/"""
import re
from collections import defaultdict
from pathlib import Path

import radar_math as rm

ROOT = Path(__file__).resolve().parents[1]
INO = (ROOT / "firmware" / "Radar_V5" / "Radar_V5.ino").read_text(encoding="utf-8")
WIRING = (ROOT / "docs" / "WIRING.md").read_text(encoding="utf-8")


def table(tag):
    block = WIRING.split(f"<!-- {tag}:BEGIN -->")[1].split(f"<!-- {tag}:END -->")[0]
    rows = [l.strip() for l in block.strip().splitlines() if l.strip().startswith("|")]
    head = [c.strip() for c in rows[0].strip("|").split("|")]
    return [dict(zip(head, [c.strip() for c in r.strip("|").split("|")])) for r in rows[2:]]


NETLIST = table("NETLIST")
PINMAP = table("PINMAP")
NETS = defaultdict(list)
for r in NETLIST:
    NETS[r["Net"]].append(r["Pin"])


def fw_const(name):
    m = re.search(rf"static constexpr \w+ {name}\s*=\s*([^;]+);", INO)
    assert m, f"{name} not found in firmware"
    v = m.group(1).strip().rstrip("f")
    return {"true": True, "false": False}.get(v, v)


# ---------------------------------------------------------------- firmware <-> docs
def test_pin_constants_match_pinmap():
    for r in PINMAP:
        assert int(fw_const(r["Firmware constant"])) == int(r["GPIO"]), r


def test_every_firmware_pin_is_documented():
    fw_pins = set(re.findall(r"static constexpr int (PIN_\w+)\s*=", INO))
    assert fw_pins == {r["Firmware constant"] for r in PINMAP}


def test_netlist_esp32_gpios_match_pinmap():
    gpio_rows = {int(r["Pin"].split("GPIO")[1]): r["Net"] for r in NETLIST if r["Pin"].startswith("ESP32.GPIO")}
    assert gpio_rows == {int(r["GPIO"]): r["Net"] for r in PINMAP}


def test_math_module_mirrors_firmware_constants():
    for name in ("SWEEP_MIN_DEG", "SWEEP_MAX_DEG", "SWEEP_STEP_DEG", "SETTLE_MS", "SERVO_FREQ_HZ",
                 "SERVO_RES_BITS", "SERVO_US_AT_0", "SERVO_US_AT_180", "SERVO_US_GUARD_MIN",
                 "SERVO_US_GUARD_MAX", "TFT_SPI_HZ"):
        assert float(fw_const(name)) == float(getattr(rm, name)), name
    for name in ("MAX_RANGE_CM", "AIR_TEMP_C"):
        assert float(fw_const(name)) == getattr(rm, name), name


def test_shipping_defaults():
    assert fw_const("CENTER_ONLY") is False, "CENTER_ONLY must be false in the committed firmware"
    assert fw_const("CALIBRATE_SERVO") is False
    assert "WiFi" not in INO and "WiFi.h" not in INO, "no Wi-Fi in this project"


# ---------------------------------------------------------------- ESP32 pin rules
FLASH_PINS = set(range(6, 12))
STRAPPING = {0, 2, 5, 12, 15}
INPUT_ONLY = {34, 35, 36, 37, 38, 39}


def test_no_flash_or_strapping_pins():
    for r in PINMAP:
        g = int(r["GPIO"])
        assert g not in FLASH_PINS, r
        assert g not in STRAPPING, r


def test_outputs_not_on_input_only_pins():
    for r in PINMAP:
        if r["Direction"].startswith("output"):
            assert int(r["GPIO"]) not in INPUT_ONLY, r


def test_lcd_cs_not_gpio5():
    assert int(fw_const("PIN_TFT_CS")) != 5


# ---------------------------------------------------------------- wiring safety rules
def test_each_pin_listed_once_and_nets_have_two_ends():
    pins = [r["Pin"] for r in NETLIST]
    assert len(pins) == len(set(pins))
    for net, members in NETS.items():
        assert len(members) >= 2, f"{net} is connected to only {members}"


def test_echo_5v_never_touches_the_esp32():
    assert set(NETS["ECHO_5V"]) == {"SR04.ECHO", "R1.1"}
    assert "ESP32.GPIO26" in NETS["ECHO_3V"]
    assert {"R1.2", "R2.1"} <= set(NETS["ECHO_3V"]) and "R2.2" in NETS["GND"]


def test_fuse_is_first_thing_on_battery_positive():
    assert set(NETS["BAT_RAW"]) == {"CELL.+", "FUSE.A"}
    assert set(NETS["BAT_POS"]) == {"FUSE.B", "DFR1026.BAT+"}


def test_bare_cell_never_feeds_a_load():
    for net in ("BAT_RAW", "BAT_POS", "BAT_NEG"):
        assert not any(p.split(".")[0] in {"ESP32", "SERVO", "SR04", "LCD"} for p in NETS[net]), net


def test_switch_cuts_load_not_charger():
    assert set(NETS["OUT_5V"]) == {"DFR1026.OUT_5V", "SW.1"}
    assert "SW.2" in NETS["LOAD_5V"]
    for net in ("USB_5V", "BAT_POS", "BAT_RAW"):
        assert not any(p.startswith("SW.") for p in NETS[net])


def test_servo_and_sensor_on_5v_not_3v3():
    assert "SERVO.RED" in NETS["LOAD_5V"] and "SR04.VCC" in NETS["LOAD_5V"]
    assert not any(p.startswith(("SERVO.", "SR04.")) for p in NETS["3V3"])


def test_bulk_cap_on_load_rail():
    assert "C1.+" in NETS["LOAD_5V"] and "C1.-" in NETS["GND"]


def test_rear_usb_has_no_data_lines():
    assert not any(p.startswith("USBC.D") for p in NETS.keys()) and \
        not any(r["Pin"].startswith(("USBC.D+", "USBC.D-")) for r in NETLIST)


def test_no_sd_card_wiring():
    assert not any("SD" in r["Pin"].split(".")[1] for r in NETLIST if r["Pin"].startswith("LCD."))


def test_compile_records_match_current_firmware():
    """A compile record is only evidence for the exact source it was made from."""
    import hashlib
    h = hashlib.sha256((ROOT / "firmware" / "Radar_V5" / "Radar_V5.ino").read_bytes()).hexdigest()
    for c in ("3", "2"):
        rec = (ROOT / "docs" / "validation" / f"compile_core{c}.txt").read_text(encoding="utf-8")
        assert f"source_sha256: {h}" in rec, (
            f"compile_core{c}.txt was made from a different Radar_V5.ino - recompile and update the record")
        assert "warnings: 0" in rec and "errors: 0" in rec
