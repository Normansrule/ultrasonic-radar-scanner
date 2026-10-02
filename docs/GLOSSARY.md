# Glossary

Every abbreviation is written out once with its short form in brackets, as used in the rest of the
documentation.

| Term | Meaning |
|---|---|
| 3D Manufacturing Format (3MF) | A print-file format that can hold several objects, their placement and slicer settings in one file. |
| Analog-to-Digital Converter (ADC) | Not used in this build; mentioned only because battery-voltage measurement would need one. |
| American Wire Gauge (AWG) | Wire thickness scale; smaller numbers are thicker. Power leads here are 22 AWG. |
| Bill of Materials (BOM) | The shopping list: every part, how many, and what to check. |
| Build packet | The printable PDF traveller in `manufacturing/` with tick boxes for every part, wire, gate and test. |
| Bulk capacitor | A large capacitor (here 1000 µF) that supplies short current bursts, so the servo's spikes do not dip the 5 V rail. |
| CadQuery | A Python library for writing 3D models as code. `cad/build_radar_v5.py` is the model of record. |
| Commanded angle | The angle the firmware *asks* the servo for. Nothing measures the real angle. |
| Configuration Channel (CC) pins | Two USB-C pins. 5.1 kΩ resistors to ground on both tell a USB-C charger to supply 5 V. |
| CycloneDX | A standard file format for a software bill of materials. |
| Development board (DevKit) | A module mounted on a board with a USB port, regulator and headers. |
| Duty (cycle) | The fraction of each PWM period that the signal is high. |
| ECHO / TRIG | HC-SR04 pins: a 10 µs pulse on TRIG starts a ping; ECHO stays high for as long as the sound took to return. |
| Electrostatic discharge (ESD) | Static shocks that can damage modules — touch something grounded before handling boards. |
| AppImage | A single-file Linux application format; make it executable and run it. |
| Content Security Policy (CSP) | Browser rules that limit what a page may load or run; the desktop app's pages carry a strict one. |
| Electron | A framework that wraps web pages in a desktop window; used for the desktop app. |
| ESP Web Tools | An open-source web page component that flashes ESP32 boards from Chrome or Edge; used on the Flash page. |
| Fit coupon | A small printed test piece that checks hole and slot sizes before the long prints. |
| General-Purpose Input/Output (GPIO) | A numbered microcontroller pin that firmware can read or drive. |
| Ground (GND) | The shared 0 V reference all voltages are measured from. |
| Harness | All the leads that plug onto the ESP32, unplugged together for programming. |
| Horn | The plastic arm supplied with a servo that grips its splined output shaft. |
| Keyed | Shaped so it only fits one way (the sensor mast, the J1 power plug). |
| LED Control (LEDC) | The ESP32 peripheral that generates PWM in hardware; used here for the servo. |
| Liquid-Crystal Display (LCD) | The 1.8" screen; driven by an ST7735S controller chip. |
| Lithium-ion (Li-ion) | The 18650 cell's chemistry. Safe when protected, fused and not abused. |
| Master Out, Slave In (MOSI) / Serial Clock (SCK) | The SPI data and clock lines (the LCD labels them DIN and CLK). |
| Net | Every pin that is electrically connected together. |
| Merged image | One firmware file containing bootloader, partition table and app, flashed at address 0x0. |
| Pilot hole | A slightly undersized printed hole that you cut threads into with a tap. |
| Progressive Web App (PWA) | A website that can be installed and used offline like an app. |
| Polylactic acid (PLA) | The plastic used for printing. |
| Power Delivery (PD) | A USB-C protocol for raising voltage to 9–20 V. **Not** used here — 5 V only. |
| Printed Circuit Board (PCB) | A board with copper tracks. This project uses ready-made module boards and no custom PCB. |
| Pulse-Width Modulation (PWM) | A repeating square wave whose high time carries a value. |
| Radar-style display | A fan-shaped picture like a radar screen. The sensing here is ultrasonic, not radio. |
| Serial Peripheral Interface (SPI) | A fast clocked bus used for the LCD. |
| Software Bill of Materials (SBOM) | A list of the software components and exact versions used to build the project. |
| Traceability | Linking every requirement to the check or test that proves it (`docs/REQUIREMENTS.md`). |
| Telemetry tap | The optional two-wire, listen-only link (TX0 + GND) from the ESP32 to a USB-to-serial adapter. |
| Spline | The toothed servo output shaft. |
| Standard for the Exchange of Product model data (STEP) | A precise CAD exchange format for editing the parts in other CAD tools. |
| Stereolithography file (STL) | A triangle-mesh file that slicers read. |
| Strapping pin | An ESP32 pin whose level at power-up selects a boot mode (GPIO 0, 2, 5, 12, 15) — avoided here. |
| Universal Asynchronous Receiver-Transmitter (UART) | The serial port the firmware prints on (115 200 baud); TX0 is its transmit pin. |
| Universal Serial Bus Type-C (USB-C) | The reversible connector used for charging. The rear port carries power only. |
| VERIFY | A CAD dimension that depends on your purchased module and must be measured before printing the full set. |
| Voltage divider | Two resistors in series that output a fixed fraction of their input voltage. |
| Web Serial | The browser interface (Chrome/Edge, and the desktop app) that lets a page read a serial port after you pick it. |
| Windows Subsystem for Linux (WSL) | Runs Ubuntu inside Windows; the publish script supports it. |
