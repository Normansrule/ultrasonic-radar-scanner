# Credits and sources

Every module datasheet the design relies on, and what was taken from it. "Checked" means the value
was read from the linked source while writing this repository (2026-09-30); "unverified" means it
is a typical value that could not be confirmed from a primary source — treat it as a VERIFY item.

## Module datasheets and product pages

| Module | Source | Used for | Status |
|---|---|---|---|
| ESP32-WROOM-32 module | [Espressif ESP32-WROOM-32 datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32_datasheet_en.pdf) | pins, 3.3 V logic, module vs WROVER differences (GPIO16/17) | checked (link); pin rules also encoded in `tests/test_sync.py` |
| ESP32 chip | [Espressif ESP32 series datasheet](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf) | input-high threshold 0.75·VDD, absolute maximum VDD + 0.3 V, strapping pins (0, 2, 5, 12, 15), flash pins (6–11), input-only pins (34–39) | values as commonly quoted — confirm in the DC-characteristics table |
| HC-SR04 | [ElecFreaks HC-SR04 datasheet (SparkFun mirror)](https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf) | 5 V supply, 10 µs trigger, ECHO pulse width ∝ distance, ≥60 ms measurement cycle, 45 × 20 × 15 mm | datasheet located; mounting-hole positions **unverified** (boards vary) |
| ST7735S controller | [Sitronix ST7735S v1.1 datasheet (SparkFun mirror)](https://cdn.sparkfun.com/assets/9/0/2/5/8/ST7735S_v1.1.pdf) | serial write clock cycle ≥ 66 ns → firmware uses 15 MHz SPI | checked (TSCYCW = 66 ns) |
| Waveshare 1.8" LCD module | [Waveshare wiki — 1.8inch LCD Module](https://www.waveshare.com/wiki/1.8inch_LCD_Module) | 56.5 × 34 mm board, 35.04 × 28.03 mm active area, 128 × 160, pin names, 3.3 V/5 V | checked; active-area offset on the board **unverified** |
| DFRobot DFR1026 | [DFRobot product page — DC-DC Charge Discharge Integrated Module (5V 2A)](https://www.dfrobot.com/product-2632.html) | 4.6–5.4 V input, 0–2.1 A charge, 5 V 0–2.1 A output, 25 × 16 mm, 2.54 mm pads, KEY: short press enables output, ~10 s press disables | checked |
| DFR1026 field reports | [Core Electronics forum thread on the DFR1026](https://forum.core-electronics.com.au/t/dc-dc-charge-discharge-integrated-module-5v-2a-dfr1026/18135) | reports of output shutting off at light load after ~30 s and needing KEY; keep-alive nearer 100 mA | user reports, **not** manufacturer data — basis of the open issue |
| Adafruit 4090 USB-C breakout | [Adafruit product 4090](https://www.adafruit.com/product/4090) · [The Pi Hut listing](https://thepihut.com/products/adafruit-usb-c-breakout-board-downstream-connection-ada4090) | 20.4 × 14.2 × 5.0 mm, 5.1 kΩ CC pull-downs so a USB-C source supplies 5 V | size checked via retailer; that **both** CC1 and CC2 carry 5.1 kΩ should be confirmed on the board/schematic |
| SG90 servo | [TowerPro SG90 datasheet (DatasheetCafe copy)](https://www.datasheetcafe.com/sg90-datasheet-pdf-9-g-micro-servo/) | 22.2 × 11.8 × 31 mm, 4.8–5 V, 0.1 s/60°, 10 µs dead band | overall size checked; flange, hole pitch, shaft offset and horn dimensions **unverified** |
| Adafruit PowerBoost 1000C (Option B only) | [Adafruit learn guide — pinouts](https://learn.adafruit.com/adafruit-powerboost-1000c-load-share-usb-charge-boost/pinouts) | EN pulled high by default; tie EN to GND to turn the boost off; USB pad is the charge input | checked; charging with EN low and current headroom **unverified** |

## Software and references

| Item | Source |
|---|---|
| ESP Web Tools 10.4.0 (browser flasher) | [github.com/esphome/esp-web-tools](https://github.com/esphome/esp-web-tools) (Apache-2.0), loaded from unpkg.com on the Flash page |
| ReportLab 4.4 (build packet PDF) | [reportlab.com/opensource](https://www.reportlab.com/opensource/) (BSD) |
| DejaVu Sans fonts (in `manufacturing/fonts/`) | [dejavu-fonts.github.io](https://dejavu-fonts.github.io/) — Bitstream Vera licence, copy in `manufacturing/fonts/LICENSE-DejaVu.txt` |
| Arduino-ESP32 core, LEDC API | [Espressif — LEDC API](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/ledc.html) and the [2.x → 3.0 migration guide](https://docs.espressif.com/projects/arduino-esp32/en/latest/migration_guides/2.x_to_3.0.html) (ledcSetup/ledcAttachPin → ledcAttach) |
| Adafruit GFX Library 1.12.6 | [github.com/adafruit/Adafruit-GFX-Library](https://github.com/adafruit/Adafruit-GFX-Library) (BSD licence) |
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
