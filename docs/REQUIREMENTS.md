# Requirements and traceability

What the scanner must do, how each requirement is verified, and where the evidence lives.
Verification methods: **I**nspection, **A**nalysis, **D**emonstration, **T**est. Evidence IDs point to
[`VALIDATION.md`](VALIDATION.md): `R-…` are recorded checks a computer can run, `T-…` are physical tests.

**Status** is filled in by `python scripts/gen_traceability.py` from `VALIDATION.md`:
*Met (recorded)* = all evidence is a passing recorded check; *Open* = at least one physical test has not
been run yet. Values marked *target* are proposed goals for an educational instrument — confirm or
change them after the first bench runs.

<!-- REQS:BEGIN -->
| ID | Requirement | Method | Evidence | Status |
|---|---|---|---|---|
| RQ-F-01 | Sweep the sensor through a **commanded** 30°–150° in 3° steps and back, centring at boot. | D, A | R-EQ-1, T-FW-1, T-CAL-1 | Open |
| RQ-F-02 | Compute distance as d = v·t/2 and show 2 cm up to the selected range; show `---` for no echo or out of range. | A, T | R-EQ-1, T-FW-5 | Open |
| RQ-F-03 | Draw a radar-style display on the 320 × 240 screen: semicircular grid, sweep beam, fading detections, angle, distance and range readout. | D | R-FW-3, T-FW-1, T-FW-2 | Open |
| RQ-F-04 | Touch controls: − / + step the range through 50–400 cm; tapping the fan pauses and resumes. | D | R-FW-1, T-FW-6 | Open |
| RQ-F-05 | Provide `CENTER_ONLY` (head fitting), `REVERSE_SERVO` and `CALIBRATE_SERVO` modes. | D | R-FW-1, T-FW-3, T-CAL-1 | Open |
| RQ-F-06 | Print one `angle,distance` line per reading at 115 200 baud over the same USB cable for logging and the live console. | T | R-APP-1, T-LNK-1, T-LNK-2 | Open |
| RQ-F-07 | Run from one USB cable (charger or power bank ≥ 1 A); no battery inside. | T | R-BOM-1, T-PWR-1, T-PWR-2 | Open |
| RQ-F-08 | The on-board RGB LED turns red when something is closer than 30 cm. | D | R-FW-1, T-FW-7 | Open |
| RQ-P-01 | One-way sweep ≤ 5 s at default settings (estimate 4.6 s). | A, T | R-EQ-1, T-FW-4 | Open |
| RQ-P-02 | *Target:* distance within ±3 cm of a tape measure at 30, 100 and 150 cm on a flat target. | T | T-FW-5 | Open |
| RQ-P-03 | Servo travel calibrated without driving into its end stops. | T | T-CAL-1 | Open |
| RQ-P-04 | No resets or screen flicker over a one-hour run from a ≥ 1 A supply. | T | T-PWR-2, T-PWR-3, T-PWR-4 | Open |
| RQ-S-01 | The sensor runs from 3.3 V, so ECHO never exceeds the ESP32's 3.3 V logic; a 5 V-only sensor is used only with the documented divider. | A, I | R-EQ-1, R-SYNC-1 | Met (recorded) |
| RQ-S-02 | The servo is powered from VIN (USB 5 V), never from 3.3 V; VIN is measured before the servo is connected. | I, T | R-SYNC-1, T-PWR-1 | Open |
| RQ-S-03 | The USB serial (TX/RX) and backlight pins are never wired. | I | R-SYNC-1 | Met (recorded) |
| RQ-S-04 | The instrument is labelled "educational — not a safety device" on the case and the start-up screen. | I, D | R-CAD-1, R-FW-1, T-FW-1 | Open |
| RQ-S-05 | No part is uncomfortable to touch after 30 min running. | T | T-THM-1 | Open |
| RQ-I-01 | Every connection follows the `WIRING.md` net list, and firmware pin constants match it. | I | R-SYNC-1 | Met (recorded) |
| RQ-I-02 | ESP32-2432S028R (CYD) with ILI9341 or ST7789 panel; no flash pins used, no strapping pins on the external wires, no outputs on input-only pins. | I | R-SYNC-1, T-FW-2 | Open |
| RQ-I-03 | Seven wires, all through the CYD's JST connectors: no breadboard, no soldering to the board. | I | R-SYNC-1, R-MFG-1 | Met (recorded) |
| RQ-M-01 | Every printed part fits a Bambu Lab A1 mini (180 × 180 × 180 mm) and prints without supports. | A, T | R-CAD-3, T-PRN-2, T-PRN-3 | Open |
| RQ-M-02 | No loose fasteners: press fits plus the screws that come with the servo. | I, T | R-BOM-1, T-FIT-2, T-FIT-3 | Open |
| RQ-M-03 | The head and horn clear the shell and servo through the commanded travel plus 15° margin. | A, T | R-CAD-5, T-SWP-1 | Open |
| RQ-M-04 | Peg, sensor-hole and screw-pilot allowances are confirmed with the fit coupon before the full print. | T | T-PRN-1 | Open |
| RQ-M-05 | Modules (CYD, servo, sensor) fit without force; no model interference. | A, T | R-CAD-4, T-FIT-1, T-FIT-3, T-FIT-4 | Open |
| RQ-M-06 | All CAD outputs regenerate from one CadQuery source as valid, watertight single solids. | A | R-CAD-1, R-CAD-2 | Met (recorded) |
| RQ-M-07 | Minimum parts: 5 purchased items (+1 optional) and 4 printed parts. | I | R-BOM-1, R-MFG-1 | Met (recorded) |
| RQ-SW-01 | Firmware compiles with zero warnings on the pinned ESP32 cores 3.x and 2.x. | T | R-FW-1, R-FW-2 | Met (recorded) |
| RQ-SW-02 | No Wi-Fi or Bluetooth in the firmware; the consoles never write to the scanner. | I | R-SYNC-1, R-APP-5 | Met (recorded) |
| RQ-SW-03 | Build guide, simulator and live console work offline in the web app and the desktop app on Linux, Windows and macOS. | T | R-APP-2, R-APP-3, T-APP-1, T-APP-2 | Open |
| RQ-SW-04 | Firmware can be installed from a browser without installing a toolchain. | D | R-FLS-1, T-FLS-1 | Open |
| RQ-SW-05 | Every release carries checksums, a build-provenance attestation and a toolchain SBOM. | I | T-REL-1 | Open |
| RQ-O-01 | Everything needed to build it is in editable open formats (CadQuery, STEP, STL/3MF, Markdown, CSV) under the MIT licence. | I | R-CAD-1, R-BOM-1 | Met (recorded) |
<!-- REQS:END -->
