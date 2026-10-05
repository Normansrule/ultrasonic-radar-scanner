# Glossary

Every abbreviation is written out once with its short form in brackets, as used in the rest of the
documentation.

| Term | Meaning |
|---|---|
| 3D Manufacturing Format (3MF) | A print-file format that can hold several objects, their placement and slicer settings in one file. |
| Bill of Materials (BOM) | The shopping list: every part, how many, and what to check. |
| Build packet | The printable PDF traveller in `manufacturing/` with tick boxes for every part, wire, gate and test. |
| CadQuery | A Python library for writing 3D models as code. `cad/build_radar.py` is the model of record. |
| Cheap Yellow Display (CYD) | Community name for the ESP32-2432S028R: an ESP32, a 2.8" 320 × 240 touch screen, an RGB LED and USB on one yellow board. |
| JST 1.25 mm connector | The small 4-pin sockets on the back of the CYD (CN1, P3, P1); cables with a JST plug on one end and Dupont sockets on the other plug into them. |
| Dupont connector | The 2.54 mm push-on jumper connector used on hobby modules and servo plugs. |
| ILI9341 / ST7789 | The two display controller chips found on CYD boards; the firmware detects which one you have. |
| XPT2046 | The CYD's resistive touch controller. |
| Press fit | A joint held by friction because the hole is very slightly smaller than the part pushed into it. |
| Crush rib | A thin printed ridge that deforms slightly to make a firm press fit. |
| VIN | The CYD's P1 pin that carries the USB 5 V; it powers the servo. |
| Liquid-Crystal Display (LCD) / Thin-Film Transistor (TFT) | The colour screen technology on the CYD. |
| Commanded angle | The angle the firmware *asks* the servo for. Nothing measures the real angle. |
| CycloneDX | A standard file format for a software bill of materials. |
| Duty (cycle) | The fraction of each PWM period that the signal is high. |
| ECHO / TRIG | Ultrasonic sensor pins: a 10 µs pulse on TRIG starts a ping; ECHO stays high for as long as the sound took to return. |
| Electrostatic discharge (ESD) | Static shocks that can damage modules — touch something grounded before handling boards. |
| AppImage | A single-file Linux application format; make it executable and run it. |
| Content Security Policy (CSP) | Browser rules that limit what a page may load or run; the desktop app's pages carry a strict one. |
| Electron | A framework that wraps web pages in a desktop window; used for the desktop app. |
| ESP Web Tools | An open-source web page component that flashes ESP32 boards from Chrome or Edge; used on the Flash page. |
| Fit coupon | A small printed test piece that checks hole and slot sizes before the long prints. |
| General-Purpose Input/Output (GPIO) | A numbered microcontroller pin that firmware can read or drive. |
| Ground (GND) | The shared 0 V reference all voltages are measured from. |
| Horn | The plastic arm supplied with a servo that grips its splined output shaft. |
| LED Control (LEDC) | The ESP32 peripheral that generates PWM in hardware; used here for the servo. |
| Net | Every pin that is electrically connected together. |
| Merged image | One firmware file containing bootloader, partition table and app, flashed at address 0x0. |
| Progressive Web App (PWA) | A website that can be installed and used offline like an app. |
| Polylactic acid (PLA) | The plastic used for printing. |
| Printed Circuit Board (PCB) | A board with copper tracks. This project uses ready-made module boards and no custom PCB. |
| Pulse-Width Modulation (PWM) | A repeating square wave whose high time carries a value. |
| Radar-style display | A fan-shaped picture like a radar screen. The sensing here is ultrasonic, not radio. |
| Serial Peripheral Interface (SPI) | A fast clocked bus; the CYD's screen and touch controller each use one. |
| Software Bill of Materials (SBOM) | A list of the software components and exact versions used to build the project. |
| Traceability | Linking every requirement to the check or test that proves it (`docs/REQUIREMENTS.md`). |
| Spline | The toothed servo output shaft. |
| Standard for the Exchange of Product model data (STEP) | A precise CAD exchange format for editing the parts in other CAD tools. |
| Stereolithography file (STL) | A triangle-mesh file that slicers read. |
| Strapping pin | An ESP32 pin whose level at power-up selects a boot mode (GPIO 0, 2, 5, 12, 15) — avoided here. |
| Universal Asynchronous Receiver-Transmitter (UART) | The serial port the firmware prints on (115 200 baud); it reaches the computer through the CYD's USB chip. |
| VERIFY | A CAD dimension that depends on your purchased module and must be measured before printing the full set. |
| Voltage divider | Two resistors in series that output a fixed fraction of their input voltage. |
| Web Serial | The browser interface (Chrome/Edge, and the desktop app) that lets a page read a serial port after you pick it. |
| Windows Subsystem for Linux (WSL) | Runs Ubuntu inside Windows; the publish script supports it. |
