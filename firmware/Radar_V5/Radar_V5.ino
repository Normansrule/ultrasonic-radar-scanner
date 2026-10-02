/*
  Radar_V5.ino — Ultrasonic Radar Scanner, firmware baseline V5.1
  ------------------------------------------------------------------
  EDUCATIONAL ultrasonic (sonar) instrument with a radar-STYLE display.
  It is NOT radio-frequency radar and NOT a safety or obstacle-avoidance
  system. The angle shown is the COMMANDED servo position, not a measured one.

  Board   : "ESP32 Dev Module" (classic ESP32-WROOM-32 DevKit, 30-pin)
  Core    : Espressif Arduino-ESP32 — compiles on 3.x (ledcAttach API) and
            2.x (ledcSetup/ledcAttachPin API). Exact versions that were
            compiled are pinned in sketch.yaml. Compiling is not bench testing:
            see docs/VALIDATION.md for what has and has not been done.
  Libs    : Adafruit GFX, Adafruit ST7735 and ST7789, Adafruit BusIO
  Servo   : driven directly by the ESP32 LEDC peripheral at 50 Hz (no servo library)

  Wiring  : docs/WIRING.md is the source of truth. tests/test_sync.py fails if
            the PIN_ constants below and the WIRING.md tables disagree.

  PROGRAMMING SAFETY: unplug the whole harness from the ESP32 before connecting
  the USB data cable. Never have external 5V/VIN and programming USB at once.
*/

#include <Arduino.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <math.h>
#if __has_include("esp_arduino_version.h")
#include "esp_arduino_version.h"
#endif

// =====================================================================
// 1. USER SETTINGS (change these, re-upload)
// =====================================================================
// Horn installation: set true, upload, fit the hub so its pointer faces the
// 90-degree tick, then set false again and re-upload.
static constexpr bool CENTER_ONLY = false;
// Flip left/right if the sweep on screen moves opposite to the real head.
static constexpr bool REVERSE_SERVO = false;
// Calibration: steps 30 -> 90 -> 150 degrees with 4 s holds and prints the
// pulse width, so you can compare the head against the keeper's tick marks.
static constexpr bool CALIBRATE_SERVO = false;

static constexpr int SWEEP_MIN_DEG = 30;       // commanded, not measured
static constexpr int SWEEP_MAX_DEG = 150;
static constexpr int SWEEP_STEP_DEG = 3;
static constexpr uint32_t SETTLE_MS = 70;      // wait after each step before pinging
static constexpr float MAX_RANGE_CM = 200.0f;  // display range (not a verified sensor range)
static constexpr float MIN_RANGE_CM = 2.0f;
static constexpr float AIR_TEMP_C = 20.0f;     // used for speed of sound; see docs/EQUATIONS.md
static constexpr uint32_t DETECTION_TTL_MS = 9000;  // > one full round trip, so dots persist until revisited

// Servo pulse mapping. Start with the conservative 1000..2000 us. Widen only
// with CALIBRATE_SERVO, and never so far that the servo buzzes against its stops.
static constexpr uint32_t SERVO_US_AT_0 = 1000;
static constexpr uint32_t SERVO_US_AT_180 = 2000;
static constexpr uint32_t SERVO_US_GUARD_MIN = 900;   // hard clamp, whatever the mapping says
static constexpr uint32_t SERVO_US_GUARD_MAX = 2100;

// Display. Some ST7735S revisions need INITR_BLACKTAB / INITR_18GREENTAB,
// a different rotation, or inversion — change here if colours/offsets look wrong.
#define TFT_INIT_TAB INITR_GREENTAB
static constexpr uint8_t TFT_ROTATION = 1;     // 160 x 128 landscape
static constexpr bool TFT_INVERT = false;
// SPI clock for the LCD. 15 MHz sits inside the ST7735S serial write-cycle
// spec (66 ns); the Adafruit library would otherwise use 32 MHz. Raise it only
// if your screen stays clean at the higher speed.
static constexpr uint32_t TFT_SPI_HZ = 15000000;

// =====================================================================
// 2. PINS (must match docs/WIRING.md — checked by tests/test_sync.py)
// =====================================================================
static constexpr int PIN_TRIG = 27;
static constexpr int PIN_ECHO = 26;    // through the 2.2k / 3.3k divider, never direct
static constexpr int PIN_SERVO = 14;
static constexpr int PIN_TFT_MOSI = 23;
static constexpr int PIN_TFT_SCLK = 18;
static constexpr int PIN_TFT_CS = 33;  // not GPIO5 (boot strapping pin)
static constexpr int PIN_TFT_DC = 17;
static constexpr int PIN_TFT_RST = 16;

// =====================================================================
// 3. FIXED CONSTANTS
// =====================================================================
static constexpr uint32_t SERVO_FREQ_HZ = 50;          // 20 ms frame
static constexpr uint8_t SERVO_RES_BITS = 16;
static constexpr uint8_t SERVO_LEDC_CHANNEL = 0;       // used by the core 2.x path only
static constexpr uint32_t SERVO_PERIOD_US = 1000000UL / SERVO_FREQ_HZ;

static constexpr int SCREEN_W = 160;
static constexpr int SCREEN_H = 128;
static constexpr int FAN_CX = 80;       // fan centre (pixels)
static constexpr int FAN_CY = 125;
static constexpr int FAN_R = 88;        // pixels that represent MAX_RANGE_CM
static constexpr int BIN_COUNT = (SWEEP_MAX_DEG - SWEEP_MIN_DEG) / SWEEP_STEP_DEG + 1;
static constexpr int TRAIL_STEPS = 4;

#define RGB565(r, g, b) (uint16_t)((((r) & 0xF8) << 8) | (((g) & 0xFC) << 3) | ((b) >> 3))
static const uint16_t COL_BG = RGB565(0, 0, 0);
static const uint16_t COL_GRID = RGB565(0, 90, 20);
static const uint16_t COL_GRID_TEXT = RGB565(0, 150, 40);
static const uint16_t COL_SWEEP = RGB565(80, 255, 110);
static const uint16_t COL_TEXT = RGB565(170, 255, 180);
static const uint16_t COL_WARN = RGB565(255, 190, 40);

// =====================================================================
// 4. STATE
// =====================================================================
Adafruit_ST7735 tft(PIN_TFT_CS, PIN_TFT_DC, PIN_TFT_RST);
GFXcanvas16 canvas(SCREEN_W, SCREEN_H);   // full-frame buffer: flicker-free redraw

struct Detection {
  float cm;
  uint32_t stampMs;
  bool valid;
};
static Detection detections[BIN_COUNT];

static int sweepDeg = 90;
static int sweepDir = +1;
static int trail[TRAIL_STEPS];
static float lastCm = NAN;
static uint32_t lastPulseUs = 0;
static uint32_t stepStartMs = 0;
static uint32_t stepSumMs = 0;
static uint16_t stepCount = 0;

// =====================================================================
// 5. SERVO (native LEDC, core 3.x and 2.x)
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
// 6. ULTRASONIC
// =====================================================================
static float speedOfSoundCmPerUs() {
  // v ~= 331.3 + 0.606 * T  [m/s]  ->  cm/us = (m/s) / 10000
  return (331.3f + 0.606f * AIR_TEMP_C) / 10000.0f;
}

static uint32_t echoTimeoutUs() {
  // round trip for 110 % of the display range, plus 1 ms for the ping to start
  return (uint32_t)(2.0f * (MAX_RANGE_CM * 1.1f) / speedOfSoundCmPerUs()) + 1000;
}

static float readDistanceCm() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(4);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  const uint32_t t = pulseIn(PIN_ECHO, HIGH, echoTimeoutUs());
  if (t == 0) return NAN;                               // timeout: no echo in range
  const float cm = (float)t * speedOfSoundCmPerUs() / 2.0f;  // d = v*t/2
  if (cm < MIN_RANGE_CM || cm > MAX_RANGE_CM) return NAN;
  return cm;
}

// =====================================================================
// 7. DRAWING (mirrored by scripts/sim_display.py for the README GIF)
// =====================================================================
static inline void polar(float deg, float r, int &x, int &y) {
  const float a = deg * (float)DEG_TO_RAD;
  x = FAN_CX + (int)lroundf(r * cosf(a));
  y = FAN_CY - (int)lroundf(r * sinf(a));
}

static uint16_t scaleGreen(float k) {  // k in 0..1
  k = constrain(k, 0.0f, 1.0f);
  return RGB565((uint8_t)(40 + 160 * k), (uint8_t)(90 + 165 * k), (uint8_t)(40 + 100 * k));
}

static void drawGrid(GFXcanvas16 &g) {
  for (int q = 1; q <= 4; q++) {
    const float r = FAN_R * q / 4.0f;
    int px, py;
    polar(SWEEP_MIN_DEG, r, px, py);
    for (int d = SWEEP_MIN_DEG + 2; d <= SWEEP_MAX_DEG; d += 2) {
      int x, y;
      polar(d, r, x, y);
      g.drawLine(px, py, x, y, COL_GRID);
      px = x;
      py = y;
    }
    // range label just right of the 90-degree line, inside the ring
    g.setTextSize(1);
    g.setTextColor(COL_GRID_TEXT);
    g.setCursor(FAN_CX + 3, FAN_CY - (int)r + 2);
    g.print((int)(MAX_RANGE_CM * q / 4));
  }
  for (int d = SWEEP_MIN_DEG; d <= SWEEP_MAX_DEG; d += 30) {
    int x, y;
    polar(d, FAN_R, x, y);
    g.drawLine(FAN_CX, FAN_CY, x, y, COL_GRID);
  }
}

static void drawHeader(GFXcanvas16 &g, int deg, float cm, const char *mode) {
  g.setTextSize(1);
  g.setTextColor(COL_GRID_TEXT);
  g.setCursor(4, 2);
  g.print("ANGLE");
  g.setCursor(84, 2);
  g.print("DIST");
  g.setCursor(130, 2);
  g.print(mode);
  char buf[8];
  g.setTextSize(2);
  g.setTextColor(COL_TEXT);
  snprintf(buf, sizeof(buf), "%03d", deg);
  g.setCursor(4, 13);
  g.print(buf);
  g.setTextSize(1);
  g.setCursor(42, 20);
  g.print("deg");
  g.setTextSize(2);
  g.setCursor(84, 13);
  if (isnan(cm)) {
    g.print("---");
  } else {
    snprintf(buf, sizeof(buf), "%3d", (int)lroundf(cm));
    g.print(buf);
    g.setTextSize(1);
    g.setCursor(122, 20);
    g.print("cm");
  }
}

static void renderFrame(int deg, float cm, const char *mode) {
  canvas.fillScreen(COL_BG);
  drawGrid(canvas);
  const uint32_t now = millis();
  // detections (fade with age, vanish after DETECTION_TTL_MS)
  for (int i = 0; i < BIN_COUNT; i++) {
    Detection &d = detections[i];
    if (!d.valid) continue;
    const uint32_t age = now - d.stampMs;
    if (age > DETECTION_TTL_MS) {
      d.valid = false;
      continue;
    }
    const float k = 1.0f - (float)age / DETECTION_TTL_MS;
    int x, y;
    polar(SWEEP_MIN_DEG + i * SWEEP_STEP_DEG, FAN_R * d.cm / MAX_RANGE_CM, x, y);
    canvas.fillCircle(x, y, 2, scaleGreen(0.25f + 0.75f * k));
  }
  // fading trail, then the sweep line
  for (int t = TRAIL_STEPS - 1; t >= 0; t--) {
    if (trail[t] < 0) continue;
    int x, y;
    polar(trail[t], FAN_R, x, y);
    canvas.drawLine(FAN_CX, FAN_CY, x, y, scaleGreen(0.15f * (TRAIL_STEPS - t) / TRAIL_STEPS));
  }
  int sx, sy;
  polar(deg, FAN_R, sx, sy);
  canvas.drawLine(FAN_CX, FAN_CY, sx, sy, COL_SWEEP);
  drawHeader(canvas, deg, cm, mode);
  tft.drawRGBBitmap(0, 0, canvas.getBuffer(), SCREEN_W, SCREEN_H);
}

static void splash() {
  canvas.fillScreen(COL_BG);
  canvas.setTextColor(COL_TEXT);
  canvas.setTextSize(2);
  canvas.setCursor(14, 20);
  canvas.print("EDU SONAR");
  canvas.setTextSize(1);
  canvas.setCursor(14, 48);
  canvas.print("Ultrasonic, radar-style");
  canvas.setCursor(14, 60);
  canvas.print("display. Firmware V5.1");
  canvas.setTextColor(COL_WARN);
  canvas.setCursor(14, 84);
  canvas.print("NOT a safety device.");
  canvas.setCursor(14, 96);
  canvas.print("Angle = commanded.");
  tft.drawRGBBitmap(0, 0, canvas.getBuffer(), SCREEN_W, SCREEN_H);
}

// =====================================================================
// 8. SETUP / LOOP
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

  servoBegin();
  servoWriteDeg(90);  // centre at boot

  SPI.begin(PIN_TFT_SCLK, -1, PIN_TFT_MOSI, -1);  // MISO unused
  tft.initR(TFT_INIT_TAB);
  tft.setSPISpeed(TFT_SPI_HZ);
  tft.setRotation(TFT_ROTATION);
  tft.invertDisplay(TFT_INVERT);
  splash();

  for (int i = 0; i < BIN_COUNT; i++) detections[i] = {NAN, 0, false};
  for (int t = 0; t < TRAIL_STEPS; t++) trail[t] = -1;

  Serial.println(F("# Radar V5.1 - educational ultrasonic sonar, radar-style display"));
  Serial.printf("# sweep %d..%d deg, step %d, settle %lu ms, range %.0f cm, echo timeout %lu us\n",
                SWEEP_MIN_DEG, SWEEP_MAX_DEG, SWEEP_STEP_DEG, (unsigned long)SETTLE_MS, MAX_RANGE_CM,
                (unsigned long)echoTimeoutUs());
  Serial.println(F("angle_deg,distance_cm   (-1 = no valid echo)"));
  delay(1500);

  if (!CENTER_ONLY && !CALIBRATE_SERVO) {
    // ease from centre to the start of the sweep instead of jumping
    for (int d = 90; d >= SWEEP_MIN_DEG; d -= SWEEP_STEP_DEG) {
      servoWriteDeg(d);
      delay(25);
    }
    sweepDeg = SWEEP_MIN_DEG;
    sweepDir = +1;
  }
  stepStartMs = millis();
}

static void loopCenterOnly() {
  servoWriteDeg(90);
  renderFrame(90, readDistanceCm(), "CTR");
  Serial.printf("# CENTER_ONLY: holding 90 deg (%lu us). Fit the horn, then set CENTER_ONLY=false.\n",
                (unsigned long)lastPulseUs);
  delay(1000);
}

static void loopCalibrate() {
  static const int targets[] = {30, 90, 150, 90};
  static uint8_t idx = 0;
  const int deg = targets[idx];
  servoWriteDeg(deg);
  const uint32_t until = millis() + 4000;
  while ((int32_t)(millis() - until) < 0) {
    renderFrame(deg, readDistanceCm(), "CAL");
    delay(200);
  }
  Serial.printf("# CAL commanded %3d deg -> %lu us. Compare the head with the keeper tick.\n",
                deg, (unsigned long)lastPulseUs);
  idx = (idx + 1) % (sizeof(targets) / sizeof(targets[0]));
}

void loop() {
  if (CENTER_ONLY) return loopCenterOnly();
  if (CALIBRATE_SERVO) return loopCalibrate();

  servoWriteDeg(sweepDeg);
  delay(SETTLE_MS);
  const float cm = readDistanceCm();
  lastCm = cm;

  const int bin = (sweepDeg - SWEEP_MIN_DEG) / SWEEP_STEP_DEG;
  if (bin >= 0 && bin < BIN_COUNT) {
    detections[bin].valid = !isnan(cm);   // a revisit with no echo clears the old dot
    detections[bin].cm = cm;
    detections[bin].stampMs = millis();
  }
  renderFrame(sweepDeg, cm, "EDU");
  Serial.printf("%d,%.1f\n", sweepDeg, isnan(cm) ? -1.0f : cm);

  pushTrail(sweepDeg);
  // advance and bounce at the ends
  int next = sweepDeg + sweepDir * SWEEP_STEP_DEG;
  if (next > SWEEP_MAX_DEG || next < SWEEP_MIN_DEG) {
    sweepDir = -sweepDir;
    next = sweepDeg + sweepDir * SWEEP_STEP_DEG;
    // report measured loop timing once per sweep (useful for docs/VALIDATION.md)
    if (stepCount) {
      Serial.printf("# measured: %u steps, mean step %.1f ms, one-way sweep %.2f s\n",
                    stepCount, (float)stepSumMs / stepCount, stepSumMs / 1000.0f);
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
