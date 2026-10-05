// Interactive pieces of the landing page. Plain JavaScript, no build step.
// 1) sweep simulator: a JavaScript approximation of renderFrame() in the firmware
// 2) wiring explorer: highlights nets in the generated wiring SVG
// 3) calculators for the four documented equations
(function () {
  "use strict";

  // ------------------------------------------------------------------ maths (mirrors tests/radar_math.py)
  const vSound = (T) => 331.3 + 0.606 * T;                 // m/s
  const cmPerUs = (T) => vSound(T) / 10000;
  const echoTimeoutUs = (maxCm, T) => Math.trunc((2 * maxCm * 1.1) / cmPerUs(T)) + 1000;
  const FRAME_PUSH_MS = (320 * 240 * 16) / 40e6 * 1000;    // 40 MHz SPI full frame (CYD)
  const DRAW_MS = 8;                                       // estimate
  const pulseUs = (deg, us0 = 1000, us180 = 2000) => {
    deg = Math.max(0, Math.min(180, deg));
    return Math.max(900, Math.min(2100, us0 + Math.trunc(((us180 - us0) * deg) / 180)));
  };
  const duty = (us) => Math.floor((us * 65535) / 20000);

  // ------------------------------------------------------------------ sweep simulator
  const cv = document.getElementById("screen");
  if (cv) {
    const g = cv.getContext("2d");
    const W = 320, H = 240, CX = 160, CY = 236, R = 176, MIN = 30, MAX = 150;
    const el = (id) => document.getElementById(id);
    const state = { step: 3, settle: 70, range: 200, temp: 20, deg: MIN, dir: 1, trail: [], dets: new Map(), clock: 0 };
    const targets = [
      { a0: 36, a1: 66, d: (a) => 150 + 0.25 * (a - 51) },
      { a0: 93, a1: 102, d: () => 62 },
      { a0: 123, a1: 138, d: () => 115 },
    ];
    const green = (k) => {
      k = Math.max(0, Math.min(1, k));
      return `rgb(${40 + 160 * k | 0},${90 + 165 * k | 0},${40 + 100 * k | 0})`;
    };
    const polar = (deg, r) => [CX + Math.round(r * Math.cos(deg * Math.PI / 180)) + 0.5,
                               CY - Math.round(r * Math.sin(deg * Math.PI / 180)) + 0.5];
    const line = (x0, y0, x1, y1, c) => { g.strokeStyle = c; g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke(); };

    function sense(deg) {
      let best = null;
      for (const t of targets) {
        if (deg >= t.a0 && deg <= t.a1) {
          const d = t.d(deg) + (Math.random() - 0.5) * 3;
          if (best === null || d < best) best = d;
        }
      }
      return best !== null && best >= 2 && best <= state.range ? best : null;
    }

    function draw(cm) {
      g.fillStyle = "rgb(0,8,0)"; g.fillRect(0, 0, W, H);
      g.lineWidth = 1;
      g.font = "8px monospace"; g.textBaseline = "top";
      for (let q = 1; q <= 4; q++) {
        const r = (R * q) / 4;
        g.strokeStyle = "rgb(0,80,32)"; g.beginPath();
        for (let d = MIN; d <= MAX; d += 2) { const [x, y] = polar(d, r); d === MIN ? g.moveTo(x, y) : g.lineTo(x, y); }
        g.stroke();
        g.fillStyle = "rgb(40,160,88)"; g.fillText(String(Math.trunc((state.range * q) / 4)), CX + 4, CY - Math.trunc(r) + 3);
      }
      for (let d = MIN; d <= MAX; d += 30) { const [x, y] = polar(d, R); line(CX + 0.5, CY + 0.5, x, y, "rgb(0,80,32)"); }
      state.trail.forEach((d, i) => {
        const a0 = i === 0 ? state.deg : state.trail[i - 1];
        const [x0, y0] = polar(a0, R), [x1, y1] = polar(d, R);
        g.fillStyle = green((0.22 * (6 - i)) / 6); g.beginPath(); g.moveTo(CX, CY); g.lineTo(x0, y0); g.lineTo(x1, y1); g.fill();
      });
      const ttl = 10000;
      for (const [deg, v] of state.dets) {
        const age = state.clock - v.t;
        if (age > ttl) { state.dets.delete(deg); continue; }
        const [x, y] = polar(deg, (R * v.cm) / state.range);
        g.fillStyle = green(0.35 + 0.65 * (1 - age / ttl));
        g.beginPath(); g.arc(x, y, 3.2, 0, Math.PI * 2); g.fill();
      }
      const [sx, sy] = polar(state.deg, R); line(CX + 0.5, CY + 0.5, sx, sy, "rgb(120,255,160)");
      g.fillStyle = "rgb(90,150,115)"; g.font = "8px monospace";
      g.fillText("ANGLE (commanded)", 8, 6); g.fillText("DISTANCE", 128, 6); g.fillText("RANGE", 236, 6); g.fillText("LIVE", 282, 6);
      g.fillStyle = "rgb(200,255,215)"; g.font = "bold 24px monospace";
      g.fillText(String(state.deg).padStart(3, " "), 8, 18);
      g.font = "bold 24px monospace";
      if (cm === null) g.fillText("---", 128, 18);
      else { g.fillText(String(Math.round(cm)).padStart(3, " "), 128, 18); g.font = "14px monospace"; g.fillText("cm", 184, 26); }
      g.font = "bold 16px monospace"; g.fillText(String(state.range), 236, 22);
      for (const [x, lab] of [[6, "−"], [258, "+"]]) {
        g.fillStyle = "rgb(20,60,36)"; g.strokeStyle = "rgb(0,80,32)";
        g.beginPath(); g.roundRect ? g.roundRect(x, 198, 55, 35, 8) : g.rect(x, 198, 55, 35); g.fill(); g.stroke();
        g.fillStyle = "rgb(200,255,215)"; g.font = "bold 22px monospace"; g.fillText(lab, x + 21, 204);
      }
    }

    function stepMs(cm) {
      const echoMs = cm === null ? echoTimeoutUs(state.range, state.temp) / 1000 : (2 * cm / cmPerUs(state.temp)) / 1000;
      return state.settle + FRAME_PUSH_MS + DRAW_MS + echoMs;
    }

    function readout() {
      const typical = state.settle + FRAME_PUSH_MS + DRAW_MS + 6;
      const moves = Math.floor((MAX - MIN) / state.step);
      el("r-sweep").textContent = ((moves * typical) / 1000).toFixed(1) + " s";
      el("r-fps").textContent = (1000 / typical).toFixed(1) + " /s";
      el("r-timeout").textContent = (echoTimeoutUs(state.range, state.temp) / 1000).toFixed(1) + " ms";
    }

    function tick() {
      const cm = sense(state.deg);
      state.clock += stepMs(cm);
      const bin = state.deg;
      if (cm === null) state.dets.delete(bin); else state.dets.set(bin, { cm, t: state.clock });
      draw(cm);
      state.trail.unshift(state.deg); state.trail = state.trail.slice(0, 6);
      let next = state.deg + state.dir * state.step;
      if (next > MAX || next < MIN) { state.dir = -state.dir; next = state.deg + state.dir * state.step; }
      state.deg = Math.max(MIN, Math.min(MAX, next));
      setTimeout(tick, reduce ? 400 : stepMs(cm));
    }

    const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    for (const [id, key] of [["c-step", "step"], ["c-settle", "settle"], ["c-range", "range"], ["c-temp", "temp"]]) {
      const input = el(id), out = el(id + "-v");
      const update = () => { state[key] = Number(input.value); out.textContent = input.value; readout(); if (key === "step") state.dets.clear(); };
      input.addEventListener("input", update); update();
    }
    cv.addEventListener("click", (e) => {
      const r = cv.getBoundingClientRect();
      const x = ((e.clientX - r.left) / r.width) * W - CX, y = CY - ((e.clientY - r.top) / r.height) * H;
      const deg = (Math.atan2(y, x) * 180) / Math.PI, dist = (Math.hypot(x, y) / R) * state.range;
      if (deg >= MIN && deg <= MAX && dist >= 5 && dist <= state.range) {
        targets.push({ a0: deg - 3, a1: deg + 3, d: () => dist });
        el("sim-note").textContent = `Added a target at ${deg.toFixed(0)}°, ${dist.toFixed(0)} cm.`;
      }
    });
    el("c-reset").addEventListener("click", () => { targets.splice(3); state.dets.clear(); el("sim-note").textContent = "Targets reset."; });
    tick();
  }

  // ------------------------------------------------------------------ wiring explorer
  const box = document.getElementById("wiring");
  const chips = document.getElementById("netchips");
  const list = document.getElementById("pinlist");
  if (box && chips && window.NETLIST) {
    const nets = [...new Set(window.NETLIST.map((r) => r.net))];
    let active = null;
    const apply = () => {
      box.classList.toggle("filtering", !!active);
      box.querySelectorAll(".net").forEach((n) => n.classList.toggle("on", n.dataset.net === active));
      chips.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(c.dataset.net === active)));
      const rows = window.NETLIST.filter((r) => !active || r.net === active);
      list.innerHTML = "<table><thead><tr><th>Wire</th><th>Pin</th><th>Net</th><th>Notes</th></tr></thead><tbody>" +
        rows.map((r) => `<tr><td>${r.wire}</td><td><code>${r.pin}</code></td><td>${r.net}</td><td>${r.notes}</td></tr>`).join("") +
        "</tbody></table>";
    };
    nets.forEach((n) => {
      const b = document.createElement("button");
      b.className = "chip"; b.type = "button"; b.dataset.net = n; b.textContent = n;
      b.addEventListener("click", () => { active = active === n ? null : n; apply(); });
      chips.appendChild(b);
    });
    box.querySelectorAll(".net").forEach((n) => n.addEventListener("click", () => { active = active === n.dataset.net ? null : n.dataset.net; apply(); }));
    apply();
  }

  // ------------------------------------------------------------------ calculators
  const num = (id) => Number(document.getElementById(id).value);
  const set = (id, txt) => { const e = document.getElementById(id); if (e) e.textContent = txt; };
  function calc() {
    if (!document.getElementById("q-t")) return;
    const t = num("q-t"), T = num("q-T");
    set("q-d", `v = ${vSound(T).toFixed(2)} m/s  →  d = ${(t * cmPerUs(T) / 2).toFixed(1)} cm`);
    const vin = num("q-vin"), r1 = num("q-r1"), r2 = num("q-r2");
    const vout = vin * r2 / (r1 + r2);
    set("q-vout", `Vout = ${vout.toFixed(2)} V ${vout > 3.6 ? "✗ above ESP32 max" : vout < 2.475 ? "✗ below logic HIGH" : "✓ safe and readable"}`);
    const a = num("q-a"), us = pulseUs(a);
    set("q-duty", `pulse = ${us} µs  →  duty = ${duty(us)} / 65535 (${(us / 200).toFixed(2)} %)`);
  }
  document.querySelectorAll(".calc input").forEach((i) => i.addEventListener("input", calc));
  calc();
})();
