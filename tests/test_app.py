"""Static checks on the web/desktop app: versions agree, the Electron window stays
locked down, and the live console can only listen."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = json.loads((ROOT / "app" / "package.json").read_text())
MAIN = (ROOT / "app" / "main.js").read_text()
LIVE = (ROOT / "site" / "assets" / "live.js").read_text()
CORE = (ROOT / "site" / "assets" / "radar-core.js").read_text()


def test_versions_agree():
    changelog = (ROOT / "CHANGELOG.md").read_text()
    top = re.search(r"^## (\d+\.\d+\.\d+)", changelog, re.M).group(1)
    assert PKG["version"] == top
    build_site = (ROOT / "scripts" / "build_site.py").read_text()
    assert f'KATEX_VERSION = "{PKG["devDependencies"]["katex"]}"' in build_site


def test_toolchain_pinned_exactly():
    for name, ver in PKG["devDependencies"].items():
        assert re.fullmatch(r"\d+\.\d+\.\d+", ver), f"{name} must be pinned exactly, got {ver}"
    lock = json.loads((ROOT / "app" / "package-lock.json").read_text())
    for name, ver in PKG["devDependencies"].items():
        assert lock["packages"][f"node_modules/{name}"]["version"] == ver


def test_electron_window_is_locked_down():
    for needle in ("contextIsolation: true", "sandbox: true", "nodeIntegration: false", "webSecurity: true",
                   "setPermissionRequestHandler", "setWindowOpenHandler", '"will-navigate"', "will-attach-webview"):
        assert needle in MAIN, needle
    assert not re.search(r"preload\s*:", MAIN), "the page must not get a preload bridge"
    assert "shell.openExternal(url)" in MAIN and "isHttp(url)" in MAIN


def test_packaged_files_are_minimal():
    assert set(PKG["build"]["files"]) == {"main.js", "package.json", "web/**/*", "build/icon.png"}


def test_console_never_writes_to_the_scanner():
    for text in (LIVE, CORE):
        assert "getWriter" not in text and ".writable.getWriter" not in text
        assert "setSignals" not in text
    assert "readable" in LIVE  # it does read


def test_app_pages_have_csp():
    bs = (ROOT / "scripts" / "build_site.py").read_text()
    assert "Content-Security-Policy" in bs and "object-src \\'none\\'" in bs


def test_live_link_docs_keep_the_usb_rule():
    doc = (ROOT / "docs" / "LIVE_LINK.md").read_text()
    assert "never plug the ESP32's own USB port in while the" in doc
    assert "VCC / 5V / 3V3** — leave unconnected" in doc
