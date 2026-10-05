"""Keeps docs/WIRING.md, the firmware and tests/radar_math.py in agreement, and
encodes the wiring safety rules as checks. Run: python -m pytest tests/"""
import re
from collections import defaultdict
from pathlib import Path

import radar_math as rm

ROOT = Path(__file__).resolve().parents[1]
INO = (ROOT / "firmware" / "Radar_V6" / "Radar_V6.ino").read_text(encoding="utf-8")
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


def test_netlist_gpios_match_pinmap():
    """Every IOxx pin in the net list is the GPIO the pin map gives for that net's firmware constant."""
    net_of_const = {"PIN_TRIG": "TRIG", "PIN_ECHO": "ECHO", "PIN_SERVO": "SERVO_PWM"}
    gpio_rows = {int(r["Pin"].split(".IO")[1]): r["Net"] for r in NETLIST if ".IO" in r["Pin"]}
    assert gpio_rows == {int(r["GPIO"]): net_of_const[r["Firmware constant"]] for r in PINMAP
                         if r["Where"] != "on-board"}


def test_connector_pins_are_on_the_documented_connector():
    for r in PINMAP:
        if r["Where"] != "on-board":
            assert f'{r["Where"]}.IO{r["GPIO"]}' in {n["Pin"] for n in NETLIST}, r


def test_math_module_mirrors_firmware_constants():
    for name in ("SWEEP_MIN_DEG", "SWEEP_MAX_DEG", "SWEEP_STEP_DEG", "SETTLE_MS", "SERVO_FREQ_HZ",
                 "SERVO_RES_BITS", "SERVO_US_AT_0", "SERVO_US_AT_180", "SERVO_US_GUARD_MIN",
                 "SERVO_US_GUARD_MAX", "TFT_SPI_HZ"):
        assert float(fw_const(name)) == float(getattr(rm, name)), name
    for name in ("MAX_RANGE_CM", "AIR_TEMP_C", "DETECTION_TTL_MS"):
        assert float(fw_const(name)) == getattr(rm, name), name


def test_shipping_defaults():
    assert fw_const("CENTER_ONLY") is False, "CENTER_ONLY must be false in the committed firmware"
    assert fw_const("CALIBRATE_SERVO") is False
    assert "WiFi" not in INO and "WiFi.h" not in INO, "no Wi-Fi in this project"


# ---------------------------------------------------------------- ESP32 pin rules
FLASH_PINS = set(range(6, 12))
STRAPPING = {0, 2, 5, 12, 15}
INPUT_ONLY = {34, 35, 36, 37, 38, 39}
OFF_BOARD = [r for r in PINMAP if r["Where"] != "on-board"]


def test_no_flash_pins_and_no_strapping_pins_off_board():
    """The CYD itself uses strapping pins 2, 12 and 15 for the display; our wires must not."""
    for r in PINMAP:
        assert int(r["GPIO"]) not in FLASH_PINS, r
    for r in OFF_BOARD:
        assert int(r["GPIO"]) not in STRAPPING, r


def test_outputs_not_on_input_only_pins():
    for r in PINMAP:
        if r["Direction"].startswith("output"):
            assert int(r["GPIO"]) not in INPUT_ONLY, r


def test_echo_on_input_only_pin_is_fine():
    assert int(fw_const("PIN_ECHO")) in INPUT_ONLY  # 35 can only be an input - that is all ECHO needs


# ---------------------------------------------------------------- wiring safety rules
def test_seven_wires_two_ends_each():
    wires = defaultdict(list)
    for r in NETLIST:
        wires[r["Wire"]].append(r["Pin"])
    assert sorted(wires) == [f"W{i}" for i in range(1, 8)]
    for w, ends in wires.items():
        assert len(ends) == 2, w
        cyd_end = [e for e in ends if e.split(".")[0] in {"CN1", "P3", "P1"}]
        assert len(cyd_end) == 1, f"{w} must run from a CYD connector to a module"


def test_each_pin_listed_once_and_nets_have_two_ends():
    pins = [r["Pin"] for r in NETLIST]
    assert len(pins) == len(set(pins))
    for net, members in NETS.items():
        assert len(members) >= 2, f"{net} is connected to only {members}"


def test_sensor_runs_from_3v3_so_echo_is_3v3():
    assert set(NETS["3V3"]) == {"CN1.3V3", "SENSOR.VCC"}
    assert set(NETS["ECHO"]) == {"P3.IO35", "SENSOR.ECHO"}
    assert rm.SENSOR_VCC == 3.3


def test_servo_on_vin_not_3v3():
    assert set(NETS["VIN_5V"]) == {"P1.VIN", "SERVO.+5V"}
    assert not any(p.startswith("SERVO.") for p in NETS["3V3"])


def test_usb_serial_and_backlight_pins_untouched():
    used = {r["Pin"] for r in NETLIST}
    for p in ("P1.TX", "P1.RX", "P3.IO21", "P3.IO22"):
        assert p not in used, p


def test_common_ground():
    assert {"CN1.GND", "SENSOR.GND", "P1.GND", "SERVO.GND"} == set(NETS["GND"])


def test_compile_records_match_current_firmware():
    """A compile record is only evidence for the exact source it was made from."""
    import hashlib
    h = hashlib.sha256((ROOT / "firmware" / "Radar_V6" / "Radar_V6.ino").read_bytes()).hexdigest()
    for c in ("3", "2"):
        rec = (ROOT / "docs" / "validation" / f"compile_core{c}.txt").read_text(encoding="utf-8")
        assert f"source_sha256: {h}" in rec, (
            f"compile_core{c}.txt was made from a different Radar_V6.ino - recompile and update the record")
        assert "warnings: 0" in rec and "errors: 0" in rec
