// Ultrasonic Radar Scanner — desktop app (Electron main process).
//
// The window shows the same pages as the web app, bundled in ./web by
// `python ../scripts/build_site.py --app --out web`. The page gets no Node.js
// access: sandboxed renderer, context isolation, no preload, strict CSP in the
// HTML. The only browser permission granted is Web Serial (listen-only console);
// external links open in the system browser.
"use strict";

const { app, BrowserWindow, Menu, dialog, shell } = require("electron");
const path = require("node:path");
const fs = require("node:fs");
const { pathToFileURL } = require("node:url");

const WEB_DIR = path.join(__dirname, "web");
const WEB_URL = pathToFileURL(WEB_DIR).href;
const REPO = "https://github.com/Normansrule/ultrasonic-radar-scanner";
const SMOKE = process.argv.includes("--smoke-test");

if (!SMOKE && !app.requestSingleInstanceLock()) app.quit();

const isInternal = (url) => url === WEB_URL || url.startsWith(WEB_URL + "/");
const isHttp = (url) => /^https?:\/\//i.test(url);

let win = null;

function page(name) {
  return path.join(WEB_DIR, name);
}

function choosePort(portList, callback) {
  if (!portList.length) {
    dialog.showMessageBox(win, {
      type: "info",
      title: "No serial ports",
      message: "No serial ports were found.",
      detail: "Plug in the USB-to-serial adapter of the telemetry tap, then press Connect again. " +
        "On Linux your user must be in the 'dialout' group. See Guide → Live link & apps.",
    });
    callback("");
    return;
  }
  const labels = portList.map((p) => `${p.displayName || p.portName || "Serial port"}${p.portName && p.displayName ? `  (${p.portName})` : ""}`);
  dialog.showMessageBox(win, {
    type: "question",
    title: "Connect scanner",
    message: "Choose the telemetry adapter's serial port",
    detail: "The console only listens (115 200 baud). Never connect the ESP32's own USB port while the battery harness is connected.",
    buttons: [...labels, "Cancel"],
    cancelId: labels.length,
    defaultId: 0,
    noLink: true,
  }).then(({ response }) => callback(response < portList.length ? portList[response].portId : ""))
    .catch(() => callback(""));
}

function hardenSession(ses) {
  ses.setPermissionCheckHandler((_wc, permission, origin) => permission === "serial" && (origin || "").startsWith("file://"));
  ses.setDevicePermissionHandler((details) => details.deviceType === "serial" && (details.origin || "").startsWith("file://"));
  ses.setPermissionRequestHandler((_wc, _permission, cb) => cb(false)); // camera, mic, geolocation, notifications… all refused
  ses.on("select-serial-port", (event, portList, _wc, callback) => {
    event.preventDefault();
    choosePort(portList, callback);
  });
  ses.on("will-download", (item) => {
    // CSV session exports: let the user pick where to save
    item.setSaveDialogOptions({ title: "Save session log", filters: [{ name: "CSV", extensions: ["csv"] }] });
  });
}

function createWindow() {
  win = new BrowserWindow({
    width: 1320,
    height: 880,
    minWidth: 860,
    minHeight: 600,
    show: !SMOKE,
    backgroundColor: "#0b110e",
    title: "Ultrasonic Radar Scanner",
    icon: path.join(__dirname, "build", "icon.png"),
    autoHideMenuBar: false,
    webPreferences: {
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      webSecurity: true,
      spellcheck: false,
      devTools: !app.isPackaged || process.env.RADAR_DEVTOOLS === "1",
    },
  });
  hardenSession(win.webContents.session);

  win.webContents.setWindowOpenHandler(({ url }) => {
    if (isHttp(url)) shell.openExternal(url);
    else if (isInternal(url)) win.loadURL(url);
    return { action: "deny" };
  });
  win.webContents.on("will-navigate", (event, url) => {
    if (isInternal(url)) return;
    event.preventDefault();
    if (isHttp(url)) shell.openExternal(url);
  });
  win.webContents.on("will-attach-webview", (event) => event.preventDefault());

  win.loadFile(page("index.html"));
  return win;
}

function buildMenu() {
  const go = (name) => () => win && win.loadFile(page(name));
  const template = [
    ...(process.platform === "darwin" ? [{ role: "appMenu" }] : []),
    { label: "File", submenu: [process.platform === "darwin" ? { role: "close" } : { role: "quit" }] },
    {
      label: "Go",
      submenu: [
        { label: "Home", accelerator: "CmdOrCtrl+1", click: go("index.html") },
        { label: "Live console", accelerator: "CmdOrCtrl+2", click: go("live.html") },
        { label: "Build guide", accelerator: "CmdOrCtrl+3", click: go("guide/overview.html") },
        { label: "Wiring", click: go("guide/wiring.html") },
        { label: "Validation log", click: go("guide/validation.html") },
        { type: "separator" },
        { label: "Back", accelerator: "Alt+Left", click: () => win && win.webContents.navigationHistory.goBack() },
        { label: "Forward", accelerator: "Alt+Right", click: () => win && win.webContents.navigationHistory.goForward() },
      ],
    },
    { role: "viewMenu" },
    { role: "windowMenu" },
    {
      role: "help",
      submenu: [
        { label: "Project on GitHub", click: () => shell.openExternal(REPO) },
        { label: "Latest release", click: () => shell.openExternal(`${REPO}/releases/latest`) },
        {
          label: "About",
          click: () => dialog.showMessageBox(win, {
            type: "info",
            title: "About",
            message: `Ultrasonic Radar Scanner ${app.getVersion()}`,
            detail: "Educational ultrasonic (sonar) instrument with a radar-style display — not RF radar and not a safety device.\n" +
              "The angle shown is the commanded servo position.\nMIT licence.",
          }),
        },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ---------------------------------------------------------------- smoke test
// `electron . --smoke-test [--shot=file.png]`: loads every main page, runs the
// demo in the live console, fails on any page error, then exits.
async function smokeTest() {
  const shotArg = process.argv.find((a) => a.startsWith("--shot="));
  const errors = [];
  win.webContents.on("console-message", (e) => {
    const level = e.level !== undefined ? e.level : e;
    if (level === "error" || level === 3) errors.push(e.message || String(e));
  });
  win.webContents.on("render-process-gone", (_e, d) => errors.push("renderer gone: " + d.reason));
  const load = (name) => new Promise((resolve, reject) => {
    win.webContents.once("did-finish-load", resolve);
    win.webContents.once("did-fail-load", (_e, code, desc) => reject(new Error(`${name}: ${desc} (${code})`)));
    win.loadFile(page(name));
  });
  const results = {};
  try {
    for (const name of ["index.html", "guide/overview.html", "guide/equations.html", "guide/live-link.html"]) {
      await load(name);
      results[name] = await win.webContents.executeJavaScript(
        "({title: document.title, mode: document.documentElement.dataset.mode, " +
        "brokenImages: [...document.images].filter(i => !i.complete || i.naturalWidth === 0).length, " +
        "katex: typeof window.katex})");
      if (name === "guide/equations.html") {
        await new Promise((r) => setTimeout(r, 800)); // KaTeX auto-render runs after load
        results.mathRendered = await win.webContents.executeJavaScript("document.querySelectorAll('.katex').length");
      }
    }
    await load("live.html");
    results.serialApi = await win.webContents.executeJavaScript("'serial' in navigator");
    await win.webContents.executeJavaScript("document.getElementById('b-demo').click()");
    await new Promise((r) => setTimeout(r, 2500));
    results.live = await win.webContents.executeJavaScript("window.__radarConsole.stats()");
    if (shotArg) {
      win.setSize(1320, 880);
      await new Promise((r) => setTimeout(r, 1500));
      const img = await win.webContents.capturePage();
      fs.writeFileSync(shotArg.slice(7), img.toPNG());
    }
  } catch (e) {
    errors.push(String(e));
  }
  const ok = !errors.length && results.live && results.live.readings >= 10 && results.serialApi === true &&
    results["index.html"].mode === "app" && results.mathRendered > 0 &&
    Object.values(results).every((r) => !r || r.brokenImages === undefined || r.brokenImages === 0);
  process.stdout.write(JSON.stringify({ ok, errors, results }, null, 2) + "\n");
  app.exit(ok ? 0 : 1);
}

app.whenReady().then(() => {
  buildMenu();
  createWindow();
  if (SMOKE) {
    win.webContents.once("did-finish-load", smokeTest);
  }
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("second-instance", () => {
  if (win) {
    if (win.isMinimized()) win.restore();
    win.focus();
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
