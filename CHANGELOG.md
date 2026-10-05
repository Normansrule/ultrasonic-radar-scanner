# Changelog

## 6.0.0 — 2026-10-04 (Radar V6 "Mini": nicer, fewer parts, cheaper)

New hardware design. Nothing has been physically validated yet.

- **Electronics: 3 modules, 7 wires.** The ESP32 DevKit + 1.8" LCD are replaced by one
  ESP32-2432S028R "Cheap Yellow Display" (ESP32 + 2.8" 320 × 240 touch screen + RGB LED + USB).
  The HC-SR04 + resistor divider is replaced by a 3.3 V RCWL-1601 / HC-SR04P. Wiring goes through the
  board's JST connectors — no breadboard, no soldering to the board.
- **Power: one USB cable.** The 18650 cell, holder, charger/boost module, USB-C breakout, fuse,
  switch and 1000 µF capacitor are gone (and with them the open charger-restart issue).
- **Enclosure: four printed parts, no loose screws.** Ivory console with the screen tilted back 20°,
  a slide-in bezel the CYD presses onto, a press-fit base, and a mint "two-eye" sensor head on a neck.
  Printed without supports; only the two screws that come with the servo.
- **Firmware V6:** 320 × 240 UI with a glowing beam, touch −/+ range (50–400 cm) and pause,
  automatic ILI9341 / ST7789 panel detection, near-object LED, band-buffered drawing, same serial
  format. Live console now works over the scanner's own USB cable.
- Photo-style Cycles renders, an illustrated 7-wire picture, a new parts-kit graphic; BOM, wiring,
  assembly, requirements (33), validation log and build packet rewritten for V6.
- Purchased line items drop from 20 to 5 (+1 optional); estimated parts cost about US$18–30
  (rough single-unit estimate, not a quote).


## 5.2.0 — 2026-10-02 (manufacturing package)

Hardware baseline unchanged (Radar V5.1). Nothing has been physically validated yet.

- `docs/REQUIREMENTS.md`: 36 numbered requirements with verification method and evidence, status
  generated from `VALIDATION.md` (`scripts/gen_traceability.py`) plus a status graphic.
- `manufacturing/`: spreadsheet-ready `bom.csv`, `printed_parts.csv`, pin-by-pin `wiring_pins.csv`,
  point-to-point `wire_list.csv` (W01–W28), and a printable `build_packet.pdf` traveller with tick
  boxes for parts, wires, gates and physical tests — all generated from the docs.
- Visual parts-kit overview (`hardware/diagrams/bom_overview.svg`).
- Browser firmware flasher (Flash page, ESP Web Tools) fed by a firmware image compiled in the Pages
  workflow; firmware images attached to releases.
- Release now also attaches a **manufacturing kit** ZIP (3D files, CSVs, build packet, diagrams, firmware).
- README rewritten to be short and visual.

## 5.1.0 — 2026-10-02 (repository baseline)

First open-source packaging of the Radar V5.1 baseline. Nothing in this release has been physically
validated; see `docs/VALIDATION.md`.

Repository
- CadQuery model of record with every dimension as a named variable and VERIFY marks; one script
  regenerates STL (print orientation), STEP (assembled position + assembly), an A1 mini
  multi-plate 3MF, core-spec plate fallbacks and build-stage plates.
- Recorded geometry checks (79): valid solids, nominal sizes, watertight meshes, plate fit,
  22 interference pairs, ±75° sweep clearance, designed clearances.
- Firmware compiles with zero warnings on Arduino-ESP32 3.3.12 and 2.0.17; versions pinned in
  `sketch.yaml` profiles.
- Wiring, BOM, assembly, printing, equations, validation, security, publishing and glossary docs;
  generated wiring SVGs, callouts, renders and a simulated sweep GIF; GitHub Pages site.
- Tests tie the firmware pins to the wiring net list and encode the wiring safety rules.
- Supply chain: pinned Actions (by commit), least-privilege workflows, Dependabot, CodeQL,
  CycloneDX SBOM, release ZIP with SHA256SUMS and signed build provenance.

Web app and desktop app
- Live console: listen-only Web Serial link, replay of saved logs, labelled demo, session recording
  to CSV; one shared parser (`site/assets/radar-core.js`) tested against the firmware's exact formats.
- Installable web app (manifest + service worker, offline after first visit).
- Desktop app (Electron 44.5.1): locked-down window, serial-port picker, offline KaTeX; Linux AppImage
  + tar.gz, Windows installer + portable, macOS dmg (arm64 + x64) built by the release workflow.
- Optional two-wire telemetry tap (TX0 + GND to a 3.3 V adapter) so the live link never breaks the
  "no ESP32 USB while the harness is connected" rule.

Improvements over the brief
- 45° self-supporting deck under the roof and gussets for the roof screws, so the body prints
  without supports.
- Keyed (one-way) mast/socket with an M2×20 cross-bolt and captive-nut pocket.
- Engraved 30°–150° angle ticks on the turret keeper plus a pointer groove on the hub, used by the
  new `CALIBRATE_SERVO` mode to calibrate travel without hitting the servo stops.
- Hard pulse-width clamp (900–2100 µs) in the firmware, independent of the calibration values.
- Full-frame off-screen buffer for a flicker-free display; measured step and sweep times printed
  over serial each pass; CSV output for the serial plotter.
- LCD SPI clock set to 15 MHz, inside the ST7735S 66 ns write-cycle spec (library default is 32 MHz).
- Range labels moved inside the fan after the display simulator showed them clipped at the edge.
- ESP32 end supports, zip-tie anchors for the cell holder, a USB-C breakout cradle, a sensor-cable
  slot and a rear knock-out reserved for the DFR1026 KEY fall-back.
- Open power issue researched: field reports indicate the DFR1026 may switch off at light load and
  need its KEY; two documented fall-backs (rear KEY button, or PowerBoost 1000C with EN switching).
