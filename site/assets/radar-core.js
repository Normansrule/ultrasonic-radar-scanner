/*
  radar-core.js — shared by the web live console, the desktop app and the Node tests.

  Parses the firmware's serial output (firmware/Radar_V6/Radar_V6.ino, 115 200 baud):
    # Radar V6 - educational ultrasonic sonar, radar-style display
    # sweep 30..150 deg, step 3, settle 70 ms, range 200 cm, echo timeout 13812 us
    angle_deg,distance_cm   (-1 = no valid echo)
    90,57.3
    93,-1.0
    # measured: 40 steps, mean step 101.2 ms, one-way sweep 4.05 s
  and draws a high-resolution radar-style view of the readings.

  The angle is the COMMANDED servo position reported by the firmware, not a measured one.
*/
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.RadarCore = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const DEFAULTS = Object.freeze({ min: 30, max: 150, step: 3, settle: 70, range: 200, timeoutUs: 13812 });
  const RE_READING = /^\s*(\d{1,3})\s*,\s*(-?\d+(?:\.\d+)?)\s*$/;
  const RE_SWEEP = /^#\s*sweep\s+(\d+)\.\.(\d+)\s*deg,\s*step\s+(\d+),\s*settle\s+(\d+)\s*ms,\s*range\s+(\d+(?:\.\d+)?)\s*cm(?:,\s*echo timeout\s+(\d+)\s*us)?/i;
  const RE_MEASURED = /^#\s*measured:\s*(\d+)\s*steps,\s*mean step\s+([\d.]+)\s*ms,\s*one-way sweep\s+([\d.]+)\s*s/i;
  const MAX_LINE = 512;

  /** Classify one line of firmware output. */
  function parseLine(raw) {
    const line = String(raw).replace(/\r$/, "").trim();
    if (!line) return null;
    let m = RE_READING.exec(line);
    if (m) {
      const deg = Number(m[1]);
      const v = Number(m[2]);
      if (deg > 180) return { type: "unknown", text: line };
      return { type: "reading", deg, cm: v < 0 ? null : v };
    }
    if ((m = RE_SWEEP.exec(line))) {
      return {
        type: "config", min: +m[1], max: +m[2], step: +m[3], settle: +m[4], range: +m[5],
        timeoutUs: m[6] ? +m[6] : null,
      };
    }
    if ((m = RE_MEASURED.exec(line))) {
      return { type: "measured", steps: +m[1], stepMs: +m[2], sweepS: +m[3] };
    }
    if (line.startsWith("#")) return { type: "comment", text: line.replace(/^#\s?/, "") };
    if (/^angle_deg\s*,\s*distance_cm/i.test(line)) return { type: "header" };
    return { type: "unknown", text: line.slice(0, MAX_LINE) };
  }

  /** Incremental parser for a byte/text stream that may split lines anywhere. */
  function createParser() {
    let buf = "";
    return {
      push(text) {
        buf += text;
        const parts = buf.split(/\n/);
        buf = parts.pop();
        if (buf.length > 4 * MAX_LINE) buf = ""; // garbage without newlines (wrong baud rate)
        const out = [];
        for (const p of parts) {
          const ev = parseLine(p);
          if (ev) out.push(ev);
        }
        return out;
      },
      flush() {
        const ev = parseLine(buf);
        buf = "";
        return ev ? [ev] : [];
      },
    };
  }

  /**
   * Parse a saved session or a raw serial log into timed lines.
   * Accepts the exported format "host_ms,angle_deg,distance_cm" and raw "angle,distance" lines.
   * Returns [{t: ms|null, line: string}] ready to feed back through parseLine().
   */
  function parseLog(text) {
    const out = [];
    for (const raw of String(text).split(/\r?\n/)) {
      const line = raw.trim();
      if (!line) continue;
      const m = /^(\d+(?:\.\d+)?)\s*,\s*(\d{1,3})\s*,\s*(-?\d+(?:\.\d+)?)$/.exec(line);
      if (m) out.push({ t: Number(m[1]), line: `${m[2]},${m[3]}` });
      else if (!/^host_ms\s*,/i.test(line)) out.push({ t: null, line: line.replace(/^#\s*host_ms=\d+\s*/, "") });
    }
    return out;
  }

  /** Session recorder → CSV text (comments keep the firmware's own header lines). */
  function createRecorder() {
    const rows = [];
    let t0 = null;
    return {
      add(ev, nowMs) {
        if (t0 === null) t0 = nowMs;
        rows.push({ t: Math.round(nowMs - t0), ev });
      },
      get count() { return rows.filter((r) => r.ev.type === "reading").length; },
      toCsv(meta) {
        const lines = [
          "# ultrasonic-radar-scanner session log",
          `# saved ${new Date().toISOString()}${meta ? " - " + meta : ""}`,
          "# angle = COMMANDED servo position; distance -1 = no valid echo",
          "host_ms,angle_deg,distance_cm",
        ];
        for (const { t, ev } of rows) {
          if (ev.type === "reading") lines.push(`${t},${ev.deg},${ev.cm === null ? -1 : ev.cm.toFixed(1)}`);
          else if (ev.type === "config")
            lines.push(`# sweep ${ev.min}..${ev.max} deg, step ${ev.step}, settle ${ev.settle} ms, range ${ev.range} cm` +
              (ev.timeoutUs ? `, echo timeout ${ev.timeoutUs} us` : ""));
          else if (ev.type === "measured")
            lines.push(`# measured: ${ev.steps} steps, mean step ${ev.stepMs} ms, one-way sweep ${ev.sweepS} s`);
          else if (ev.type === "comment") lines.push(`# ${ev.text}`);
        }
        return lines.join("\n") + "\n";
      },
    };
  }

  /** Running statistics for the side panel. */
  function createStats() {
    const s = {
      readings: 0, valid: 0, lastDeg: null, lastCm: null, nearestCm: null, nearestDeg: null,
      measuredStepMs: null, measuredSweepS: null, hostStepMs: null, lastHostMs: null, config: { ...DEFAULTS },
      configFromDevice: false, unknownLines: 0,
    };
    let ema = null;
    return {
      state: s,
      apply(ev, nowMs) {
        if (ev.type === "reading") {
          s.readings++;
          s.lastDeg = ev.deg;
          s.lastCm = ev.cm;
          if (ev.cm !== null) {
            s.valid++;
            if (s.nearestCm === null || ev.cm < s.nearestCm) { s.nearestCm = ev.cm; s.nearestDeg = ev.deg; }
          }
          if (s.lastHostMs !== null) {
            const dt = nowMs - s.lastHostMs;
            if (dt > 0 && dt < 2000) ema = ema === null ? dt : ema * 0.9 + dt * 0.1;
            s.hostStepMs = ema;
          }
          s.lastHostMs = nowMs;
        } else if (ev.type === "config") {
          s.config = { ...s.config, ...Object.fromEntries(Object.entries(ev).filter(([k, v]) => k !== "type" && v !== null)) };
          s.configFromDevice = true;
        } else if (ev.type === "measured") {
          s.measuredStepMs = ev.stepMs;
          s.measuredSweepS = ev.sweepS;
        } else if (ev.type === "unknown") {
          s.unknownLines++;
        }
      },
      resetNearest() { s.nearestCm = null; s.nearestDeg = null; },
    };
  }

  /** High-resolution radar-style renderer. */
  function createView(canvas, opts) {
    const o = Object.assign({ ttlMs: 10000, trail: 6 }, opts || {});
    const ctx = canvas.getContext("2d");
    const dets = new Map(); // deg -> {cm, t}
    let cfg = { ...DEFAULTS };
    let sweepDeg = null;
    const trail = [];
    let W = 0, H = 0, dpr = 1;

    function resize() {
      dpr = (typeof window !== "undefined" && window.devicePixelRatio) || 1;
      const r = canvas.getBoundingClientRect();
      W = Math.max(320, Math.round(r.width));
      H = Math.round(W * 0.62);
      canvas.style.height = H + "px";
      canvas.width = Math.round(W * dpr);
      canvas.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function geom() {
      const cx = W / 2, cy = H - 18;
      const a0 = (cfg.min * Math.PI) / 180, a1 = (cfg.max * Math.PI) / 180;
      const halfW = Math.max(Math.abs(Math.cos(a0)), Math.abs(Math.cos(a1)));
      const R = Math.min(cy - 34, (W / 2 - 44) / Math.max(halfW, 0.5));
      return { cx, cy, R };
    }

    const P = (g, deg, r) => [g.cx + r * Math.cos((deg * Math.PI) / 180), g.cy - r * Math.sin((deg * Math.PI) / 180)];

    function draw(nowMs) {
      const g = geom();
      ctx.fillStyle = "#020503";
      ctx.fillRect(0, 0, W, H);
      // rings + labels
      ctx.lineWidth = 1;
      ctx.font = "11px ui-monospace, Menlo, Consolas, monospace";
      for (let q = 1; q <= 4; q++) {
        const r = (g.R * q) / 4;
        ctx.strokeStyle = q === 4 ? "rgba(40,190,90,.55)" : "rgba(40,170,80,.32)";
        ctx.beginPath();
        ctx.arc(g.cx, g.cy, r, -(cfg.max * Math.PI) / 180, -(cfg.min * Math.PI) / 180);
        ctx.stroke();
        ctx.fillStyle = "rgba(90,220,130,.75)";
        ctx.fillText(`${Math.round((cfg.range * q) / 4)} cm`, g.cx + 4, g.cy - r + 13);
      }
      // spokes every 30 deg + labels
      for (let d = Math.ceil(cfg.min / 30) * 30; d <= cfg.max; d += 30) {
        const [x, y] = P(g, d, g.R);
        ctx.strokeStyle = "rgba(40,170,80,.32)";
        ctx.beginPath(); ctx.moveTo(g.cx, g.cy); ctx.lineTo(x, y); ctx.stroke();
        const [lx, ly] = P(g, d, g.R + 16);
        ctx.fillStyle = "rgba(90,220,130,.75)";
        ctx.textAlign = "center";
        ctx.fillText(`${d}°`, lx, ly + 4);
        ctx.textAlign = "start";
      }
      // detections
      for (const [deg, v] of dets) {
        const age = nowMs - v.t;
        if (age > o.ttlMs) { dets.delete(deg); continue; }
        const k = 1 - age / o.ttlMs;
        const r = Math.min(1, v.cm / cfg.range) * g.R;
        const [x, y] = P(g, deg, r);
        ctx.fillStyle = `rgba(${90 + 140 * k | 0},255,${120 + 60 * k | 0},${0.25 + 0.75 * k})`;
        ctx.beginPath(); ctx.arc(x, y, 2.5 + 2.5 * k, 0, Math.PI * 2); ctx.fill();
      }
      // trail + sweep
      trail.forEach((d, i) => {
        const [x, y] = P(g, d, g.R);
        ctx.strokeStyle = `rgba(80,255,120,${0.28 * (1 - i / trail.length)})`;
        ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(g.cx, g.cy); ctx.lineTo(x, y); ctx.stroke();
      });
      if (sweepDeg !== null) {
        const [x, y] = P(g, sweepDeg, g.R);
        ctx.strokeStyle = "rgb(120,255,150)";
        ctx.lineWidth = 2.5;
        ctx.beginPath(); ctx.moveTo(g.cx, g.cy); ctx.lineTo(x, y); ctx.stroke();
      }
      ctx.lineWidth = 1;
    }

    return {
      resize,
      draw,
      setConfig(c) { cfg = { ...cfg, ...c }; },
      get config() { return { ...cfg }; },
      setTtl(ms) { o.ttlMs = ms; },
      clear() { dets.clear(); trail.length = 0; sweepDeg = null; },
      add(ev, nowMs) {
        if (ev.type === "config") { cfg = { ...cfg, ...Object.fromEntries(Object.entries(ev).filter(([k, v]) => k !== "type" && v !== null)) }; return; }
        if (ev.type !== "reading") return;
        if (sweepDeg !== null) { trail.unshift(sweepDeg); if (trail.length > o.trail) trail.pop(); }
        sweepDeg = ev.deg;
        if (ev.cm === null) dets.delete(ev.deg);
        else dets.set(ev.deg, { cm: ev.cm, t: nowMs });
      },
      get detectionCount() { return dets.size; },
    };
  }

  /** Synthetic stream for the demo button (clearly labelled in the UI). */
  function createDemo(config) {
    const c = { ...DEFAULTS, ...(config || {}) };
    let deg = c.min, dir = 1, k = 0, sentHeader = false;
    const targets = [
      { a0: 36, a1: 66, d: (a) => 150 + 0.25 * (a - 51) },
      { a0: 93, a1: 102, d: () => 62 },
      { a0: 123, a1: 138, d: () => 115 },
    ];
    return {
      stepMs: 101,
      next() {
        if (!sentHeader) {
          sentHeader = true;
          return [
            "# DEMO - synthetic targets, not a real scanner",
            `# sweep ${c.min}..${c.max} deg, step ${c.step}, settle ${c.settle} ms, range ${c.range} cm, echo timeout ${c.timeoutUs} us`,
            "angle_deg,distance_cm   (-1 = no valid echo)",
          ];
        }
        let cm = -1;
        for (const t of targets) if (deg >= t.a0 && deg <= t.a1) cm = t.d(deg) + (((k * 7919 + deg * 104729) % 31) - 15) / 10;
        const line = `${deg},${cm < 0 ? "-1.0" : cm.toFixed(1)}`;
        k++;
        let n = deg + dir * c.step;
        const lines = [line];
        if (n > c.max || n < c.min) {
          dir = -dir; n = deg + dir * c.step;
          lines.push(`# measured: ${(c.max - c.min) / c.step} steps, mean step 101.0 ms, one-way sweep 4.04 s`);
        }
        deg = n;
        return lines;
      },
    };
  }

  return { DEFAULTS, parseLine, createParser, parseLog, createRecorder, createStats, createView, createDemo };
});
