# Live link and apps

The project ships in two forms built from the same files:

| Form | Where | Works offline | Live link to the scanner |
|---|---|---|---|
| **Web app** | the GitHub Pages site — open it in any browser; "Install web app" adds it to your desktop or phone home screen (a Progressive Web App (PWA)) | yes, after the first visit | Chrome or Edge on a desktop (Web Serial API) |
| **Desktop app** | Releases page: Windows installer or portable `.exe`, macOS `.dmg`, Linux `.AppImage` / `.tar.gz` | always (guide, simulator, console are bundled) | yes, on Windows, macOS and Linux |

Both contain the build guide, the sweep simulator, the wiring explorer and the **live console**.
The console has three sources, all decoded by the same parser
([`site/assets/radar-core.js`](../site/assets/radar-core.js)):

* **Connect scanner** — reads the firmware's serial output (115 200 baud, `angle_deg,distance_cm` lines).
* **Replay a log** — plays back a saved session, or any serial log, in any browser.
* **Demo** — synthetic targets, clearly labelled, for trying the console without hardware.

It can **record** a session and save it as CSV (`host_ms,angle_deg,distance_cm`) — use this for the
validation tests T-FW-4, T-FW-5 and T-LNK-1. The console **only listens**: it never sends a byte to the scanner.

Status: the parser, renderer, replay and demo are tested automatically (see
[`VALIDATION.md`](VALIDATION.md)); **the live serial link has never been connected to a real
scanner.** The desktop app has been built and smoke-tested on Linux only; the Windows and macOS
builds are produced by GitHub Actions on each release and are unsigned.

## Connecting the scanner

![Live console](../hardware/diagrams/live_console.png)

The Cheap Yellow Display has a USB-to-serial chip on board, so the **same USB cable that powers the
scanner** carries its readings. No extra wires or adapters.

1. Plug the scanner into the computer. Use a port or powered hub that can supply about 1 A; a weak
   port may make the board reset when the servo starts (see [Wiring → Power](WIRING.md#power--read-this)).
2. Open the **Live console** (web app in Chrome/Edge, or the desktop app) → **Connect scanner** →
   pick the port (CH340 or CP210x, depending on your board). Linux: if the port is refused, add yourself
   to the `dialout` group (`sudo usermod -aG dialout $USER`, then log out and in).
3. Opening the port may **restart** the board (the USB chip's reset lines). The sweep just starts again.
4. Nothing appears? Check the baud rate is 115 200 and that no other program (Arduino serial monitor)
   has the port open.

## Installing the desktop app

Download from the repository's **Releases** page (the latest release is linked from the web app).

| System | File | Notes |
|---|---|---|
| Windows 10/11 | `…-win-x64.exe` (installer) or `…-portable-x64.exe` | Unsigned: SmartScreen shows "unknown publisher" → *More info* → *Run anyway*. |
| macOS 12+ | `…-mac-arm64.dmg` (Apple silicon) or `…-mac-x64.dmg` (Intel) | Unsigned: first launch is blocked → System Settings → Privacy & Security → *Open Anyway*. |
| Linux x64 | `…-linux-x86_64.AppImage` or `…-linux-x64.tar.gz` | AppImage needs FUSE 2 (`sudo apt install libfuse2t64` on Ubuntu 24.04+); the `.tar.gz` needs nothing — unpack and run `ultrasonic-radar-scanner`. If it exits with a sandbox error (Ubuntu 24.04+ AppArmor), start it with `--no-sandbox`. |

Every release carries `SHA256SUMS` and a signed build-provenance attestation — see
[`SECURITY.md`](SECURITY.md#verifying-a-release-yourself).

## Building the apps yourself

```bash
# web app (GitHub Pages output in site/)
python -m pip install -r requirements-site.txt
python scripts/build_site.py

# desktop app
cd app
npm ci                                         # Electron, electron-builder, KaTeX (versions pinned in package-lock.json)
python ../scripts/build_site.py --app --out web
npm start                                      # run it
npm run dist                                   # build installers for this OS into app/dist/
```

The desktop app is a locked-down Electron window around the same pages: no Node.js access in the
page, sandboxed renderer, context isolation, a strict Content Security Policy (CSP), external links
open in your normal browser, and every browser permission except serial-port access is refused.
