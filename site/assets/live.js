// Live console: Web Serial (Chrome/Edge/desktop app), log replay and a labelled demo.
// All three sources go through the same RadarCore parser, so what you see in a
// replay is exactly what you would see live.
(function () {
  "use strict";
  const RC = window.RadarCore;
  const $ = (id) => document.getElementById(id);
  const now = () => performance.now();

  const view = RC.createView($("radar"));
  let stats = RC.createStats();
  let recorder = null;
  let source = null; // {kind, stop: async fn}
  const logLines = [];

  // ------------------------------------------------------------------ rendering
  function fmtCm(cm) { return cm === null || cm === undefined ? "---" : `${cm.toFixed(1)} cm`; }
  function refresh() {
    const s = stats.state;
    $("s-deg").textContent = s.lastDeg === null ? "–" : `${s.lastDeg}°`;
    $("s-cm").textContent = s.lastDeg === null ? "–" : fmtCm(s.lastCm);
    $("s-near").textContent = s.nearestCm === null ? "–" : `${s.nearestCm.toFixed(1)} cm @ ${s.nearestDeg}°`;
    $("s-step").textContent = s.measuredStepMs !== null ? `${s.measuredStepMs.toFixed(1)} ms (fw)`
      : s.hostStepMs !== null ? `${s.hostStepMs.toFixed(0)} ms (host)` : "–";
    $("s-n").textContent = String(s.readings);
    $("s-valid").textContent = s.readings ? `${Math.round((100 * s.valid) / s.readings)} %` : "–";
    $("s-rec").textContent = recorder ? String(recorder.count) : "0";
    const c = s.config;
    $("s-sweep").textContent = `${c.min}°–${c.max}°, ${c.step}° steps, ${c.range} cm ${s.configFromDevice ? "(from device)" : "(default)"}`;
    $("s-meas").textContent = s.measuredSweepS !== null ? `${s.measuredSweepS.toFixed(2)} s one way, ${s.measuredStepMs.toFixed(1)} ms/step` : "–";
  }
  let dirty = true;
  function frame() {
    view.draw(now());
    if (dirty) { refresh(); dirty = false; }
    requestAnimationFrame(frame);
  }
  function resize() { view.resize(); }
  window.addEventListener("resize", resize);
  resize();
  requestAnimationFrame(frame);

  function log(line) {
    logLines.push(line);
    if (logLines.length > 300) logLines.splice(0, logLines.length - 300);
    const el = $("log");
    el.textContent = logLines.join("\n");
    el.scrollTop = el.scrollHeight;
  }

  function handle(events) {
    const t = now();
    for (const ev of events) {
      stats.apply(ev, t);
      view.add(ev, t);
      if (ev.type === "config") $("i-range").value = String(ev.range);
      if (recorder) recorder.add(ev, t);
      if (ev.type === "unknown" && stats.state.unknownLines === 20 && stats.state.readings === 0)
        log("! no readings yet — check the baud rate (115200), the USB cable (it must carry data) and that no other program has the port open");
    }
    if (events.length) dirty = true;
  }

  function feedLine(line) {
    log(line);
    const ev = RC.parseLine(line);
    if (ev) handle([ev]);
  }

  // ------------------------------------------------------------------ source control
  function setSource(kind, hint) {
    $("src-pill").textContent = kind || "idle";
    $("src-pill").dataset.kind = kind || "idle";
    $("src-hint").textContent = hint || "Choose a source on the right. The angle shown is the commanded servo position.";
    $("b-stop").disabled = !kind;
  }
  async function stopSource() {
    if (source) {
      const s = source;
      source = null;
      try { await s.stop(); } catch (e) { /* already closed */ }
    }
    setSource(null);
  }
  $("b-stop").addEventListener("click", stopSource);

  function resetSession() {
    stats = RC.createStats();
    view.clear();
    logLines.length = 0;
    $("log").textContent = "";
    dirty = true;
  }

  // demo ------------------------------------------------------------------
  $("b-demo").addEventListener("click", async () => {
    await stopSource();
    resetSession();
    const demo = RC.createDemo();
    let timer = null, stopped = false;
    const tick = () => {
      if (stopped) return;
      for (const l of demo.next()) feedLine(l);
      timer = setTimeout(tick, demo.stepMs);
    };
    source = { kind: "demo", stop: async () => { stopped = true; clearTimeout(timer); } };
    setSource("demo", "SYNTHETIC targets generated on this computer — not a real scanner.");
    tick();
  });

  // replay ----------------------------------------------------------------
  $("f-log").addEventListener("change", async (e) => {
    const file = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!file) return;
    await stopSource();
    resetSession();
    const items = RC.parseLog(await file.text());
    let i = 0, timer = null, stopped = false;
    const speed = () => Number($("sel-speed").value) || 1;
    const step = () => {
      if (stopped) return;
      if (i >= items.length) { log(`# replay finished (${items.length} lines)`); source = null; setSource(null); return; }
      const cur = items[i++];
      feedLine(cur.line);
      // wait for the next reading's timestamp; comments/headers go out immediately
      let delay = 0;
      const nxt = items[i];
      if (nxt && RC.parseLine(nxt.line) && RC.parseLine(nxt.line).type === "reading") {
        delay = cur.t !== null && nxt.t !== null ? Math.max(0, nxt.t - cur.t) : 101;
      }
      timer = setTimeout(step, Math.min(delay, 5000) / speed());
    };
    source = { kind: "replay", stop: async () => { stopped = true; clearTimeout(timer); } };
    setSource("replay", `Replaying ${file.name} (${items.length} lines). This shows recorded data, not a live scanner.`);
    step();
  });

  // serial ----------------------------------------------------------------
  const hasSerial = "serial" in navigator;
  if (!hasSerial) {
    $("b-serial").disabled = true;
    $("serial-note").textContent = document.documentElement.dataset.mode === "app"
      ? "Serial is unavailable in this build."
      : "Your browser has no Web Serial support. Use Chrome or Edge on a desktop, or the desktop app. Replay and demo work everywhere.";
  } else {
    $("serial-note").textContent = "Listen-only at 115 200 baud. Nothing is ever sent to the scanner.";
  }

  $("b-serial").addEventListener("click", async () => {
    if (!hasSerial) return;
    let port;
    try {
      port = await navigator.serial.requestPort();
    } catch (e) {
      return; // user cancelled the picker
    }
    await stopSource();
    resetSession();
    try {
      await port.open({ baudRate: 115200, dataBits: 8, stopBits: 1, parity: "none", bufferSize: 4096 });
    } catch (e) {
      log(`! could not open the port: ${e.message} (is another program using it?)`);
      return;
    }
    const parser = RC.createParser();
    const decoder = new TextDecoderStream();
    const done = port.readable.pipeTo(decoder.writable).catch(() => {});
    const reader = decoder.readable.getReader();
    let stopped = false;
    source = {
      kind: "serial",
      stop: async () => {
        stopped = true;
        try { await reader.cancel(); } catch (e) { /* ignore */ }
        await done;
        try { await port.close(); } catch (e) { /* ignore */ }
      },
    };
    const info = port.getInfo ? port.getInfo() : {};
    setSource("serial", `Connected${info.usbVendorId ? ` (USB ${info.usbVendorId.toString(16)}:${(info.usbProductId || 0).toString(16)})` : ""} — live data from the scanner.`);
    navigator.serial.addEventListener("disconnect", (ev) => {
      if (ev.target === port && source && source.kind === "serial") { log("# device disconnected"); stopSource(); }
    });
    try {
      while (!stopped) {
        const { value, done: end } = await reader.read();
        if (end) break;
        if (value) {
          const evs = parser.push(value);
          for (const l of value.split("\n")) if (l.trim()) log(l.replace(/\r$/, ""));
          handle(evs);
        }
      }
    } catch (e) {
      if (!stopped) log(`! serial read error: ${e.message}`);
    } finally {
      reader.releaseLock();
      if (!stopped) stopSource();
    }
  });

  // ------------------------------------------------------------------ session + view controls
  $("b-rec").addEventListener("click", () => {
    if (recorder && $("b-rec").getAttribute("aria-pressed") === "true") {
      $("b-rec").setAttribute("aria-pressed", "false");
      $("b-rec").textContent = "● Record";
      $("b-save").disabled = recorder.count === 0;
      return;
    }
    recorder = RC.createRecorder();
    $("b-rec").setAttribute("aria-pressed", "true");
    $("b-rec").textContent = "■ Stop recording";
    $("b-save").disabled = false;
    dirty = true;
  });
  $("b-save").addEventListener("click", () => {
    if (!recorder) return;
    const src = (source && source.kind) || "stopped";
    const blob = new Blob([recorder.toCsv(`source: ${src}`)], { type: "text/csv" });
    const a = document.createElement("a");
    const ts = new Date().toISOString().replace(/[:T]/g, "-").slice(0, 19);
    a.href = URL.createObjectURL(blob);
    a.download = `radar-session-${ts}.csv`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  });
  $("b-clear").addEventListener("click", () => { view.clear(); stats.resetNearest(); dirty = true; });
  $("i-range").addEventListener("change", () => {
    const r = Number($("i-range").value);
    if (r >= 20 && r <= 500) { view.setConfig({ range: r }); stats.state.config.range = r; dirty = true; }
  });
  $("i-ttl").addEventListener("input", () => { view.setTtl(Number($("i-ttl").value) * 1000); $("i-ttl-v").textContent = $("i-ttl").value; });

  // test hook (used by tests/browser and the desktop smoke test)
  window.__radarConsole = { stats: () => ({ ...stats.state }), detections: () => view.detectionCount, source: () => (source ? source.kind : null) };
})();
