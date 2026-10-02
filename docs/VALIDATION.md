# Validation log — what is known, and what is not

This project separates two kinds of evidence and never mixes them:

* **RECORDED** — checks a computer can do without hardware: the CAD solids are valid, parts fit
  the print bed, parts do not overlap in the model, the firmware compiles, the equations are
  numerically consistent, the docs and firmware agree. These are real results, but they say
  nothing about whether a physical build works.
* **PHYSICAL** — anything that needs a printer, a multimeter, a powered scanner or a tape measure.

> **Current status: no PHYSICAL validation has been performed.** No part has been printed or fitted,
> the firmware has not been flashed, and the scanner has never been powered. Do not quote this
> project as "working" until the PHYSICAL table below has entries.

## RECORDED checks

| ID | Check | Result | Date (UTC) | Evidence / how to reproduce |
|---|---|---|---|---|
| R-CAD-1 | All 8 parts build as single valid solids; required parts match the brief's nominal sizes within 0.6 mm | PASS | 2026-09-30 | `python scripts/render_cad.py` → `cad/geometry_report.json` |
| R-CAD-2 | Every print mesh is watertight with outward normals | PASS | 2026-09-30 | same report, "print mesh watertight" |
| R-CAD-3 | Plates P1, P2, P3, S1, S2 fit the A1 mini bed (180 × 180 mm, 6 mm margin) with parts ≥ 6 mm apart; every part height ≤ 180 mm | PASS | 2026-09-30 | same report, "plates" |
| R-CAD-4 | No overlap in the assembled model between printed parts, or between printed parts and the module envelopes (servo, horn, HC-SR04, LCD, ESP32, cell holder, USB-C breakout) — 22 pairs, each < 0.5 mm³ | PASS | 2026-09-30 | same report, "interference" |
| R-CAD-5 | Sweep clearance in the model: head + HC-SR04, hub and horn rotated −75°…+75° about the turret axis (commanded travel is ±60°) never overlap keeper, roof, body or servo | PASS | 2026-09-30 | same report, "sweep" |
| R-CAD-6 | Designed clearances: hub axial play 0.4 mm; head rim 8.0 mm above keeper; hub 2.2 mm above servo gear boss; servo 1.3 mm from keeper | RECORDED | 2026-09-30 | same report, "clearances" — all depend on VERIFY values |
| R-FW-1 | Firmware compiles for ESP32 Dev Module on Arduino-ESP32 **3.3.12** with `--warnings all`: 0 warnings, 0 errors (326 215 B flash, 24 504 B RAM) | PASS | 2026-10-01 | [`validation/compile_core3.txt`](validation/compile_core3.txt) |
| R-FW-2 | Same sketch on Arduino-ESP32 **2.0.17** (the 2.x LEDC path): 0 warnings, 0 errors (296 905 B flash, 22 624 B RAM) | PASS | 2026-10-01 | [`validation/compile_core2.txt`](validation/compile_core2.txt) |
| R-FW-3 | Screen layout checked in the pixel-level Python port (`scripts/sim_display.py`); found and fixed range labels clipped at the right edge | PASS | 2026-09-30 | `hardware/diagrams/radar_frame.png` — synthetic targets only |
| R-EQ-1 | 18 equation checks: distance, temperature effect, echo timeout, divider incl. worst case, LEDC duty, angle map, clamp, sweep cadence estimate | PASS | 2026-09-30 | `python -m pytest tests/test_equations.py` |
| R-SYNC-1 | Firmware pins = WIRING.md pin map = net list; wiring safety rules (fuse first on battery +, ECHO never direct, switch on load side, servo on 5 V, no USB data, no flash/strapping pins) | PASS | 2026-09-30 | `python -m pytest tests/test_sync.py` |
| R-BOM-1 | Fastener counts in BOM add up to their listed uses | PASS | 2026-09-30 | `python -m pytest tests/test_bom.py` |
| R-APP-1 | Shared serial parser/recorder (web + desktop): 10 checks incl. the firmware's exact `printf` formats, lines split across chunks, wrong-baud garbage, CSV round-trip | PASS | 2026-10-02 | `node --test tests/js/*.test.js` |
| R-APP-2 | Web app in headless Chromium: landing simulator, wiring explorer, demo stream, record + save CSV, replay of a saved log, guide images, service worker, offline reload, no page errors — 17 checks | PASS | 2026-10-02 | `python tests/browser/check_site.py` |
| R-APP-3 | Desktop app (Electron 44.5.1) run from source and as the **packaged Linux build**: every main page loads with no errors or broken images, offline KaTeX renders 39 equations, Web Serial API present, demo delivers readings | PASS | 2026-10-02 | `xvfb-run npx electron . --smoke-test` and `dist/linux-unpacked/ultrasonic-radar-scanner --smoke-test` |
| R-APP-4 | Linux installers built: AppImage + tar.gz (electron-builder 26.15.3) | PASS | 2026-10-02 | local build; Windows and macOS installers are built only by `.github/workflows/release.yml` and have **not** been run |
| R-MFG-1 | Manufacturing exports regenerate identically from the docs (BOM, printed parts, pin list, 28-wire point-to-point list); every pin appears in the wire list; build packet PDF builds (11 pages) | PASS | 2026-10-02 | `python -m pytest tests/test_mfg.py`, `python scripts/make_build_packet.py` |
| R-REQ-1 | 36 requirements each have a verification method and evidence that exists here; every physical test traces to a requirement | PASS | 2026-10-02 | `python -m pytest tests/test_requirements.py` |
| R-FLS-1 | Browser-flasher payload: merged ESP32 image (offset 0x0) and ESP Web Tools manifest generated from the compiled firmware | PASS | 2026-10-02 | `python scripts/build_site.py --firmware …merged.bin`; flashing itself is T-FLS-1 |
| R-APP-5 | Electron hardening + listen-only console encoded as tests (context isolation, sandbox, no Node, no preload, permissions refused except serial, external links to system browser, CSP, no serial writes) | PASS | 2026-10-02 | `python -m pytest tests/test_app.py` |

Notes on R-FW-1/2: built in a sandbox that could not reach `downloads.arduino.cc`; libraries came
from their GitHub release tags and the Arduino prototype generator (ctags) was stubbed — the sketch
declares every function before use, so nothing depended on it. Re-compile on a normal install with
`arduino-cli compile --profile esp32-core3 firmware/Radar_V5` before flashing.

## PHYSICAL validation — all NOT established

Fill in **Result**, **Date** and **By** as you go; attach photos or serial logs under
`docs/validation/`. A test that fails is still useful — write down what happened.

| ID | Test | Pass criterion | Status | Result | Date | By |
|---|---|---|---|---|---|---|
| T-PRN-1 | Print the fit coupon; tap pilots; try clearances, servo cut-out, switch hole, nut pocket | chosen sizes recorded; CAD updated if needed | NOT RUN | | | |
| T-PRN-2 | Print the servo-fit subset (roof, hub, keeper) | prints without supports or failures | NOT RUN | | | |
| T-PRN-3 | Print P1 (body, front panel) and the sensor head | 45° deck and bridges print cleanly | NOT RUN | | | |
| T-FIT-1 | LCD in the front-panel locators; display aperture over the active area | no light leak; active area centred (else set `LCD_AA_OFFSET_X/Z`) | NOT RUN | | | |
| T-FIT-2 | ESP32 on its supports; cell holder on the anchors; USB-C receptacle flush with the rear opening | plug inserts fully; nothing forced | NOT RUN | | | |
| T-FIT-3 | Hub on spline under the keeper | 0.2–0.6 mm axial play; turns freely 30°–150° | NOT RUN | | | |
| T-FIT-4 | Head mast in socket, cross-bolt | no wobble; single orientation | NOT RUN | | | |
| T-PWR-1 | Bench power: no shorts; `OUT_5V`, `LOAD_5V` with switch ON/OFF | ≈5 V ON; `LOAD_5V` 0 V OFF | NOT RUN | | | |
| T-PWR-2 | Minimum running current of the complete scanner (servo holding, LCD on) | record mA; compare with the DFR1026 keep-alive (forum reports ~100 mA) | NOT RUN | | | |
| T-PWR-3 | **Open issue:** OFF → ON after 5 s, 60 s, 10 min; with and without USB-C | output returns without pressing KEY | NOT RUN | | | |
| T-PWR-4 | One-hour run | no drop-outs or resets | NOT RUN | | | |
| T-PWR-5 | Charge with scanner OFF; charge while ON | charging indicated both ways; nothing hot | NOT RUN | | | |
| T-FW-1 | Flash; splash then grid and sweep | as described in ASSEMBLY stage 4 | NOT RUN | | | |
| T-FW-2 | Display orientation and colours | correct with `INITR_GREENTAB`, rotation 1, no inversion — else record the settings that work | NOT RUN | | | |
| T-FW-3 | `CENTER_ONLY` horn fit; `REVERSE_SERVO` direction | pointer on 90° tick; screen matches head | NOT RUN | | | |
| T-FW-4 | Measured timing from the serial "# measured" line | record mean step and one-way sweep (estimate: ≈101 ms, ≈4.0 s) | NOT RUN | | | |
| T-FW-5 | Distance at 30 / 100 / 150 cm on the 90° line (flat target) | record reading vs tape measure | NOT RUN | | | |
| T-CAL-1 | Servo calibration against keeper ticks without hitting stops | record `SERVO_US_AT_0/180`; no buzzing at ends | NOT RUN | | | |
| T-SWP-1 | Powered sweep clearance with the sensor cable fitted | no rubbing, no cable tug at 30° or 150° | NOT RUN | | | |
| T-RUN-1 | Runtime from full charge | record hours | NOT RUN | | | |
| T-THM-1 | Temperatures after 30 min running and during charging (DFR1026, ESP32 regulator, cell) | nothing uncomfortable to touch; record °C if you have a thermometer | NOT RUN | | | |
| T-LNK-1 | Live link: telemetry tap (TX0 + GND only) to a 3.3 V adapter; live console connects at 115 200 baud | readings appear, sweep matches the real head, nothing resets or heats up | NOT RUN | | | |
| T-LNK-2 | Record a session in the console and replay it | replay matches the live view | NOT RUN | | | |
| T-APP-1 | Windows installer + portable build open and connect over the tap | app opens; port picker lists the adapter | NOT RUN | | | |
| T-APP-2 | macOS build opens (after Gatekeeper approval) and connects | as above | NOT RUN | | | |
| T-FLS-1 | Browser flasher (Flash page, Chrome/Edge) installs the release firmware on a bare ESP32 DevKit (harness unplugged) | splash screen appears after re-connecting the harness | NOT RUN | | | |
| T-REL-1 | First tagged release on GitHub carries the source ZIP, manufacturing kit, firmware, desktop apps, SHA256SUMS and attestations | `sha256sum -c` and `gh attestation verify` pass | NOT RUN | | | |

## Untested assumptions (every VERIFY value in the CAD)

| Variable | Assumed | Source of the assumption | Measured |
|---|---|---|---|
| `SERVO_BODY_L` × `SERVO_BODY_W` | 22.2 × 11.8 mm | SG90 datasheet overall size | |
| `SERVO_FLANGE_L`, `SERVO_FLANGE_T` | 32.2 mm, 2.5 mm | typical SG90 drawings | |
| `SERVO_FLANGE_BELOW`, `SERVO_CASE_ABOVE`, `SERVO_BOSS_ABOVE`, `SERVO_SPLINE_ABOVE` | 15.9, 6.8, 10.8, 15.1 mm | typical SG90 drawings (31 mm overall) | |
| `SERVO_HOLE_PITCH`, `SERVO_SHAFT_OFFSET` | 27.5 mm, 5.5 mm | typical SG90 drawings | |
| `HORN_LEN`, `HORN_ARM_W`, `HORN_ARM_T`, `HORN_COLLAR_D`, `HORN_SCREW_R` | 34, 6.2, 1.5, 7.2, 12 mm | estimate of a stock double-arm horn | |
| `HUB_BOTTOM_ABOVE_ROOF` | 13.0 mm | derived from the servo estimates | |
| `SR04_PCB_L/W`, `SR04_CAN_D/H`, `SR04_CAN_PITCH` | 45 × 20, Ø16 × 12, 26 mm | common HC-SR04 dimensions | |
| `SR04_HOLE_X/Y` | ±21, ±8.5 mm | estimate — boards vary; some have no holes | |
| `LCD_PCB_L/H`, `LCD_AA_W/H` | 56.5 × 34, 35.04 × 28.03 mm | Waveshare 1.8inch LCD Module wiki | |
| `LCD_AA_OFFSET_X/Z` | 0, 0 | not known — check against the Waveshare 2D drawing | |
| `SWITCH_PANEL_D`, `SWITCH_NUT_CLR_D` | 12.2, 17.0 mm | typical 12 mm switch | |
| `USBC_PCB_L/D`, `USBC_PCB_T`, `USBC_RECEPT_H`, `USBC_OPEN_W/H` | 20.4 × 14.2, 1.6, 3.3, 12.5 × 7.0 mm | Adafruit 4090 listed size (20.4 × 14.2 × 5.0) + estimates | |
| `ESP32_L/W` | 51.5 × 28.4 mm | typical 30-pin DevKit | |
| `CELL_HOLDER_L/W` | 77 × 21 mm | typical single 18650 holder | |
| `M2_PILOT_D`, `M2_CLEAR_D`, `M2_NUT_POCKET_AF` | 1.70, 2.25, 4.35 mm | print allowances — set from the coupon | |

## Electrical assumptions not yet checked on hardware

* The DFR1026 delivers a stable 5 V at the scanner's peak load (servo moving + ESP32 + LCD) — datasheet
  says up to 2.1 A output; not measured here.
* The DFR1026 restarts after OFF → ON — **open issue**, evidence suggests it may not (see WIRING.md).
* The HC-SR04 variant used gives ECHO ≈ 5 V; some clones differ.
* The chosen ST7735S revision works with `INITR_GREENTAB` / rotation 1 / no inversion at 15 MHz SPI.
* 1000–2000 µs covers 30°–150° of real travel on the chosen servo — probably not exactly; calibrate.
