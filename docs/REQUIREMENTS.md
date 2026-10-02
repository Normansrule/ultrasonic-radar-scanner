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
| RQ-F-01 | Sweep the HC-SR04 through a **commanded** 30°–150° in 3° steps and back, centring at boot. | D, A | R-EQ-1, T-FW-1, T-CAL-1 | Open |
| RQ-F-02 | Compute distance as d = v·t/2 and show 2–200 cm; show `---` for no echo or out of range. | A, T | R-EQ-1, T-FW-5 | Open |
| RQ-F-03 | Draw a radar-style display: semicircular grid, sweep line, fading detections, angle and distance readout. | D | R-FW-3, T-FW-1, T-FW-2 | Open |
| RQ-F-04 | Provide `CENTER_ONLY` (horn fitting), `REVERSE_SERVO` and `CALIBRATE_SERVO` modes. | D | R-FW-1, T-FW-3, T-CAL-1 | Open |
| RQ-F-05 | Print one `angle,distance` line per reading at 115 200 baud for logging and the live console. | T | R-APP-1, T-LNK-1, T-LNK-2 | Open |
| RQ-F-06 | Run from one protected 18650 cell; charge from USB-C with the scanner switched OFF. | T | T-PWR-1, T-PWR-5 | Open |
| RQ-F-07 | Turn on and off with the front latching switch without opening the case, and stay on while running (open power issue). | T | T-PWR-2, T-PWR-3, T-PWR-4 | Open |
| RQ-P-01 | One-way sweep ≤ 5 s at default settings (estimate 4.0 s). | A, T | R-EQ-1, T-FW-4 | Open |
| RQ-P-02 | *Target:* distance within ±3 cm of a tape measure at 30, 100 and 150 cm on a flat target. | T | T-FW-5 | Open |
| RQ-P-03 | *Target:* ≥ 2 h runtime from a full charge. | T | T-RUN-1 | Open |
| RQ-P-04 | Servo travel calibrated without driving into its end stops. | T | T-CAL-1 | Open |
| RQ-S-01 | A 3 A fuse is the first item on the battery positive lead. | I, T | R-SYNC-1, T-PWR-1 | Open |
| RQ-S-02 | A bare cell never feeds the ESP32, servo, sensor or display. | I | R-SYNC-1 | Met (recorded) |
| RQ-S-03 | HC-SR04 ECHO reaches the ESP32 only through the 2.2 k/3.3 k divider; GPIO stays ≤ 3.6 V at worst case. | A, I | R-EQ-1, R-SYNC-1 | Met (recorded) |
| RQ-S-04 | Servo and sensor run from the switched 5 V rail, never from 3V3. | I | R-SYNC-1 | Met (recorded) |
| RQ-S-05 | Protected cell rated ≥ 2.1 A charge and ≥ 3 A discharge; switch rated ≥ 2 A at 5 V DC. | I | R-BOM-1 | Met (recorded) |
| RQ-S-06 | USB-C input negotiates 5 V only (5.1 kΩ on CC1 and CC2, no Power Delivery trigger). | I | R-BOM-1, R-SYNC-1 | Met (recorded) |
| RQ-S-07 | The instrument is labelled "educational — not a safety device" on the case and the start-up screen. | I, D | R-CAD-1, R-FW-1, T-FW-1 | Open |
| RQ-S-08 | The ESP32's own USB port is never connected while the battery harness is; the live link is a listen-only tap. | I | R-APP-5, T-LNK-1 | Open |
| RQ-S-09 | No part is uncomfortable to touch after 30 min running or during charging. | T | T-THM-1 | Open |
| RQ-I-01 | Every connection follows the `WIRING.md` net list, and firmware pin constants match it. | I | R-SYNC-1 | Met (recorded) |
| RQ-I-02 | Classic 30-pin ESP32-WROOM-32 DevKit; no flash, strapping or input-only pins used as outputs. | I | R-SYNC-1 | Met (recorded) |
| RQ-M-01 | Every printed part fits a Bambu Lab A1 mini (180 × 180 × 180 mm) and prints without supports. | A, T | R-CAD-3, T-PRN-2, T-PRN-3 | Open |
| RQ-M-02 | M2 fasteners only; counts in the BOM match their uses. | I | R-BOM-1 | Met (recorded) |
| RQ-M-03 | The turret clears the keeper, roof, body and servo through the commanded travel plus 15° margin. | A, T | R-CAD-5, T-SWP-1 | Open |
| RQ-M-04 | Hole and slot allowances are confirmed with the fit coupon before the full print. | T | T-PRN-1 | Open |
| RQ-M-05 | Modules (LCD, ESP32, USB-C breakout, cell holder) fit without force; no model interference. | A, T | R-CAD-4, T-FIT-1, T-FIT-2 | Open |
| RQ-M-06 | Rotor hub axial play 0.2–0.6 mm under the keeper; mast fits one way only. | A, T | R-CAD-6, T-FIT-3, T-FIT-4 | Open |
| RQ-M-07 | All CAD outputs regenerate from one CadQuery source as valid, watertight single solids. | A | R-CAD-1, R-CAD-2 | Met (recorded) |
| RQ-M-08 | No custom PCB: off-the-shelf modules, hand wiring, one keyed disconnect for programming. | I | R-SYNC-1, R-BOM-1 | Met (recorded) |
| RQ-SW-01 | Firmware compiles with zero warnings on the pinned ESP32 cores 3.x and 2.x. | T | R-FW-1, R-FW-2 | Met (recorded) |
| RQ-SW-02 | No Wi-Fi or Bluetooth in the firmware; the consoles never write to the scanner. | I | R-SYNC-1, R-APP-5 | Met (recorded) |
| RQ-SW-03 | Build guide, simulator and live console work offline in the web app and the desktop app on Linux, Windows and macOS. | T | R-APP-2, R-APP-3, T-APP-1, T-APP-2 | Open |
| RQ-SW-04 | Firmware can be installed from a browser without installing a toolchain. | D | T-FLS-1 | Open |
| RQ-SW-05 | Every release carries checksums, a build-provenance attestation and a toolchain SBOM. | I | T-REL-1 | Open |
| RQ-O-01 | Everything needed to build it is in editable open formats (CadQuery, STEP, STL/3MF, Markdown, CSV) under the MIT licence. | I | R-CAD-1, R-BOM-1 | Met (recorded) |
<!-- REQS:END -->
