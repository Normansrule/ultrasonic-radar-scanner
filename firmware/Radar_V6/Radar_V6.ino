/*
  Radar_V6.ino — Ultrasonic Radar Scanner, firmware V6 ("Mini")
  -------------------------------------------------------------------------
  EDUCATIONAL ultrasonic (sonar) instrument with a radar-STYLE display.
  NOT radio-frequency radar and NOT a safety or obstacle-avoidance system.
  The angle shown is the COMMANDED servo position, not a measured one.

  Hardware (3 modules, 7 wires, one USB cable):
    * ESP32-2432S028R "Cheap Yellow Display" (CYD): ESP32 + 2.8" 320x240 touch LCD
    * RCWL-1601 / HC-SR04P ultrasonic sensor, powered from 3.3 V (no level shifting)
    * SG90-size positional micro servo, powered from the CYD's P1 VIN (USB 5 V)
  Wiring: docs/WIRING.md is the source of truth; tests/test_sync.py checks the
  PIN_ constants below against it.

  Board   : "ESP32 Dev Module". Libraries: Adafruit GFX, Adafruit ILI9341,
            Adafruit ST7735 and ST7789, Adafruit BusIO, XPT2046_Touchscreen.
            Exact versions are pinned in sketch.yaml. Compiles on Arduino-ESP32
            3.x and 2.x. Compiling is not bench testing — see docs/VALIDATION.md.

  Touch   : tap  −  (bottom left) / + (bottom right) to change the range,
            tap the radar to pause / resume.
  Serial  : 115200 baud, one "angle_deg,distance_cm" line per reading
            (-1 = no echo). The web app's live console reads this over the same
            USB cable that powers the scanner.
*/

#include <Arduino.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include <Adafruit_ST7789.h>
#include <XPT2046_Touchscreen.h>
#include <math.h>
#if __has_include("esp_arduino_version.h")
#include "esp_arduino_version.h"
#endif

// =====================================================================
// 1. USER SETTINGS
// =====================================================================
static constexpr bool CENTER_ONLY = false;      // true: hold 90° for fitting the head, then set back to false
static constexpr bool REVERSE_SERVO = false;    // flip if the screen sweeps opposite to the real head
static constexpr bool CALIBRATE_SERVO = false;  // steps 30 -> 90 -> 150 with 4 s holds to compare with the roof ticks

static constexpr int SWEEP_MIN_DEG = 30;        // commanded, not measured
static constexpr int SWEEP_MAX_DEG = 150;
static constexpr int SWEEP_STEP_DEG = 3;
static constexpr uint32_t SETTLE_MS = 70;
static constexpr float MAX_RANGE_CM = 200.0f;   // start-up display range (touch +/- to change)
static constexpr float MIN_RANGE_CM = 2.0f;
static constexpr float AIR_TEMP_C = 20.0f;
static constexpr uint32_t DETECTION_TTL_MS = 10000;
static constexpr float NEAR_CM = 30.0f;         // RGB LED turns red below this

static constexpr uint32_t SERVO_US_AT_0 = 1000;
static constexpr uint32_t SERVO_US_AT_180 = 2000;
static constexpr uint32_t SERVO_US_GUARD_MIN = 900;
static constexpr uint32_t SERVO_US_GUARD_MAX = 2100;

// Display: CYD boards ship with an ILI9341 panel (one USB port) or an ST7789
// panel ("CYD2USB", micro-USB + USB-C). PANEL_AUTO reads the panel ID first.
enum PanelType { PANEL_AUTO, PANEL_ILI9341, PANEL_ST7789 };
static constexpr PanelType PANEL = PANEL_AUTO;
static constexpr int INVERT_OVERRIDE = -1;      // -1 = panel default, 0 = off, 1 = on
static constexpr bool SWAP_RED_BLUE = false;    // set true if reds look blue (some CYD2USB boards)
static constexpr uint32_t TFT_SPI_HZ = 40000000; // common CYD practice; lower to 27 MHz if the picture glitches

// =====================================================================
// 2. PINS (must match docs/WIRING.md — checked by tests/test_sync.py)
// =====================================================================
static constexpr int PIN_TRIG = 27;   // CN1
static constexpr int PIN_ECHO = 35;   // P3, input-only pin; sensor runs at 3.3 V so no divider is needed
static constexpr int PIN_SERVO = 22;  // CN1 (also on P3 - leave that one unconnected)
// on-board, fixed by the CYD layout
static constexpr int PIN_TFT_SCK = 14;
static constexpr int PIN_TFT_MISO = 12;
static constexpr int PIN_TFT_MOSI = 13;
static constexpr int PIN_TFT_CS = 15;
static constexpr int PIN_TFT_DC = 2;
static constexpr int PIN_TFT_BL = 21;
static constexpr int PIN_TOUCH_CLK = 25;
static constexpr int PIN_TOUCH_MISO = 39;
static constexpr int PIN_TOUCH_MOSI = 32;
static constexpr int PIN_TOUCH_CS = 33;
static constexpr int PIN_TOUCH_IRQ = 36;
static constexpr int PIN_LED_R = 4;    // RGB LED, active low
static constexpr int PIN_LED_G = 16;
static constexpr int PIN_LED_B = 17;

// =====================================================================
// 3. FIXED CONSTANTS
// =====================================================================
static constexpr uint32_t SERVO_FREQ_HZ = 50;
static constexpr uint8_t SERVO_RES_BITS = 16;
static constexpr uint8_t SERVO_LEDC_CHANNEL = 0;
static constexpr uint32_t SERVO_PERIOD_US = 1000000UL / SERVO_FREQ_HZ;

static constexpr int SCREEN_W = 320;
static constexpr int SCREEN_H = 240;
static constexpr int BAND_H = 60;                 // render in 4 bands of 320x60 (38 KB each)
static constexpr int FAN_CX = 160;
static constexpr int FAN_CY = 236;
static constexpr int FAN_R = 176;
static constexpr int BIN_COUNT = (SWEEP_MAX_DEG - SWEEP_MIN_DEG) / SWEEP_STEP_DEG + 1;
static constexpr int TRAIL_STEPS = 6;
static const float RANGES_CM[] = {50.0f, 100.0f, 200.0f, 300.0f, 400.0f};
static constexpr int RANGE_COUNT = sizeof(RANGES_CM) / sizeof(RANGES_CM[0]);

// =====================================================================
// 4. STATE
// =====================================================================
SPIClass hspi(HSPI);
SPIClass touchSpi(VSPI);
XPT2046_Touchscreen touch(PIN_TOUCH_CS, PIN_TOUCH_IRQ);
Adafruit_SPITFT *tft = nullptr;
const char *panelName = "?";
GFXcanvas16 band(SCREEN_W, BAND_H);

struct Detection { float cm; uint32_t stampMs; bool valid; };
static Detection detections[BIN_COUNT];
static int sweepDeg = 90;
static int sweepDir = +1;
static int trail[TRAIL_STEPS];
static float rangeCm = MAX_RANGE_CM;
static bool paused = false;
static uint32_t lastPulseUs = 0;
static uint32_t stepStartMs = 0, stepSumMs = 0;
static uint16_t stepCount = 0;
static float nearestThisPass = NAN;
static uint32_t lastTouchMs = 0;

// =====================================================================
// 5. COLOURS
// =====================================================================
static uint16_t rgb(uint8_t r, uint8_t g, uint8_t b) {
  if (SWAP_RED_BLUE) { uint8_t t = r; r = b; b = t; }
  return (uint16_t)(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3));
}
static uint16_t C_BG, C_GRID, C_GRID_TXT, C_SWEEP, C_TEXT, C_DIM, C_WARN, C_BTN;
static void initColours() {
  C_BG = rgb(2, 10, 6);
  C_GRID = rgb(0, 80, 36);
  C_GRID_TXT = rgb(40, 160, 90);
  C_SWEEP = rgb(120, 255, 160);
  C_TEXT = rgb(200, 255, 215);
  C_DIM = rgb(90, 150, 115);
  C_WARN = rgb(255, 190, 60);
  C_BTN = rgb(20, 60, 36);
}
static uint16_t glow(float k) {  // 0..1 -> dark..bright green
  k = constrain(k, 0.0f, 1.0f);
  return rgb((uint8_t)(20 + 150 * k), (uint8_t)(60 + 195 * k), (uint8_t)(30 + 120 * k));
}

// =====================================================================
// 6. SERVO (native LEDC, core 3.x and 2.x)
// =====================================================================
static uint32_t pulseToDuty(uint32_t us) {
  const uint32_t maxDuty = (1UL << SERVO_RES_BITS) - 1;
  return (uint32_t)(((uint64_t)us * maxDuty) / SERVO_PERIOD_US);
}
static void servoBegin() {
#if defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
  ledcAttach(PIN_SERVO, SERVO_FREQ_HZ, SERVO_RES_BITS);
#else
  ledcSetup(SERVO_LEDC_CHANNEL, SERVO_FREQ_HZ, SERVO_RES_BITS);
  ledcAttachPin(PIN_SERVO, SERVO_LEDC_CHANNEL);
#endif
}
static void servoWriteUs(uint32_t us) {
  us = constrain(us, SERVO_US_GUARD_MIN, SERVO_US_GUARD_MAX);
  lastPulseUs = us;
#if defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
  ledcWrite(PIN_SERVO, pulseToDuty(us));
#else
  ledcWrite(SERVO_LEDC_CHANNEL, pulseToDuty(us));
#endif
}
static uint32_t angleToUs(int deg) {
  deg = constrain(deg, 0, 180);
  if (REVERSE_SERVO) deg = 180 - deg;
  return SERVO_US_AT_0 + (uint32_t)((int32_t)(SERVO_US_AT_180 - SERVO_US_AT_0) * deg / 180);
}
static void servoWriteDeg(int deg) { servoWriteUs(angleToUs(deg)); }

// =====================================================================
// 7. ULTRASONIC
// =====================================================================
static float speedOfSoundCmPerUs() { return (331.3f + 0.606f * AIR_TEMP_C) / 10000.0f; }
static uint32_t echoTimeoutUs() {
  return (uint32_t)(2.0f * (rangeCm * 1.1f) / speedOfSoundCmPerUs()) + 1000;
}
static float readDistanceCm() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(4);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  const uint32_t t = pulseIn(PIN_ECHO, HIGH, echoTimeoutUs());
  if (t == 0) return NAN;
  const float cm = (float)t * speedOfSoundCmPerUs() / 2.0f;  // d = v*t/2
  if (cm < MIN_RANGE_CM || cm > rangeCm) return NAN;
  return cm;
}

// =====================================================================
// 8. DISPLAY (mirrored by scripts/sim_display.py for the README GIF)
// =====================================================================
static bool initDisplay() {
  hspi.begin(PIN_TFT_SCK, PIN_TFT_MISO, PIN_TFT_MOSI, PIN_TFT_CS);
  PanelType p = PANEL;
  if (p != PANEL_ST7789) {
    Adafruit_ILI9341 *ili = new Adafruit_ILI9341(&hspi, PIN_TFT_DC, PIN_TFT_CS, -1);
    ili->begin(TFT_SPI_HZ);
    if (p == PANEL_AUTO) {
      const uint8_t id1 = ili->readcommand8(0xD3, 2), id2 = ili->readcommand8(0xD3, 3);
      Serial.printf("# panel id 0xD3: %02X %02X\n", id1, id2);
      p = (id1 == 0x93 && id2 == 0x41) ? PANEL_ILI9341 : PANEL_ST7789;
    }
    if (p == PANEL_ILI9341) { tft = ili; panelName = "ILI9341"; }
    else delete ili;
  }
  if (p == PANEL_ST7789) {
    Adafruit_ST7789 *st = new Adafruit_ST7789(&hspi, PIN_TFT_CS, PIN_TFT_DC, -1);
    st->init(240, 320);
    st->setSPISpeed(TFT_SPI_HZ);
    st->invertDisplay(false);  // CYD2USB panels need inversion off
    tft = st;
    panelName = "ST7789";
  }
  tft->setRotation(1);  // 320 x 240 landscape
  if (INVERT_OVERRIDE >= 0) tft->invertDisplay(INVERT_OVERRIDE == 1);
  pinMode(PIN_TFT_BL, OUTPUT);
  digitalWrite(PIN_TFT_BL, HIGH);
  return band.getBuffer() != nullptr;
}

// drawing helpers: every coordinate is shifted by -y0 so one scene can be painted band by band
static int Y0 = 0;
static inline void P(float deg, float r, int &x, int &y) {
  const float a = deg * (float)DEG_TO_RAD;
  x = FAN_CX + (int)lroundf(r * cosf(a));
  y = FAN_CY - (int)lroundf(r * sinf(a)) - Y0;
}

static void drawButton(int x, int y, const char *label) {
  band.fillRoundRect(x, y - Y0, 56, 36, 8, C_BTN);
  band.drawRoundRect(x, y - Y0, 56, 36, 8, C_GRID);
  band.setTextSize(3);
  band.setTextColor(C_TEXT);
  band.setCursor(x + 19, y + 7 - Y0);
  band.print(label);
}

static void drawScene(int deg, float cm, uint32_t now) {
  band.fillScreen(C_BG);
  // range rings + labels
  for (int q = 1; q <= 4; q++) {
    const float r = FAN_R * q / 4.0f;
    int px, py;
    P(SWEEP_MIN_DEG, r, px, py);
    for (int d = SWEEP_MIN_DEG + 2; d <= SWEEP_MAX_DEG; d += 2) {
      int x, y;
      P(d, r, x, y);
      band.drawLine(px, py, x, y, C_GRID);
      px = x; py = y;
    }
    band.setTextSize(1);
    band.setTextColor(C_GRID_TXT);
    band.setCursor(FAN_CX + 4, FAN_CY - (int)r + 3 - Y0);
    band.print((int)(rangeCm * q / 4));
  }
  for (int d = SWEEP_MIN_DEG; d <= SWEEP_MAX_DEG; d += 30) {
    int x, y;
    P(d, FAN_R, x, y);
    band.drawLine(FAN_CX, FAN_CY - Y0, x, y, C_GRID);
  }
  // fading sweep wedge (trail), newest brightest
  int ox, oy;
  P(deg, FAN_R, ox, oy);
  for (int t = 0; t < TRAIL_STEPS; t++) {
    if (trail[t] < 0) break;
    int x1, y1, x2, y2;
    P(t == 0 ? deg : trail[t - 1], FAN_R, x1, y1);
    P(trail[t], FAN_R, x2, y2);
    band.fillTriangle(FAN_CX, FAN_CY - Y0, x1, y1, x2, y2, glow(0.22f * (TRAIL_STEPS - t) / TRAIL_STEPS));
  }
  // detections: soft halo + bright core, fading with age
  for (int i = 0; i < BIN_COUNT; i++) {
    Detection &d = detections[i];
    if (!d.valid) continue;
    const uint32_t age = now - d.stampMs;
    if (age > DETECTION_TTL_MS) continue;
    const float k = 1.0f - (float)age / DETECTION_TTL_MS;
    int x, y;
    P(SWEEP_MIN_DEG + i * SWEEP_STEP_DEG, FAN_R * d.cm / rangeCm, x, y);
    band.fillCircle(x, y, 5, glow(0.25f * k));
    band.fillCircle(x, y, 3, glow(0.35f + 0.65f * k));
  }
  band.drawLine(FAN_CX, FAN_CY - Y0, ox, oy, C_SWEEP);
  band.fillCircle(FAN_CX, FAN_CY - Y0, 4, C_SWEEP);
  // header
  band.setTextSize(1);
  band.setTextColor(C_DIM);
  band.setCursor(8, 6 - Y0);   band.print("ANGLE (commanded)");
  band.setCursor(128, 6 - Y0); band.print("DISTANCE");
  band.setCursor(236, 6 - Y0); band.print("RANGE");
  band.setTextColor(paused ? C_WARN : C_DIM);
  band.setCursor(282, 6 - Y0); band.print(paused ? "PAUSE" : "LIVE");
  char buf[12];
  band.setTextSize(3);
  band.setTextColor(C_TEXT);
  snprintf(buf, sizeof(buf), "%3d", deg);
  band.setCursor(8, 20 - Y0);  band.print(buf);
  band.setTextSize(2); band.setCursor(64, 26 - Y0); band.print("o");
  band.setTextSize(3);
  band.setCursor(128, 20 - Y0);
  if (isnan(cm)) band.print("---");
  else { snprintf(buf, sizeof(buf), "%3d", (int)lroundf(cm)); band.print(buf); band.setTextSize(2); band.setCursor(184, 26 - Y0); band.print("cm"); }
  band.setTextSize(2);
  band.setTextColor(C_TEXT);
  snprintf(buf, sizeof(buf), "%d", (int)rangeCm);
  band.setCursor(236, 24 - Y0); band.print(buf);
  band.setTextSize(1); band.print(" cm");
  // touch buttons in the corners the fan does not use
  drawButton(6, 198, "-");
  drawButton(258, 198, "+");
}

static void renderFrame(int deg, float cm) {
  const uint32_t now = millis();
  for (int y0 = 0; y0 < SCREEN_H; y0 += BAND_H) {
    Y0 = y0;
    drawScene(deg, cm, now);
    tft->drawRGBBitmap(0, y0, band.getBuffer(), SCREEN_W, BAND_H);
  }
  Y0 = 0;
}

static void splash() {
  tft->fillScreen(C_BG);
  tft->setTextColor(C_TEXT);
  tft->setTextSize(4);
  tft->setCursor(48, 40);
  tft->print("EDU SONAR");
  tft->setTextSize(2);
  tft->setCursor(48, 96);
  tft->print("Ultrasonic radar-style");
  tft->setCursor(48, 118);
  tft->print("scanner - firmware V6");
  tft->setTextColor(C_WARN);
  tft->setCursor(48, 160);
  tft->print("NOT a safety device.");
  tft->setCursor(48, 182);
  tft->print("Angle = commanded.");
}

// =====================================================================
// 9. LED, TOUCH, SERIAL
// =====================================================================
static void led(bool r, bool g, bool b) {  // active low
  digitalWrite(PIN_LED_R, r ? LOW : HIGH);
  digitalWrite(PIN_LED_G, g ? LOW : HIGH);
  digitalWrite(PIN_LED_B, b ? LOW : HIGH);
}
static void printConfig() {
  Serial.printf("# sweep %d..%d deg, step %d, settle %lu ms, range %.0f cm, echo timeout %lu us\n",
                SWEEP_MIN_DEG, SWEEP_MAX_DEG, SWEEP_STEP_DEG, (unsigned long)SETTLE_MS, rangeCm,
                (unsigned long)echoTimeoutUs());
}
static int rangeIndex() {
  for (int i = 0; i < RANGE_COUNT; i++) if (RANGES_CM[i] >= rangeCm - 0.5f) return i;
  return RANGE_COUNT - 1;
}
static void handleTouch() {
  if (!touch.touched() || millis() - lastTouchMs < 300) return;
  lastTouchMs = millis();
  const TS_Point p = touch.getPoint();
  // coarse mapping is enough for three zones (typical CYD raw range 200..3800)
  const int x = map(p.x, 200, 3800, 0, SCREEN_W);
  const int y = map(p.y, 240, 3800, 0, SCREEN_H);
  if (y > 180 && x < 80) {
    rangeCm = RANGES_CM[max(0, rangeIndex() - 1)];
  } else if (y > 180 && x > 240) {
    rangeCm = RANGES_CM[min(RANGE_COUNT - 1, rangeIndex() + 1)];
  } else {
    paused = !paused;
    Serial.println(paused ? F("# paused") : F("# resumed"));
    return;
  }
  for (int i = 0; i < BIN_COUNT; i++) detections[i].valid = false;
  printConfig();
}

// =====================================================================
// 10. SETUP / LOOP
// =====================================================================
static void pushTrail(int deg) {
  for (int t = TRAIL_STEPS - 1; t > 0; t--) trail[t] = trail[t - 1];
  trail[0] = deg;
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_TRIG, OUTPUT);
  digitalWrite(PIN_TRIG, LOW);
  pinMode(PIN_ECHO, INPUT);
  pinMode(PIN_LED_R, OUTPUT); pinMode(PIN_LED_G, OUTPUT); pinMode(PIN_LED_B, OUTPUT);
  led(false, false, true);

  servoBegin();
  servoWriteDeg(90);  // centre at boot

  initColours();
  const bool bufferOk = initDisplay();
  splash();
  touchSpi.begin(PIN_TOUCH_CLK, PIN_TOUCH_MISO, PIN_TOUCH_MOSI, PIN_TOUCH_CS);
  touch.begin(touchSpi);
  touch.setRotation(1);

  for (int i = 0; i < BIN_COUNT; i++) detections[i] = {NAN, 0, false};
  for (int t = 0; t < TRAIL_STEPS; t++) trail[t] = -1;

  Serial.println(F("# Radar V6 - educational ultrasonic sonar, radar-style display"));
  Serial.printf("# board ESP32-2432S028 (CYD), panel %s, band buffer %s\n", panelName, bufferOk ? "ok" : "FAILED");
  printConfig();
  Serial.println(F("angle_deg,distance_cm   (-1 = no valid echo)"));
  delay(1500);

  if (!CENTER_ONLY && !CALIBRATE_SERVO) {
    for (int d = 90; d >= SWEEP_MIN_DEG; d -= SWEEP_STEP_DEG) { servoWriteDeg(d); delay(25); }
    sweepDeg = SWEEP_MIN_DEG;
    sweepDir = +1;
  }
  led(false, true, false);
  stepStartMs = millis();
}

static void loopCenterOnly() {
  servoWriteDeg(90);
  renderFrame(90, readDistanceCm());
  Serial.printf("# CENTER_ONLY: holding 90 deg (%lu us). Fit the head, then set CENTER_ONLY=false.\n",
                (unsigned long)lastPulseUs);
  delay(1000);
}

static void loopCalibrate() {
  static const int targets[] = {30, 90, 150, 90};
  static uint8_t idx = 0;
  const int deg = targets[idx];
  servoWriteDeg(deg);
  const uint32_t until = millis() + 4000;
  while ((int32_t)(millis() - until) < 0) { renderFrame(deg, readDistanceCm()); delay(200); }
  Serial.printf("# CAL commanded %3d deg -> %lu us. Compare the head with the roof tick.\n", deg,
                (unsigned long)lastPulseUs);
  idx = (idx + 1) % (sizeof(targets) / sizeof(targets[0]));
}

void loop() {
  handleTouch();
  if (CENTER_ONLY) return loopCenterOnly();
  if (CALIBRATE_SERVO) return loopCalibrate();
  if (paused) {
    led(false, false, true);
    renderFrame(sweepDeg, NAN);
    delay(100);
    stepStartMs = millis();
    return;
  }

  servoWriteDeg(sweepDeg);
  delay(SETTLE_MS);
  const float cm = readDistanceCm();
  const int bin = (sweepDeg - SWEEP_MIN_DEG) / SWEEP_STEP_DEG;
  if (bin >= 0 && bin < BIN_COUNT) {
    detections[bin].valid = !isnan(cm);
    detections[bin].cm = cm;
    detections[bin].stampMs = millis();
  }
  if (!isnan(cm) && (isnan(nearestThisPass) || cm < nearestThisPass)) nearestThisPass = cm;
  renderFrame(sweepDeg, cm);
  Serial.printf("%d,%.1f\n", sweepDeg, isnan(cm) ? -1.0f : cm);
  pushTrail(sweepDeg);

  int next = sweepDeg + sweepDir * SWEEP_STEP_DEG;
  if (next > SWEEP_MAX_DEG || next < SWEEP_MIN_DEG) {
    sweepDir = -sweepDir;
    next = sweepDeg + sweepDir * SWEEP_STEP_DEG;
    const bool near = !isnan(nearestThisPass) && nearestThisPass < NEAR_CM;
    led(near, !near, false);  // proximity colour for the pass that just ended
    nearestThisPass = NAN;
    if (stepCount) {
      Serial.printf("# measured: %u steps, mean step %.1f ms, one-way sweep %.2f s\n", stepCount,
                    (float)stepSumMs / stepCount, stepSumMs / 1000.0f);
    }
    stepSumMs = 0;
    stepCount = 0;
  }
  const uint32_t now = millis();
  stepSumMs += now - stepStartMs;
  stepCount++;
  stepStartMs = now;
  sweepDeg = next;
}
