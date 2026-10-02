"""
Headless-browser checks of the built web app (site/). Not part of the fast test run;
needs Playwright + Chromium:  python -m pip install playwright==1.56.0 && python -m playwright install chromium
Run:  python scripts/build_site.py && python tests/browser/check_site.py [--shots DIR]
"""
from __future__ import annotations

import argparse
import functools
import http.server
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"

SAMPLE_LOG = """# Radar V5.1 - educational ultrasonic sonar, radar-style display
# sweep 30..150 deg, step 3, settle 70 ms, range 200 cm, echo timeout 13812 us
host_ms,angle_deg,distance_cm
0,84,61.0
100,87,60.5
200,90,60.2
300,93,-1
400,96,118.0
"""


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default="")
    ap.add_argument("--chromium", default="")
    ap.add_argument("--readme-shot", action="store_true", help="also refresh hardware/diagrams/live_console.png")
    a = ap.parse_args()
    httpd, base = serve()
    failures = []

    def check(name, ok, detail=""):
        print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))
        if not ok:
            failures.append(name)

    with sync_playwright() as p:
        kw = {"executable_path": a.chromium} if a.chromium else {}
        browser = p.chromium.launch(**kw)
        page = browser.new_page(viewport={"width": 1360, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        # only same-origin failures count; the sandbox running these tests may not reach the KaTeX CDN
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "Failed to load resource" not in m.text else None)
        page.on("requestfailed", lambda r: errors.append("request failed: " + r.url) if r.url.startswith(base) else None)

        # landing page
        page.goto(base + "/index.html")
        page.wait_for_timeout(1500)
        check("landing: simulator readout filled", page.inner_text("#r-sweep") not in ("", "–"), page.inner_text("#r-sweep"))
        check("landing: wiring explorer chips", page.locator("#netchips .chip").count() >= 15)
        check("landing: links to live console", page.locator('a[href="live.html"]').count() >= 2)
        sw = page.evaluate("navigator.serviceWorker.getRegistration().then(r => !!r)")
        page.wait_for_timeout(500)
        sw = page.evaluate("navigator.serviceWorker.getRegistration().then(r => !!r)")
        check("landing: service worker registered", sw)
        man = page.evaluate("fetch('manifest.webmanifest').then(r => r.json()).then(j => j.name)")
        check("landing: manifest served", man == "Ultrasonic Radar Scanner", man)
        if a.shots:
            page.screenshot(path=f"{a.shots}/web_landing.png")

        # live console - demo
        page.goto(base + "/live.html")
        page.wait_for_timeout(500)
        check("live: serial button present", page.locator("#b-serial").count() == 1)
        page.click("#b-demo")
        page.wait_for_timeout(2600)
        st = page.evaluate("window.__radarConsole.stats()")
        check("live demo: readings arrive", st["readings"] >= 15, f"{st['readings']} readings")
        check("live demo: config parsed from stream", st["configFromDevice"] and st["config"]["range"] == 200)
        check("live demo: labelled synthetic", "SYNTHETIC" in page.inner_text("#src-hint"))
        if a.shots:
            page.wait_for_timeout(2500)
            page.screenshot(path=f"{a.shots}/web_live_demo.png")
        if a.readme_shot:
            page.wait_for_timeout(2500)
            page.screenshot(path=str(ROOT / "hardware" / "diagrams" / "live_console.png"),
                            clip={"x": 0, "y": 0, "width": 1360, "height": 730})
        page.click("#b-rec")
        page.wait_for_timeout(1200)
        with page.expect_download() as dl:
            page.click("#b-save")
        csv = Path(dl.value.path()).read_text()
        check("live: recorded CSV saved", csv.count("\n") > 5 and "host_ms,angle_deg,distance_cm" in csv)
        page.click("#b-stop")

        # replay
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write(SAMPLE_LOG)
        page.set_input_files("#f-log", f.name)
        page.wait_for_timeout(1200)
        st = page.evaluate("window.__radarConsole.stats()")
        check("replay: all readings played", st["readings"] == 5, f"{st['readings']}")
        check("replay: nearest echo", abs((st["nearestCm"] or 0) - 60.2) < 1e-6 and st["nearestDeg"] == 90)
        check("replay: no-echo counted", st["valid"] == 4)

        # firmware flasher page
        page.goto(base + "/flash.html")
        check("flash: page has the safety steps", "unplug the" in page.inner_text("main").lower())
        if (SITE / "firmware" / "manifest.json").exists():
            man = page.evaluate("fetch('firmware/manifest.json').then(r => r.json())")
            part = man["builds"][0]["parts"][0]
            size = page.evaluate(f"fetch('firmware/{part['path']}').then(r => r.arrayBuffer()).then(b => b.byteLength)")
            check("flash: manifest + merged image served", man["builds"][0]["chipFamily"] == "ESP32" and part["offset"] == 0 and size > 200_000, f"{size} bytes")
            check("flash: install button present", page.locator("esp-web-install-button").count() == 1)
        else:
            check("flash: shows no-firmware notice", "No firmware image" in page.inner_text("main"))

        # guide pages render math and have no broken local images
        page.goto(base + "/guide/equations.html")
        page.wait_for_timeout(2500)
        broken = page.evaluate("[...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.src)")
        check("guide: images load", not broken, str(broken))
        page.goto(base + "/guide/live-link.html")
        broken = page.evaluate("[...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.src)")
        check("guide/live-link: images load", not broken, str(broken))

        # offline: service worker serves the console
        ctx = page.context
        page.goto(base + "/index.html")
        page.wait_for_timeout(1500)
        ctx.set_offline(True)
        try:
            page.goto(base + "/live.html")
            check("offline: live console served from cache", page.locator("#b-demo").count() == 1)
        except Exception as e:  # noqa: BLE001
            check("offline: live console served from cache", False, str(e)[:120])
        ctx.set_offline(False)

        check("no page errors or failed same-origin requests", not errors, "; ".join(errors[:3]))
        browser.close()
    httpd.shutdown()
    print(f"\n{'ALL PASS' if not failures else str(len(failures)) + ' FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
