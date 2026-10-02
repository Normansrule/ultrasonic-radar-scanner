# Bill of materials (BOM)

Spreadsheet version: [`manufacturing/bom.csv`](../manufacturing/bom.csv) (generated from this page). Visual overview:

![Parts kit](../hardware/diagrams/bom_overview.svg)

**Reference candidates, not endorsements.** Prices, stock and exact variants change — recheck
every item live before buying, and compare the listing's own datasheet against the "what to
check" column. Datasheet links are in [`CREDITS.md`](../CREDITS.md).

**Do not cheapen the safety parts.** The cell, its protection, the switch rating, the fuse and the
power-wire gauge are not places to save money.

**Not in this project (on purpose):** custom printed circuit board (PCB), decorative LEDs, battery
fuel gauge, external display, Wi-Fi or Bluetooth inside the scanner. (The optional live console in the web/desktop app reads the existing serial output through a two-wire tap; see [`LIVE_LINK.md`](LIVE_LINK.md).) The firmware never enables Wi-Fi and does not
show a measured battery percentage.

## Electronics

| # | Qty | Part | What to check before you buy | Reference candidate |
|---|---|---|---|---|
| E1 | 1 | ESP32-WROOM-32 development board ("DevKit"), classic **30-pin**, headers **already soldered** | Module marking says WROOM-32 (not WROVER); pins labelled GPIO16/17/18/23/26/27/33/14; a USB data port. **Do not substitute** an ESP32-C3, ESP32-S3 or a WROVER board without re-checking every pin and the firmware — GPIO16/17 are used for PSRAM on WROVER. | Generic "ESP32 DevKit V1 (30-pin)" |
| E2 | 1 | HC-SR04 ultrasonic sensor | 5 V part with 4-pin header VCC/TRIG/ECHO/GND; four corner mounting holes (the sensor head expects them — `SR04_HOLE_X/Y` in the CAD are VERIFY values). | Generic HC-SR04 |
| E3 | 1 | SG90-size **positional** micro servo **with its factory double-arm horn** | 180°-type positional servo, **not** continuous-rotation ("360°") — those cannot hold an angle. Keep the factory horn and spline. | TowerPro SG90 |
| E4 | 1 | Waveshare 1.8" SPI LCD, ST7735S, 128×160 | Pins VCC/GND/DIN/CLK/CS/DC/RST/BL; board 56.5 × 34 mm (check your revision). | Waveshare 1.8inch LCD Module |
| E5 | 1 | DFRobot DFR1026 charge/discharge module (5 V / 2 A output) | Accepts 4.6–5.4 V input, ~2 A charge. It has **no USB connector** — needs E6. See the [open issue](WIRING.md#open-issue--dfr1026-restart-after-offon-unresolved-must-be-bench-tested) before committing to it. | DFRobot DFR1026 |
| E6 | 1 | USB-C female **power-input** breakout with **5.1 kΩ pull-downs on both CC1 and CC2** | The two 5.1 kΩ resistors (one per CC pin) are what make a USB-C charger switch on 5 V. **No** Power Delivery (PD) trigger board — this project must never receive 9 V or 12 V. | Adafruit 4090 (USB-C breakout, downstream) |
| E7 | 1 | Protected 18650 lithium-ion cell, ~2600–3500 mAh | **Protected** (built-in protection circuit). Check the datasheet for **≥2.1 A charge** and **≥3 A continuous discharge** — capacity alone is not enough. Buy from a reputable supplier; protected cells are slightly longer than bare ones, so check the holder fits. | Any reputable protected 18650 meeting both current ratings |
| E8 | 1 | Wired single-cell 18650 holder | Flying leads (no soldering to the cell), fits a *protected* cell's length. | Generic 1 × 18650 holder with leads |
| E9 | 1 | 12 mm latching push-on/push-off button, 2 terminals, single-pole single-throw (SPST) | Rated **≥2 A at 5 V DC** (check the DC rating, not only the AC one). Panel hole 12 mm; fascia is 2.6 mm thick. | Generic 12 mm latching metal push button |
| E10 | 1 | 3 A fuse + insulated inline holder | On battery positive, as close to the holder as practical. Blade (ATM/mini) or 5 × 20 mm glass both fine. | Inline mini-blade holder + 3 A fuse |
| E11 | 1 | 1000 µF electrolytic capacitor, ≥10 V (16 V gives margin) | Polarised: stripe = negative. Mounted at the servo end of its supply branch. | Any 1000 µF 16 V radial |
| E12 | 1 | 2.2 kΩ resistor, 1 %, ¼ W | ECHO divider R1. | Metal-film 1 % |
| E13 | 1 | 3.3 kΩ resistor, 1 %, ¼ W | ECHO divider R2. | Metal-film 1 % |
| E14 | ~20 | Jumper leads, mostly female–female, plus short 22–24 AWG stranded power wire | Power branches (charger → switch → load) in 22 AWG; signal leads can be jumpers. | Assorted Dupont leads + 22 AWG silicone wire |
| E15 | ≥1 | Keyed two-pin power disconnect (J1) | Polarised so it cannot be reversed (for example JST-XH 2.54 mm). Lets the ESP32's power lead unplug for programming. | JST-XH 2-pin pair (or similar) |
| E16 | 1 lot | Heat-shrink, double-sided foam tape, 2 battery straps or zip ties (≤3.6 mm wide), 4 rubber feet | Straps go round the **holder**, not the bare cell. | — |
| E17 | 1 | 5 V / 3 A USB-C wall supply + USB-C cable | Plain 5 V is enough; a PD charger also works because the breakout only asks for 5 V. | Any reputable 5 V 3 A USB-C supply |
| E18 | 1 | USB **data** cable for the ESP32 board | Micro-USB or USB-C to match E1. Charge-only cables will not program. | — |
| E19 | ~260 g max | PLA filament | 257 g is the solid-volume upper bound for all required parts plus the coupon (from `cad/geometry_report.json`); your slicer's figure with walls + infill will be lower. | Any PLA |
| E20 | 1 (optional) | 3.3 V-logic USB-to-serial adapter + 2 female jumper leads | Only for the live console. CP2102, CH340 or FT232 type, voltage set to **3.3 V**. Only its RX and GND are used; VCC stays unconnected. See [`LIVE_LINK.md`](LIVE_LINK.md). | Generic CP2102 USB-UART module |

## Fasteners — M2 only (no M3/M4)

<!-- FASTENERS:BEGIN -->
| Qty | Item | Used for |
|---|---|---|
| 2 | M2×6 screw | horn → rotor hub (from below, through the horn arm holes) |
| 12 | M2×8 screw | 4 roof → body, 4 front panel → body, 2 servo flange → roof, 2 turret keeper → roof |
| 4 | M2×12 screw | HC-SR04 board → sensor head (nuts on the back) |
| 1 | M2×20 screw | cross-bolt through the rotor hub and the sensor-head mast |
| 6 | M2 hex nut | 4 sensor + 1 cross-bolt + 1 spare — buy extras |
| 8 | M2 washer | 6–10 under screw heads on printed plastic |
| 1 | M2 hand tap | cuts threads in the 1.70 mm printed pilot holes |
<!-- FASTENERS:END -->

Screws are machine screws (pan or socket head). Holes in the prints are **1.70 mm pilots** (tap
M2) and **2.25 mm clearances** (screw passes through). Print the fit-test coupon first and adjust
`M2_PILOT_D` / `M2_CLEAR_D` in the CAD source if your printer runs tight or loose — see
[`PRINTING.md`](PRINTING.md).

## Tools you will need

Soldering iron (for the charger pads, fuse holder leads, resistors and capacitor — **never** the
cell), wire strippers, small cross-head and hex drivers, multimeter (required for the bench-power
stage), calipers (required for the VERIFY measurements), tweezers, a heat source for heat-shrink.

## If the power open issue forces a change

[`WIRING.md` → Open issue](WIRING.md#open-issue--dfr1026-restart-after-offon-unresolved-must-be-bench-tested)
lists two documented fall-backs: **Option A** adds a small momentary push button for the DFR1026
KEY (fits the rear knock-out); **Option B** replaces the DFR1026 with an Adafruit PowerBoost 1000C.
Neither has been tested. Update this BOM in the same commit as the wiring change.
