// Run: node --test tests/js
// Checks the shared parser/recorder used by the web app and the desktop app
// against the exact lines the firmware prints.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const RC = require("../../site/assets/radar-core.js");

const INO = fs.readFileSync(path.join(__dirname, "../../firmware/Radar_V5/Radar_V5.ino"), "utf8");

test("readings: valid, no-echo, CRLF", () => {
  assert.deepEqual(RC.parseLine("90,57.3"), { type: "reading", deg: 90, cm: 57.3 });
  assert.deepEqual(RC.parseLine("93,-1.0"), { type: "reading", deg: 93, cm: null });
  assert.deepEqual(RC.parseLine("30,200.0\r"), { type: "reading", deg: 30, cm: 200 });
  assert.equal(RC.parseLine("181,10").type, "unknown");
  assert.equal(RC.parseLine(""), null);
});

test("firmware sweep header is parsed", () => {
  const ev = RC.parseLine("# sweep 30..150 deg, step 3, settle 70 ms, range 200 cm, echo timeout 13812 us");
  assert.deepEqual(ev, { type: "config", min: 30, max: 150, step: 3, settle: 70, range: 200, timeoutUs: 13812 });
});

test("firmware measured line is parsed", () => {
  const ev = RC.parseLine("# measured: 40 steps, mean step 101.2 ms, one-way sweep 4.05 s");
  assert.deepEqual(ev, { type: "measured", steps: 40, stepMs: 101.2, sweepS: 4.05 });
});

test("parser formats match the firmware's printf strings", () => {
  // if someone edits the firmware's serial format, this test points at the parser
  assert.match(INO, /"# sweep %d\.\.%d deg, step %d, settle %lu ms, range %\.0f cm, echo timeout %lu us\\n"/);
  assert.match(INO, /"# measured: %u steps, mean step %\.1f ms, one-way sweep %\.2f s\\n"/);
  assert.match(INO, /Serial\.printf\("%d,%\.1f\\n", sweepDeg, isnan\(cm\) \? -1\.0f : cm\)/);
  assert.match(INO, /Serial\.begin\(115200\)/);
});

test("stream parser handles lines split across chunks", () => {
  const p = RC.createParser();
  const a = p.push("# sweep 30..150 deg, step 3, settle 70 ms, ra");
  const b = p.push("nge 200 cm, echo timeout 13812 us\n90,5");
  const c = p.push("7.3\n93,-1.0\n");
  assert.equal(a.length, 0);
  assert.equal(b[0].type, "config");
  assert.deepEqual(c.map((e) => e.cm), [57.3, null]);
});

test("garbage without newlines is dropped (wrong baud rate)", () => {
  const p = RC.createParser();
  p.push("ÿ".repeat(5000));
  assert.deepEqual(p.push("\n10,20.0\n").map((e) => e.type), ["reading"]);
});

test("recorder CSV round-trips through parseLog", () => {
  const r = RC.createRecorder();
  r.add(RC.parseLine("# sweep 30..150 deg, step 3, settle 70 ms, range 200 cm, echo timeout 13812 us"), 1000);
  r.add(RC.parseLine("90,57.3"), 1000);
  r.add(RC.parseLine("93,-1.0"), 1101);
  const csv = r.toCsv("source: test");
  assert.match(csv, /^host_ms,angle_deg,distance_cm$/m);
  assert.equal(r.count, 2);
  const items = RC.parseLog(csv);
  const readings = items.map((i) => ({ t: i.t, ev: RC.parseLine(i.line) })).filter((x) => x.ev && x.ev.type === "reading");
  assert.deepEqual(readings.map((x) => [x.t, x.ev.deg, x.ev.cm]), [[0, 90, 57.3], [101, 93, null]]);
  const cfg = items.map((i) => RC.parseLine(i.line)).find((e) => e && e.type === "config");
  assert.equal(cfg.range, 200);
});

test("raw serial logs replay without timestamps", () => {
  const items = RC.parseLog("angle_deg,distance_cm   (-1 = no valid echo)\n30,100.0\n33,-1.0\n");
  assert.deepEqual(items.map((i) => i.t), [null, null, null]);
  assert.equal(RC.parseLine(items[1].line).cm, 100);
});

test("stats track valid echoes, nearest and device config", () => {
  const s = RC.createStats();
  for (const [t, l] of [[0, "# sweep 40..140 deg, step 2, settle 80 ms, range 150 cm"], [0, "90,80.0"], [100, "92,-1"], [200, "94,40.5"]])
    s.apply(RC.parseLine(l), t);
  assert.equal(s.state.readings, 3);
  assert.equal(s.state.valid, 2);
  assert.equal(s.state.nearestCm, 40.5);
  assert.equal(s.state.nearestDeg, 94);
  assert.equal(s.state.config.range, 150);
  assert.equal(s.state.config.min, 40);
  assert.ok(Math.abs(s.state.hostStepMs - 100) < 1e-9);
});

test("demo stream is labelled synthetic and bounces at the sweep limits", () => {
  const d = RC.createDemo();
  const first = d.next();
  assert.match(first[0], /DEMO - synthetic/);
  const degs = [];
  for (let i = 0; i < 90; i++) for (const l of d.next()) { const e = RC.parseLine(l); if (e && e.type === "reading") degs.push(e.deg); }
  assert.equal(Math.min(...degs), 30);
  assert.equal(Math.max(...degs), 150);
  assert.ok(degs.every((x) => (x - 30) % 3 === 0));
});
