# Wiring — pin by pin (Radar V5.1 baseline)

> **Follow the labels, not the wire colours.** Jumper colours vary between kits; module
> silkscreen labels do not. Where this page and your module's silkscreen disagree, stop and
> check the module's datasheet (links in [`CREDITS.md`](../CREDITS.md)).

This page is the **single source of truth** for connections. Two things are generated from it:

* the SVG wiring diagrams in [`hardware/diagrams/`](../hardware/diagrams/) (`python scripts/gen_diagrams.py`)
* the firmware pin check: `python -m pytest tests/test_sync.py` fails if the `PIN_…`
  constants in [`firmware/Radar_V5/Radar_V5.ino`](../firmware/Radar_V5/Radar_V5.ino) and the
  [ESP32 pin map](#esp32-pin-map) below disagree.

Spreadsheet versions: [`manufacturing/wiring_pins.csv`](../manufacturing/wiring_pins.csv) (pin by pin) and
[`manufacturing/wire_list.csv`](../manufacturing/wire_list.csv) (point-to-point wires W01–W28, as printed in the
[build packet](../manufacturing/build_packet.pdf)).

Status: **documented and cross-checked on paper only.** Nothing on this page has been wired and
powered yet — see [`VALIDATION.md`](VALIDATION.md).

![Full wiring diagram](../hardware/diagrams/wiring_full.svg)

## Words used on this page

| Term | Meaning |
|---|---|
| Net | A set of pins that are all electrically connected together. Every pin on the same net touches the same copper. |
| `LOAD_5V` | The switched 5 V rail that feeds the scanner. It is live only when the latching switch is ON. |
| `GND` (common ground) | The shared 0 V reference for the ESP32, sensor, servo and display. |
| General-Purpose Input/Output (GPIO) | A numbered ESP32 pin that firmware can read or drive. |
| Serial Peripheral Interface (SPI) | The 4-wire bus (clock, data, chip-select, data/command) that drives the LCD. |
| Pulse-Width Modulation (PWM) | A repeating square wave whose high time encodes a value; the servo reads the high time as an angle. |
| Keyed disconnect (J1) | A two-pin polarised plug (for example JST-XH) that can only be inserted one way, so the ESP32's power lead can be unplugged and re-plugged safely. |

## Safety rules that the wiring depends on

1. The **3 A fuse sits on the battery positive lead**, as close to the cell holder as practical. Mandatory.
2. **Never** connect a bare cell to the ESP32 VIN or to the servo. Everything runs from the charger module's regulated 5 V output.
3. The latching switch cuts the **load**, not the charger↔cell path, so USB-C charges the cell with the scanner OFF.
4. The servo is powered from `LOAD_5V`, **never** from the ESP32's 3V3 pin.
5. HC-SR04 ECHO is a 5 V signal. It reaches GPIO26 **only through the 2.2 kΩ / 3.3 kΩ divider** — never direct.
6. Programming: unplug the whole harness from the ESP32 first. **Never** have external 5 V/VIN and the programming USB cable connected at the same time.
7. The rear USB-C port is **power/charging only** — it is not connected to the ESP32's data lines.

## Net list (machine-readable)

Each row is one pin and the net it joins. Parts: `USBC` = USB-C power-input breakout
(Adafruit 4090 reference), `DFR1026` = DFRobot charge/discharge module, `CELL` = protected
18650 in its wired holder, `FUSE` = 3 A inline fuse, `SW` = 12 mm latching push switch,
`ESP32` = ESP32-WROOM-32 DevKit, `SR04` = HC-SR04, `SERVO` = SG90-size positional servo,
`LCD` = Waveshare 1.8" ST7735S, `R1` = 2.2 kΩ, `R2` = 3.3 kΩ, `C1` = 1000 µF electrolytic.

<!-- NETLIST:BEGIN -->
| ID | Pin | Net | Kind | Wire | Notes |
|---|---|---|---|---|---|
| P01 | USBC.VBUS | USB_5V | POWER | 22 AWG | USB-C breakout VBUS to charger input |
| P02 | DFR1026.VIN | USB_5V | POWER | 22 AWG | charger input (4.6–5.4 V) |
| P03 | USBC.GND | USB_GND | POWER | 22 AWG | |
| P04 | DFR1026.GND_IN | USB_GND | POWER | 22 AWG | charger input ground pad |
| P05 | CELL.+ | BAT_RAW | POWER | 22 AWG | cell holder positive lead, keep short |
| P06 | FUSE.A | BAT_RAW | POWER | 22 AWG | 3 A fuse, insulated holder, mandatory |
| P07 | FUSE.B | BAT_POS | POWER | 22 AWG | |
| P08 | DFR1026.BAT+ | BAT_POS | POWER | 22 AWG | |
| P09 | CELL.- | BAT_NEG | POWER | 22 AWG | cell holder negative lead |
| P10 | DFR1026.GND_BAT | BAT_NEG | POWER | 22 AWG | battery ground pad only; do not tie elsewhere |
| P11 | DFR1026.OUT_5V | OUT_5V | POWER | 22 AWG | regulated 5 V output |
| P12 | SW.1 | OUT_5V | POWER | 22 AWG | latching switch, rated ≥2 A at 5 V |
| P13 | SW.2 | LOAD_5V | POWER | 22 AWG | star point for the load branches |
| P14 | DFR1026.GND_OUT | GND | POWER | 22 AWG | common ground star point |
| P15 | ESP32.VIN | LOAD_5V | POWER | 22–24 AWG | via keyed disconnect J1 pin 1; own branch from the star point |
| P16 | ESP32.GND | GND | POWER | 22–24 AWG | via keyed disconnect J1 pin 2 |
| P17 | SERVO.RED | LOAD_5V | POWER | 22 AWG | own short branch, separate from the ESP32 branch |
| P18 | SERVO.BROWN | GND | POWER | 22 AWG | brown or black lead |
| P19 | C1.+ | LOAD_5V | POWER | leads | 1000 µF ≥10 V, mounted at the servo end; mind polarity |
| P20 | C1.- | GND | POWER | leads | stripe side |
| P21 | SR04.VCC | LOAD_5V | POWER | jumper | |
| P22 | SR04.GND | GND | POWER | jumper | |
| P23 | ESP32.3V3 | 3V3 | POWER | jumper | ESP32 on-board regulator output |
| P24 | LCD.VCC | 3V3 | POWER | jumper | |
| P25 | LCD.BL | 3V3 | POWER | jumper | backlight always on |
| P26 | LCD.GND | GND | POWER | jumper | |
| S01 | ESP32.GPIO27 | TRIG | SIGNAL | jumper | 10 µs trigger pulse |
| S02 | SR04.TRIG | TRIG | SIGNAL | jumper | |
| S03 | SR04.ECHO | ECHO_5V | SIGNAL | jumper | 5 V pulse — never straight to a GPIO |
| S04 | R1.1 | ECHO_5V | SIGNAL | leads | R1 = 2.2 kΩ 1 % |
| S05 | R1.2 | ECHO_3V | SIGNAL | leads | divider junction |
| S06 | R2.1 | ECHO_3V | SIGNAL | leads | R2 = 3.3 kΩ 1 % |
| S07 | R2.2 | GND | SIGNAL | leads | |
| S08 | ESP32.GPIO26 | ECHO_3V | SIGNAL | jumper | ≈3.0 V high level |
| S09 | ESP32.GPIO14 | SERVO_PWM | SIGNAL | jumper | 50 Hz LEDC output |
| S10 | SERVO.SIGNAL | SERVO_PWM | SIGNAL | jumper | orange/yellow lead |
| S11 | ESP32.GPIO23 | TFT_MOSI | SIGNAL | jumper | LCD pin labelled DIN |
| S12 | LCD.DIN | TFT_MOSI | SIGNAL | jumper | |
| S13 | ESP32.GPIO18 | TFT_SCK | SIGNAL | jumper | LCD pin labelled CLK |
| S14 | LCD.CLK | TFT_SCK | SIGNAL | jumper | |
| S15 | ESP32.GPIO33 | TFT_CS | SIGNAL | jumper | not GPIO5 (boot strapping pin) |
| S16 | LCD.CS | TFT_CS | SIGNAL | jumper | |
| S17 | ESP32.GPIO17 | TFT_DC | SIGNAL | jumper | LCD pin labelled DC (sometimes A0) |
| S18 | LCD.DC | TFT_DC | SIGNAL | jumper | |
| S19 | ESP32.GPIO16 | TFT_RST | SIGNAL | jumper | |
| S20 | LCD.RST | TFT_RST | SIGNAL | jumper | |
<!-- NETLIST:END -->

No SD-card pins are wired. No other GPIO is used.

## ESP32 pin map

<!-- PINMAP:BEGIN -->
| GPIO | Firmware constant | Net | Direction | Why this pin |
|---|---|---|---|---|
| 27 | PIN_TRIG | TRIG | output | ordinary GPIO, not a strapping pin |
| 26 | PIN_ECHO | ECHO_3V | input | ordinary GPIO; sees ≈3.0 V through the divider |
| 14 | PIN_SERVO | SERVO_PWM | output (LEDC) | LEDC-capable, not a strapping pin. It can toggle briefly during boot, so the servo may twitch at power-up — keep fingers clear of the head |
| 23 | PIN_TFT_MOSI | TFT_MOSI | output | default VSPI MOSI |
| 18 | PIN_TFT_SCLK | TFT_SCK | output | default VSPI SCK |
| 33 | PIN_TFT_CS | TFT_CS | output | avoids GPIO5, a boot strapping pin |
| 17 | PIN_TFT_DC | TFT_DC | output | free on WROOM-32 (used for PSRAM on WROVER — do not substitute a WROVER board) |
| 16 | PIN_TFT_RST | TFT_RST | output | free on WROOM-32 (used for PSRAM on WROVER) |
<!-- PINMAP:END -->

## The same connections, module by module

### Power (charger, cell, switch)
```
USB-C VBUS  ──────────────────────────────▶ DFR1026 VIN
USB-C GND   ──────────────────────────────▶ DFR1026 input GND
Cell +  ──[ 3 A fuse ]────────────────────▶ DFR1026 BAT+
Cell −  ──────────────────────────────────▶ DFR1026 battery GND
DFR1026 OUT 5V ──[ latching switch ]──▶ LOAD_5V star point
DFR1026 GND ──────────────────────────────▶ common GND star point
LOAD_5V ─┬─ branch A ─[J1 pin 1]─▶ ESP32 VIN (5V)
         ├─ branch B ─────────────▶ servo red  ── C1 (+) right at the servo
         └─ branch C ─────────────▶ HC-SR04 VCC
GND ─────┬─ [J1 pin 2] ─▶ ESP32 GND
         ├─ servo brown/black ── C1 (−)
         ├─ HC-SR04 GND
         └─ R2 (bottom of the ECHO divider)
```
Separate short branches mean the servo's current spikes do not travel through the ESP32's
supply lead. The 1000 µF capacitor sits at the servo end of branch B for the same reason.

### HC-SR04 and the ECHO divider
```
HC-SR04 TRIG ◀──────────── GPIO27
HC-SR04 ECHO ──[ R1 2.2 kΩ ]──●── GPIO26
                              │
                        [ R2 3.3 kΩ ]
                              │
                             GND
```
Divider output: `5.0 V × 3.3 / (2.2 + 3.3) = 3.0 V` — see [`EQUATIONS.md`](EQUATIONS.md#2-echo-voltage-divider).

![ECHO divider and fuse callout](../hardware/diagrams/callout_echo_divider_fuse.svg)

### Servo
| Servo lead | Goes to |
|---|---|
| signal (orange/yellow) | GPIO14 |
| red | `LOAD_5V` (branch B) |
| brown/black | common `GND` |

### ST7735S LCD (Waveshare 1.8")
| LCD pin | Goes to |
|---|---|
| VCC | ESP32 3V3 |
| GND | GND |
| DIN (MOSI) | GPIO23 |
| CLK (SCK) | GPIO18 |
| CS | GPIO33 |
| DC (A0) | GPIO17 |
| RST | GPIO16 |
| BL | ESP32 3V3 |

## Programming procedure

1. Switch the scanner **OFF**.
2. Unplug **J1** (ESP32 power) and every jumper on the ESP32 header — the whole harness.
3. Plug the USB **data** cable into the ESP32's own micro-USB/USB-C port. The rear USB-C port
   of the case is power-only and cannot program the board.
4. Upload (Arduino IDE: board **ESP32 Dev Module**; or `arduino-cli compile --upload --profile esp32-core3 -p <port> firmware/Radar_V5`).
5. Unplug the data cable. Re-connect the harness, checking every label against the net list, then J1 last.
6. Switch ON.

## Optional live-link tap

To watch the scanner in the web or desktop app's live console, add a two-wire, listen-only tap from
ESP32 **TX0 (GPIO1)** and **GND** to a 3.3 V USB-to-serial adapter (adapter VCC unconnected). It is
kept out of the net list above because it is optional and plugs in only when needed — full details and
diagram in [`LIVE_LINK.md`](LIVE_LINK.md). It never replaces the rule above: the ESP32's own USB port
stays unplugged while the battery harness is connected.

## Open issue — DFR1026 restart after OFF→ON (unresolved, must be bench-tested)

**Question:** after the latching switch goes OFF and back ON, does the DFR1026 output come back
by itself, or does someone have to press the module's on-board KEY (which is inside the case)?

**What the sources say (not yet confirmed on our hardware):**

* DFRobot's product page describes the KEY: in discharge mode a short press enables the output
  and a long press (about 10 s) disables it. It does not say whether the output re-enables
  automatically when a load is reconnected.
* Users on the Core Electronics forum report the module switching its output off after roughly
  30 s at light load and needing a KEY press to come back; one user found the keep-alive load was
  closer to 100 mA than the 50 mA they expected.

**Why it matters here:** with the switch on the *load* side, switching OFF leaves the module with
no load, so it will probably go to sleep; switching ON again may then do nothing. Separately, if
the scanner's idle draw (ESP32 + LCD backlight + sensor + holding servo) falls below the
module's keep-alive threshold, the output could drop out while the scanner is running.

**Bench tests that settle it** (log results in [`VALIDATION.md`](VALIDATION.md)): T-PWR-2 (measure the
scanner's minimum running current), T-PWR-3 (OFF→ON after 5 s, 60 s, 10 min, with and without USB-C
connected), T-PWR-4 (one-hour run, watch for dropouts).

**If the DFR1026 fails T-PWR-3 or T-PWR-4, adopt one of these (documented, not yet tested):**

| Option | Change | Trade-off |
|---|---|---|
| A — rear KEY button | Open the rear knock-out (Ø7 mm, printed as a 0.45 mm skin above the cell holder) and fit a small momentary push button wired across the DFR1026 KEY pads. User presses it once after switching ON. | Keeps all other parts. Two-step turn-on; does not fix a light-load dropout. |
| B — PowerBoost 1000C (V5.2 candidate) | Replace the DFR1026 with an Adafruit PowerBoost 1000C. Wire USB-C VBUS → its USB pad, cell (through the fuse) → BAT, its 5V → `LOAD_5V`. Wire the latching switch between its EN pin and GND (switch closed = OFF, because EN low disables the boost). | Clean on/off with no keep-alive. Lower output (about 1 A) — check servo stall + ESP32 peak; confirm that charging continues with EN low before adopting. |

Whichever is chosen, update this page, the BOM, `hardware/diagrams/` (re-run the generator) and
`VALIDATION.md` in the same commit.
