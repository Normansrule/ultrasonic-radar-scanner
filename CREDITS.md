# Credits and sources

Every module datasheet the design relies on, and what was taken from it. "Checked" means the value
was read from the linked source while writing this repository (2026-09-30 to 2026-10-04); "unverified" means it
is a typical value that could not be confirmed from a primary source — treat it as a ## Module datasheets and product pages

| Module | Source | Used for | Status |
|---|---|---|---|
| ESP32-2432S028R "Cheap Yellow Display" | [witnessmenow/ESP32-Cheap-Yellow-Display](https://github.com/witnessmenow/ESP32-Cheap-Yellow-Display) (MIT) — `PINS.md`, schematics, community 3D model | display SPI (14/12/13/15/2, backlight 21), touch SPI (25/39/32/33/36), RGB LED (4/16/17, active low), connectors CN1 (GND/IO22/IO27/3.3V), P3 (GND/IO35/IO22/IO21), P1 (VIN/TX/RX/GND), board outline and holes | checked from the community documentation; **not** a manufacturer datasheet — clones vary, VERIFY |
| CYD pinout cross-checks | [Random Nerd Tutorials — CYD pinout](https://randomnerdtutorials.com/esp32-cheap-yellow-display-cyd-pinout-esp32-2432s028r/) · [Mischianti — ESP32-2432S028 pinout and schema](https://mischianti.org/esp32-2432s028-cheap-yellow-display-high-resolution-pinout-datasheet-schema-and-specs/) | same pins from independent write-ups; CYD2USB (ST7789) variant notes | cross-checked |
| ESP32 chip | [Espressif ESP32 series datasheet](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf) | input-high threshold 0.75·VDD, absolute maximum VDD + 0.3 V, strapping pins (0, 2, 5, 12, 15), flash pins (6–11), input-only pins (34–39) | values as commonly quoted — confirm in the DC-characteristics table |
| RCWL-1601 ultrasonic sensor | [Adafruit 4007 — Ultrasonic Distance Sensor, 3 V or 5 V](https://www.adafruit.com/product/4007) | runs from 3–5 V, so at 3.3 V its ECHO is 3.3 V logic; HC-SR04 footprint | checked (product page) |
| HC-SR04 (footprint and fallback) | [ElecFreaks HC-SR04 datasheet (SparkFun mirror)](https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf) | 10 µs trigger, ECHO pulse width ∝ distance, ≥ 60 ms cycle, 45 × 20 mm board, 5 V ECHO on the classic part | datasheet located; can diameter and pitch **unverified** across clones |
| ILI9341 controller | [Adafruit ILI9341 library](https://github.com/adafruit/Adafruit_ILI9341) | panel ID read (0xD3 → 0x93 0x41) for auto-detection | used as implemented in the library |
| XPT2046 touch controller | [PaulStoffregen/XPT2046_Touchscreen](https://github.com/PaulStoffregen/XPT2046_Touchscreen) | touch on its own SPI bus | used as implemented |
| SG90 servo | [TowerPro SG90 datasheet (DatasheetCafe copy)](https://www.datasheetcafe.com/sg90-datasheet-pdf-9-g-micro-servo/) | 22.2 × 11.8 × 31 mm, 4.8–5 V, 0.1 s/60°, 10 µs dead band | overall size checked; flange, hole pitch, shaft offset and horn dimensions **unverified** |

verified** |

## Software and references

| Item | Source |
|---|---|
| ESP Web Tools 10.4.0 (browser flasher) | [github.com/esphome/esp-web-tools](https://github.com/esphome/esp-web-tools) (Apache-2.0), loaded from unpkg.com on the Flash page |
| ReportLab 4.4 (build packet PDF) | [reportlab.com/opensource](https://www.reportlab.com/opensource/) (BSD) |
| DejaVu Sans fonts (in `manufacturing/fonts/`) | [dejavu-fonts.github.io](https://dejavu-fonts.github.io/) — Bitstream Vera licence, copy in `manufacturing/fonts/LICENSE-DejaVu.txt` |
| Arduino-ESP32 core, LEDC API | [Espressif — LEDC API](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/ledc.html) and the [2.x → 3.0 migration guide](https://docs.espressif.com/projects/arduino-esp32/en/latest/migration_guides/2.x_to_3.0.html) (ledcSetup/ledcAttachPin → ledcAttach) |
| Adafruit GFX Library 1.12.6 | [github.com/adafruit/Adafruit-GFX-Library](https://github.com/adafruit/Adafruit-GFX-Library) (BSD licence) |
| Adafruit ILI9341 1.6.4 | [github.com/adafruit/Adafruit_ILI9341](https://github.com/adafruit/Adafruit_ILI9341) (MIT licence) |
| XPT2046_Touchscreen 1.4 | [github.com/PaulStoffregen/XPT2046_Touchscreen](https://github.com/PaulStoffregen/XPT2046_Touchscreen) |
| Blender 4.2 (`bpy`, renders) | [blender.org](https://www.blender.org/) (GPL; used as a tool, nothing redistributed) |
| Adafruit ST7735 and ST7789 Library 1.11.0 | [github.com/adafruit/Adafruit-ST7735-Library](https://github.com/adafruit/Adafruit-ST7735-Library) (MIT licence) |
| Adafruit BusIO 1.17.4 | [github.com/adafruit/Adafruit_BusIO](https://github.com/adafruit/Adafruit_BusIO) (MIT licence) |
| CadQuery 2.8 | [github.com/CadQuery/cadquery](https://github.com/CadQuery/cadquery) (Apache 2.0) |
| arduino-cli sketch profiles | [Arduino CLI — sketch project file](https://arduino.github.io/arduino-cli/latest/sketch-project-file/) |
| OWASP Top 10:2025 — A03 Software Supply Chain Failures | [owasp.org/Top10/2025/A03_2025-Software_Supply_Chain_Failures](https://owasp.org/Top10/2025/A03_2025-Software_Supply_Chain_Failures/) |
| Speed of sound in air, $v ≈ 331.3 + 0.606\,T$ | standard linear approximation for dry air near room temperature; e.g. [Wikipedia — Speed of sound](https://en.wikipedia.org/wiki/Speed_of_sound) |

The display simulator (`scripts/sim_display.py`) reads the 5×7 font from your locally installed
Adafruit GFX library at run time; the font is not redistributed here.

## People

Design, brief and project ownership: Aleksander Norman. Repository structure, CadQuery model,
firmware, generators and documentation drafted with AI assistance (Claude, Anthropic) and to be
reviewed and physically validated by the maintainer.
