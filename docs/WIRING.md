# Wiring — 7 wires, pin by pin (Radar V6)

![Wiring picture](../hardware/diagrams/wiring_picture.svg)

> **Follow the silkscreen labels, not the wire colours.** Cable colours and the pin order printed
> on Cheap Yellow Display (CYD) connectors differ between batches. Read the labels on *your* board
> before plugging anything in.

This page is the **single source of truth**. `python scripts/gen_diagrams.py` draws the diagrams
from the tables below, and `python -m pytest tests/test_sync.py` fails if the firmware `PIN_…`
constants disagree with them.

Status: **checked on paper only** — nothing here has been wired and powered yet
([`VALIDATION.md`](VALIDATION.md)).

## The three connectors you use

The CYD has three small 4-pin **JST 1.25 mm** sockets on its back. You use one or two pins on each.

| Connector | Its 4 pins (typical silkscreen) | You use |
|---|---|---|
| **CN1** | GND · IO22 · IO27 · 3.3V | all four: sensor power, TRIG, ground + servo signal |
| **P3** | GND · IO35 · IO22 · IO21 | **IO35 only** (sensor ECHO). Leave IO22 and IO21 unconnected (IO21 is the backlight on most boards). |
| **P1** | VIN · TX · RX · GND | **VIN and GND only** (servo power). Leave TX/RX alone — they are the USB serial lines. |

## Net list (machine-readable)

One row per wire end. `Wire` is the label to put on each wire.

<!-- NETLIST:BEGIN -->
| ID | Wire | Pin | Net | Kind | Notes |
|---|---|---|---|---|---|
| N01 | W1 | CN1.3V3 | 3V3 | POWER | 3.3 V from the CYD regulator |
| N02 | W1 | SENSOR.VCC | 3V3 | POWER | RCWL-1601 / HC-SR04P runs at 3.3 V |
| N03 | W2 | CN1.IO27 | TRIG | SIGNAL | 10 µs trigger pulse |
| N04 | W2 | SENSOR.TRIG | TRIG | SIGNAL |  |
| N05 | W3 | P3.IO35 | ECHO | SIGNAL | input-only pin; 3.3 V echo, no divider |
| N06 | W3 | SENSOR.ECHO | ECHO | SIGNAL |  |
| N07 | W4 | CN1.GND | GND | POWER | common ground |
| N08 | W4 | SENSOR.GND | GND | POWER |  |
| N09 | W5 | CN1.IO22 | SERVO_PWM | SIGNAL | 50 Hz pulses, 1000–2000 µs |
| N10 | W5 | SERVO.SIGNAL | SERVO_PWM | SIGNAL | orange (or yellow/white) lead |
| N11 | W6 | P1.VIN | VIN_5V | POWER | USB 5 V on the board side. VERIFY on your board |
| N12 | W6 | SERVO.+5V | VIN_5V | POWER | red lead (middle) |
| N13 | W7 | P1.GND | GND | POWER | same copper as CN1.GND |
| N14 | W7 | SERVO.GND | GND | POWER | brown (or black) lead |
<!-- NETLIST:END -->

## Firmware pin map

`Where` says how you reach the pin: a connector, or `on-board` (already wired on the CYD, nothing to do).

<!-- PINMAP:BEGIN -->
| Firmware constant | GPIO | Where | Direction | Function |
|---|---|---|---|---|
| PIN_TRIG | 27 | CN1 | output | sensor trigger |
| PIN_ECHO | 35 | P3 | input | sensor echo (input-only pin) |
| PIN_SERVO | 22 | CN1 | output | servo PWM (LEDC, 50 Hz) |
| PIN_TFT_SCK | 14 | on-board | output | display SPI clock |
| PIN_TFT_MISO | 12 | on-board | input | display SPI data in |
| PIN_TFT_MOSI | 13 | on-board | output | display SPI data out |
| PIN_TFT_CS | 15 | on-board | output | display chip select |
| PIN_TFT_DC | 2 | on-board | output | display data/command |
| PIN_TFT_BL | 21 | on-board | output | backlight |
| PIN_TOUCH_CLK | 25 | on-board | output | touch SPI clock |
| PIN_TOUCH_MISO | 39 | on-board | input | touch SPI data in |
| PIN_TOUCH_MOSI | 32 | on-board | output | touch SPI data out |
| PIN_TOUCH_CS | 33 | on-board | output | touch chip select |
| PIN_TOUCH_IRQ | 36 | on-board | input | touch interrupt |
| PIN_LED_R | 4 | on-board | output | RGB LED red (active low) |
| PIN_LED_G | 16 | on-board | output | RGB LED green (active low) |
| PIN_LED_B | 17 | on-board | output | RGB LED blue (active low) |
<!-- PINMAP:END -->

## Step by step

1. **Unplug USB.** Never wire with the board powered.
2. **CN1 cable → sensor + servo signal.** 3.3V → `VCC`, IO27 → `Trig`, GND → `Gnd`, IO22 → servo signal.
3. **P3 cable → sensor echo.** IO35 → `Echo`. Tape off the other three wires of that cable.
4. **P1 cable → servo power.** VIN → servo red, GND → servo brown. Tape off TX and RX.
5. Route the sensor's four wires up through the slot next to the turret hole and leave a loop
   so the head can turn ±60°.
6. Check every wire against the net list above before connecting USB.

The servo plug and the CYD cables often both end in *female* Dupont sockets: join them with
three male-to-male jumper pins, or crimp/solder and heat-shrink.

## Power — read this

* The scanner runs from **one USB cable**. Use a phone charger or power bank rated **≥ 1 A**.
  A laptop port (often 500 mA) may brown out when the servo starts.
* The servo is fed from P1 **VIN**. On the boards documented by the community this pin is the
  USB 5 V rail (through the board's protection parts). **VERIFY with a multimeter** on your board
  before connecting the servo: you should read ≈ 4.5–5.2 V between P1 VIN and GND with USB in.
* If the screen flickers or the board resets when the servo moves, add a **470–1000 µF, ≥ 6.3 V
  electrolytic capacitor** across the servo's red (+) and brown (−) leads, stripe to brown.

## Fallback: you only have a 5 V HC-SR04

A classic HC-SR04 (not the "P" version) needs 5 V and outputs a **5 V echo** that can damage the
ESP32. If that is what you have:

* Power it from **P1 VIN** instead of CN1 3.3V.
* Put a divider in the echo line: `ECHO —[2.2 kΩ]— IO35`, and `IO35 —[3.3 kΩ]— GND`
  (5 V × 3.3/5.5 ≈ 3.0 V).

The RCWL-1601 / HC-SR04P costs about the same and needs neither, which is why it is the default.

## Programming

Plug the CYD into your computer by USB and flash from the web page (`flash.html`) or with
`arduino-cli` ([`README`](../README.md#flash)). The sensor and servo can stay connected.
Spreadsheet versions: [`manufacturing/wiring_pins.csv`](../manufacturing/wiring_pins.csv) and
[`manufacturing/wire_list.csv`](../manufacturing/wire_list.csv).
