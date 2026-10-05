# Validation log — what is known, and what is not

Two kinds of evidence, never mixed:

* **RECORDED** — checks a computer can run without hardware: CAD solids are valid, parts fit the
  bed and don't overlap in the model, the firmware compiles, the equations agree, the docs and
  firmware agree. Real results, but they say nothing about whether a physical build works.
* **PHYSICAL** — anything that needs a printer, a multimeter, a powered scanner or a tape measure.

> **Current status: no PHYSICAL validation has been performed for Radar V6.** No part has been
> printed or fitted, the firmware has not been flashed onto a Cheap Yellow Display, and the scanner
> has never been powered. Do not call it "working" until the PHYSICAL table has entries.

## RECORDED checks

| ID | Check | Result | Date (UTC) | Evidence / how to reproduce |
|---|---|---|---|---|
| R-CAD-1 | All 5 parts build as single valid solids; the shell matches its nominal size within 0.6 mm | PASS | 2026-10-04 | `python scripts/render_cad.py` → `cad/geometry_report.json` |
| R-CAD-2 | Every print mesh is watertight with outward normals | PASS | 2026-10-04 | same report |
| R-CAD-3 | Plates P1, P2 and S1 fit the A1 mini bed (180 × 180 mm, 6 mm margin), parts ≥ 6 mm apart | PASS | 2026-10-04 | same report, "plates" |
| R-CAD-4 | No overlap in the assembled model between printed parts and the module models (CYD, SG90, horn, sensor) — 14 pairs; the base's three 0.3 mm crush ribs are the only allowed overlap; the CYD sits on the bezel pegs | PASS | 2026-10-04 | same report, "interference" |
| R-CAD-5 | Sweep clearance in the model: head + sensor and horn rotated −75°…+75° (commanded travel is ±60°) never touch the shell or servo | PASS | 2026-10-04 | same report, "sweep" |
| R-CAD-6 | Designed clearances: horn foot 3.7 mm above the roof; screen glass 0.1 mm behind the bezel; CYD 1.8 mm from the shell, 19.4 mm from the servo | RECORDED | 2026-10-04 | same report, "clearances" — all depend on VERIFY values |
| R-FW-1 | Firmware compiles for ESP32 Dev Module on Arduino-ESP32 **3.3.12** with `--warnings all`: 0 warnings, 0 errors (334 227 B flash, 25 056 B RAM) | PASS | 2026-10-04 | [`validation/compile_core3.txt`](validation/compile_core3.txt) |
| R-FW-2 | Same sketch on Arduino-ESP32 **2.0.17** (the 2.x LEDC path): 0 warnings, 0 errors (304 621 B flash, 23 192 B RAM) | PASS | 2026-10-04 | [`validation/compile_core2.txt`](validation/compile_core2.txt) |
| R-FW-3 | 320 × 240 screen layout checked in the pixel-level Python port of the drawing code | PASS | 2026-10-04 | `python scripts/sim_display.py` → `hardware/diagrams/radar_frame.png` — synthetic targets only |
| R-EQ-1 | 19 equation checks: distance, temperature effect, echo timeout, 3.3 V echo level, fallback divider incl. worst case, LEDC duty, angle map, clamp, sweep cadence estimate, dot persistence | PASS | 2026-10-04 | `python -m pytest tests/test_equations.py` |
| R-SYNC-1 | Firmware pins = WIRING.md pin map = net list; 7 wires with two ends each; sensor on 3.3 V; servo on VIN; USB serial and backlight pins untouched; no flash pins, no strapping pins on the wires | PASS | 2026-10-04 | `python -m pytest tests/test_sync.py` |
| R-BOM-1 | BOM has 5 required items + 1 optional, no battery or loose screws, sensor must be 3.3 V capable, prices labelled as estimates | PASS | 2026-10-04 | `python -m pytest tests/test_bom.py` |
| R-APP-1 | Shared serial parser/recorder (web + desktop): 10 checks incl. the firmware's exact `printf` formats | PASS | 2026-10-04 | `node --test tests/js/*.test.js` |
| R-APP-2 | Web app in headless Chromium: simulator, wiring explorer, demo stream, record + save CSV, replay, guide images, service worker, offline reload, no page errors | PASS | 2026-10-04 | `python tests/browser/check_site.py` |
| R-APP-3 | Desktop app (Electron) run from source: every main page loads with no errors or broken images, offline KaTeX renders, Web Serial API present, demo delivers readings | PASS | 2026-10-04 | `xvfb-run npx electron . --smoke-test` |
| R-APP-4 | Linux installers built: AppImage + tar.gz (electron-builder) — from the V5.2 release build; Windows and macOS installers are built only by `.github/workflows/release.yml` and have **not** been run | RECORDED | 2026-10-02 | local build |
| R-MFG-1 | Manufacturing exports regenerate identically from the docs (BOM, printed parts, pin list, 7-wire list); every pin appears in the wire list; build packet PDF builds | PASS | 2026-10-04 | `python -m pytest tests/test_mfg.py`, `python scripts/make_build_packet.py` |
| R-REQ-1 | Every requirement has a verification method and evidence that exists here; every physical test traces to a requirement | PASS | 2026-10-04 | `python -m pytest tests/test_requirements.py` |
| R-FLS-1 | Browser-flasher payload: merged ESP32 image (offset 0x0) and ESP Web Tools manifest generated from the compiled firmware | PASS | 2026-10-04 | `python scripts/build_site.py --firmware …merged.bin`; flashing itself is T-FLS-1 |
| R-APP-5 | Electron hardening + listen-only console encoded as tests (context isolation, sandbox, no Node, permissions refused except serial, CSP, no serial writes) | PASS | 2026-10-04 | `python -m pytest tests/test_app.py` |

Notes on R-FW-1/2: built in a sandbox that could not reach `downloads.arduino.cc`; libraries came
from their GitHub release tags and the Arduino prototype generator (ctags) was stubbed — the sketch
declares every function before use. Re-compile on a normal install with
`arduino-cli compile --profile esp32-core3 firmware/Radar_V6` before flashing.

## PHYSICAL validation — all NOT established

Fill in **Result**, **Date** and **By** as you go; put photos or serial logs in `docs/validation/`.
A failed test is still useful — write down what happened.

| ID | Test | Pass criterion | Status | Result | Date | By |
|---|---|---|---|---|---|---|
| T-PRN-1 | Print the fit coupon; try the CYD pegs, sensor-can holes and servo-screw pilots | chosen sizes recorded; `PEG_D`, `CAN_HOLE_D`, `PILOT_D` updated if needed | NOT RUN | | | |
| T-PRN-2 | Print P1 (shell, roof-down) | no supports, chamfers and grooves clean | NOT RUN | | | |
| T-PRN-3 | Print P2 (bezel, base, head) | no supports; pegs not snapped | NOT RUN | | | |
| T-FIT-1 | CYD pressed onto the bezel pegs | firm; screen centred in the window (else set `CYD_VIEW_DX`) | NOT RUN | | | |
| T-FIT-2 | Bezel slides into the shell grooves; base presses in; USB plug reaches the board | nothing forced; base stays in when lifted | NOT RUN | | | |
| T-FIT-3 | Servo screwed under the roof with its own screws; horn pressed into the head foot | head firm on the spline, no wobble | NOT RUN | | | |
| T-FIT-4 | Sensor cans pressed into the head | cans hold; PCB not bent | NOT RUN | | | |
| T-PWR-1 | P1 VIN voltage with USB in: idle, and while the servo moves | ≈ 4.5–5.2 V; record the dip | NOT RUN | | | |
| T-PWR-2 | One-hour run from a ≥ 1 A charger | no resets, flicker or brown-outs (else add the capacitor and re-test) | NOT RUN | | | |
| T-PWR-3 | Run from a laptop USB port | record whether it works; note resets | NOT RUN | | | |
| T-PWR-4 | Current draw with a USB meter: idle and sweeping | record mA | NOT RUN | | | |
| T-FW-1 | Flash; splash, then grid and sweep | as described in ASSEMBLY | NOT RUN | | | |
| T-FW-2 | Panel detection and colours (`# board … panel …` line) | correct picture; else record the `PANEL` / `INVERT_OVERRIDE` / `SWAP_RED_BLUE` that work | NOT RUN | | | |
| T-FW-3 | `CENTER_ONLY` head fit; `REVERSE_SERVO` direction | head faces straight out at 90°; screen matches head | NOT RUN | | | |
| T-FW-4 | Measured timing from the serial "# measured" line | record mean step and one-way sweep (estimate ≈ 115 ms, ≈ 4.6 s) | NOT RUN | | | |
| T-FW-5 | Distance at 30 / 100 / 150 cm on the 90° line (flat target) | record reading vs tape measure | NOT RUN | | | |
| T-FW-6 | Touch: − / + change the range; tap the fan to pause | each tap acts once; no false taps | NOT RUN | | | |
| T-FW-7 | RGB LED turns red under 30 cm | as described | NOT RUN | | | |
| T-CAL-1 | `CALIBRATE_SERVO` against the roof ticks without hitting the end stops | record `SERVO_US_AT_0/180`; no buzzing at ends | NOT RUN | | | |
| T-SWP-1 | Powered sweep with the sensor cable fitted | no rubbing, no cable tug at 30° or 150° | NOT RUN | | | |
| T-THM-1 | Temperatures after 30 min running (board regulator, servo) | nothing uncomfortable to touch | NOT RUN | | | |
| T-LNK-1 | Live console over the scanner's own USB cable at 115 200 baud | readings appear, sweep matches the head; note whether opening the port resets the board | NOT RUN | | | |
| T-LNK-2 | Record a session in the console and replay it | replay matches the live view | NOT RUN | | | |
| T-APP-1 | Windows installer + portable build open and connect | app opens; port picker lists the board | NOT RUN | | | |
| T-APP-2 | macOS build opens (after Gatekeeper approval) and connects | as above | NOT RUN | | | |
| T-FLS-1 | Browser flasher (Flash page, Chrome/Edge) installs the release firmware on a CYD | splash screen appears | NOT RUN | | | |
| T-REL-1 | First tagged release carries the source ZIP, manufacturing kit, firmware, desktop apps, SHA256SUMS and attestations | `sha256sum -c` and `gh attestation verify` pass | NOT RUN | | | |

## Untested assumptions (every VERIFY value in the CAD)

| Variable | Assumed | Source of the assumption | Measured |
|---|---|---|---|
| `CYD_L` × `CYD_H`, `CYD_HOLE_DX/DY` | 86.6 × 50 mm, holes ±39 × ±21 mm | community drawings of the ESP32-2432S028R | |
| `CYD_GLASS_TOP`, `CYD_BACK_DEPTH` | 5.1 mm, 4.8 mm | community STEP model | |
| `CYD_VIEW_DX` | −2.5 mm | community STEP model (active area off-centre) | |
| `CYD_USB_LY/LZ` | −9.3, −1.5 mm | photos; the CYD2USB board's USB-C sits elsewhere — the 15 × 10 mm opening is generous | |
| `SERVO_*` | 22.2 × 11.8 body, 32.2 mm flange, 27.5 mm hole pitch | typical TowerPro SG90 drawings | |
| `HORN_*` | 34 × 6.2 × 1.5 mm single arm, 7.2 mm collar | estimate of a stock horn | |
| `SR04_*` | 45 × 20 mm PCB, Ø16 mm cans, 26 mm pitch | common HC-SR04 / RCWL-1601 footprint | |
| `PEG_D`, `CAN_HOLE_D`, `PILOT_D`, `HORN_SLOT_CLR` | 2.9, 16.2, 1.8, 0.15 mm | print allowances — set from the coupon | |

## Electrical assumptions not yet checked on hardware

* P1 **VIN** carries USB 5 V and can supply an SG90's start-up current (community pinouts say VIN is
  the USB 5 V rail; current capability through the board's protection parts is not measured here).
* The RCWL-1601 / HC-SR04P bought works reliably at 3.3 V (datasheets say 3–5.5 V).
* GPIO 27 and 22 on CN1 and GPIO 35 on P3 are free on your board revision (true for the documented
  ESP32-2432S028R; some clones differ).
* 1000–2000 µs covers 30°–150° of real travel on your servo — probably not exactly; calibrate.
