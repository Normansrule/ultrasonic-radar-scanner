#!/usr/bin/env python3
"""
Build the web app (GitHub Pages) or the desktop app's offline copy from the same
content as the repository.

  <out>/index.html             landing page (site/_templates/index.html)
  <out>/live.html              live / replay console (site/_templates/live.html)
  <out>/guide/<page>.html      README + docs/*.md + CREDITS.md + CHANGELOG.md rendered to HTML
  <out>/assets/...             static assets, diagrams, equation plots, icons
  <out>/manifest.webmanifest, <out>/sw.js   installable web app (web mode only)

Usage:
  python scripts/build_site.py                      # web mode -> site/   (GitHub Pages)
  python scripts/build_site.py --app --out app/web  # desktop mode: offline KaTeX, CSP, no service worker
  python scripts/build_site.py --firmware build/fw/Radar_V6.ino.merged.bin   # web mode + browser flasher payload
Needs: Markdown (requirements-site.txt). Desktop mode also needs `npm ci` in app/ (KaTeX copy).
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
REPO = os.environ.get("GITHUB_REPOSITORY", "Normansrule/ultrasonic-radar-scanner")
REPO_URL = f"https://github.com/{REPO}"
APP_VERSION = json.loads((ROOT / "app" / "package.json").read_text())["version"]
KATEX_VERSION = "0.16.47"  # keep equal to app/package.json

PAGES = [  # (source, output slug, nav title)
    ("README.md", "overview", "Overview"),
    ("docs/REQUIREMENTS.md", "requirements", "Requirements"),
    ("docs/BOM.md", "bom", "Bill of materials"),
    ("docs/PRINTING.md", "printing", "Printing"),
    ("docs/WIRING.md", "wiring", "Wiring"),
    ("docs/ASSEMBLY.md", "assembly", "Assembly"),
    ("docs/EQUATIONS.md", "equations", "Equations"),
    ("docs/LIVE_LINK.md", "live-link", "Live link & apps"),
    ("docs/VALIDATION.md", "validation", "Validation log"),
    ("docs/SECURITY.md", "security", "Security & safety"),
    ("docs/GLOSSARY.md", "glossary", "Glossary"),
    ("docs/PUBLISH.md", "publish", "Publishing"),
    ("CREDITS.md", "credits", "Credits & sources"),
    ("CHANGELOG.md", "changelog", "Changelog"),
]
SLUG = {src: slug for src, slug, _ in PAGES}

APP_CSP = ('<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; '
           'script-src \'self\' \'unsafe-inline\'; style-src \'self\' \'unsafe-inline\'; '
           'img-src \'self\' data: blob:; font-src \'self\' data:; connect-src \'self\'; '
           'object-src \'none\'; base-uri \'none\'; form-action \'none\'">')


def katex_tags(app: bool) -> str:
    base = "../assets/vendor/katex" if app else f"https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist"
    return (f'<link rel="stylesheet" href="{base}/katex.min.css">\n'
            f'<script defer src="{base}/katex.min.js"></script>\n'
            f'<script defer src="{base}/contrib/auto-render.min.js" onload="renderMathInElement(document.body,'
            "{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}]});\"></script>")


def protect_math(md: str):
    store = []

    def keep(m):
        store.append(m.group(0))
        return f"@@MATH{len(store) - 1}@@"
    md = re.sub(r"\$\$.+?\$\$", keep, md, flags=re.S)
    md = re.sub(r"(?<![\\$])\$(?!\s)[^$\n]+?(?<!\s)\$", keep, md)
    return md, store


def restore_math(h: str, store):
    return re.sub(r"@@MATH(\d+)@@", lambda m: html.escape(store[int(m.group(1))], quote=False), h)


def rewrite_link(target: str, src: str) -> str:
    if re.match(r"^[a-z]+:", target) or target.startswith("#"):
        return target
    path, _, frag = target.partition("#")
    frag = f"#{frag}" if frag else ""
    base = (ROOT / src).parent
    abs_p = (base / path).resolve()
    try:
        rel = abs_p.relative_to(ROOT).as_posix()
    except ValueError:
        return target
    if rel in SLUG:
        return f"{SLUG[rel]}.html{frag}"
    if rel.startswith("hardware/diagrams/"):
        return "../assets/diagrams/" + rel.split("/", 2)[2]
    if rel.startswith("docs/img/"):
        return "../assets/img/" + rel.split("/", 2)[2]
    kind = "tree" if abs_p.is_dir() else "blob"
    return f"{REPO_URL}/{kind}/main/{rel}{frag}"


def github_slug(text: str) -> str:
    t = re.sub(r"<[^>]+>", "", text).strip().lower()
    t = re.sub(r"[^\w\- ]", "", t)
    return t.replace(" ", "-")


def head_common(prefix: str, app: bool) -> str:
    tags = [APP_CSP] if app else [f'<link rel="manifest" href="{prefix}manifest.webmanifest">']
    tags += ['<meta name="theme-color" content="#0b110e">',
             f'<link rel="icon" href="{prefix}assets/icons/icon-192.png">',
             f'<link rel="apple-touch-icon" href="{prefix}assets/icons/icon-192.png">']
    return "\n".join(tags)


def render_page(src: str, slug: str, title: str, app: bool) -> str:
    md = (ROOT / src).read_text(encoding="utf-8")
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    for kind in ("IMPORTANT", "WARNING", "NOTE", "TIP", "CAUTION"):
        md = md.replace(f"> [!{kind}]\n> ", f"> **{kind.title()}.** ")
    md, store = protect_math(md)
    body = markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"])
    body = restore_math(body, store)
    body = re.sub(r'(href|src)="([^"]+)"', lambda m: f'{m.group(1)}="{rewrite_link(html.unescape(m.group(2)), src)}"', body)
    body = re.sub(r"<(h[1-4])>(.*?)</\1>", lambda m: f'<{m.group(1)} id="{github_slug(m.group(2))}">{m.group(2)}</{m.group(1)}>', body)
    body = body.replace("<table>", '<div class="tablewrap"><table>').replace("</table>", "</table></div>")
    if app:  # the offline app never loads remote images (status badges etc.)
        body = re.sub(r'<a [^>]*>\s*<img [^>]*src="https?://[^"]*"[^>]*>\s*</a>\s*', "", body)
        body = re.sub(r'<img [^>]*src="https?://[^"]*"[^>]*>', "", body)
    here = ' class="here"'
    nav = "\n".join(f'<a href="{s}.html"{here if s == slug else ""}>{html.escape(t)}</a>'
                    for _, s, t in PAGES)
    return f"""<!doctype html>
<html lang="en" data-mode="{'app' if app else 'web'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
{head_common('../', app)}
<title>{html.escape(title)} · Ultrasonic Radar Scanner</title>
<link rel="stylesheet" href="../assets/style.css">{katex_tags(app)}
</head><body class="guide">
<header class="top"><a class="brand" href="../index.html"><span class="dot"></span>Ultrasonic Radar Scanner</a>
<nav class="toplinks"><a href="../index.html">Home</a><a href="overview.html" aria-current="page">Guide</a><a href="../live.html">Live console</a><a class="web-only" href="../flash.html">Flash</a></nav>
<span class="badge">educational sonar · not physically validated yet</span>
<a class="gh web-only" href="{REPO_URL}">GitHub</a></header>
<div class="layout"><nav class="side">{nav}</nav>
<main class="doc">{body}
<p class="src">Source: <a href="{REPO_URL}/blob/main/{src}">{src}</a> — generated by scripts/build_site.py</p>
</main></div>
<script src="../assets/pwa.js" data-root="../"></script>
</body></html>
"""


def validation_counts():
    v = (ROOT / "docs" / "VALIDATION.md").read_text(encoding="utf-8")
    recorded = len(re.findall(r"^\| R-[A-Z]+-\d+ \|.*\| PASS \|", v, re.M))
    physical_total = len(re.findall(r"^\| T-[A-Z]+-\d+ \|", v, re.M))
    physical_done = physical_total - len(re.findall(r"^\| T-[A-Z]+-\d+ \|.*\| NOT RUN \|", v, re.M))
    return recorded, physical_done, physical_total


def fill(tpl: str, app: bool, extra: dict) -> str:
    rec, done, total = validation_counts()
    out = (tpl.replace("{{REPO_URL}}", REPO_URL)
              .replace("{{MODE}}", "app" if app else "web")
              .replace("{{VERSION}}", APP_VERSION)
              .replace("{{CSP}}", APP_CSP if app else "")
              .replace("{{HEAD_COMMON}}", head_common("", app))
              .replace("{{RECORDED}}", str(rec))
              .replace("{{PHYS_DONE}}", str(done))
              .replace("{{PHYS_TOTAL}}", str(total)))
    for k, v in extra.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def flash_block(out: Path, firmware: str, app: bool) -> str:
    """Copy the firmware image + ESP Web Tools manifest into <out>/firmware/ and return the HTML for the install card."""
    fw_dir = out / "firmware"
    if app:
        return ""
    if not firmware:
        if fw_dir.exists():
            shutil.rmtree(fw_dir)
        return ('<p><b>No firmware image in this build.</b> The GitHub Pages deployment compiles the firmware and '
                f'publishes it here; it is also attached to every <a href="{REPO_URL}/releases/latest">release</a>.</p>')
    src = Path(firmware)
    fw_dir.mkdir(parents=True, exist_ok=True)
    name = "radar_v6_esp32_merged.bin"
    shutil.copy2(src, fw_dir / name)
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    commit = os.environ.get("GITHUB_SHA", "local build")[:12]
    manifest = {"name": "Ultrasonic Radar Scanner (Radar V6)", "version": APP_VERSION,
                "new_install_prompt_erase": True,
                "builds": [{"chipFamily": "ESP32", "parts": [{"path": name, "offset": 0}]}]}
    (fw_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return (f'<esp-web-install-button manifest="firmware/manifest.json">'
            f'<button slot="activate" class="btn primary big">Install firmware {APP_VERSION}</button>'
            f'<span slot="unsupported">Your browser cannot flash boards — use Chrome or Edge on a desktop computer.</span>'
            f'<span slot="not-allowed">Open this page over https (GitHub Pages) to flash.</span></esp-web-install-button>'
            f'<dl class="stats"><dt>image</dt><dd>{name} ({src.stat().st_size // 1024} KiB, offset 0x0)</dd>'
            f'<dt>SHA-256</dt><dd class="hash">{digest}</dd><dt>built from</dt><dd>{commit}</dd>'
            f'<dt>board</dt><dd>ESP32 Dev Module (classic WROOM-32)</dd></dl>')


def write_pwa(out: Path):
    manifest = {
        "name": "Ultrasonic Radar Scanner",
        "short_name": "Radar Scanner",
        "description": "Build guide, simulator and live console for an educational ultrasonic scanner with a radar-style display.",
        "start_url": "./index.html",
        "scope": "./",
        "display": "standalone",
        "background_color": "#0b110e",
        "theme_color": "#0b110e",
        "icons": [
            {"src": "assets/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "assets/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "assets/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
        "shortcuts": [{"name": "Live console", "url": "./live.html"}, {"name": "Build guide", "url": "./guide/overview.html"}],
    }
    (out / "manifest.webmanifest").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*")
                   if p.is_file() and not p.name.startswith(".") and "_templates" not in p.parts and p.name != "sw.js"
                   and "firmware" not in p.relative_to(out).parts)
    digest = hashlib.sha256()
    for f in files:
        digest.update(f.encode())
        digest.update((out / f).read_bytes())
    version = digest.hexdigest()[:12]
    sw = f"""// Generated by scripts/build_site.py - offline copy of the web app.
const CACHE = "radar-{version}";
const FILES = {json.dumps(["./"] + files)};
self.addEventListener("install", (e) => {{
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(FILES)).then(() => self.skipWaiting()));
}});
self.addEventListener("activate", (e) => {{
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
}});
self.addEventListener("fetch", (e) => {{
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  if (req.mode === "navigate") {{
    // pages: network first so a new deploy shows up, cache when offline
    e.respondWith(fetch(req).then((r) => {{ const c = r.clone(); caches.open(CACHE).then((x) => x.put(req, c)); return r; }})
      .catch(() => caches.match(req).then((r) => r || caches.match("./index.html"))));
    return;
  }}
  e.respondWith(caches.match(req).then((r) => r || fetch(req)));
}});
"""
    (out / "sw.js").write_text(sw, encoding="utf-8")
    return version, len(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", action="store_true", help="desktop-app build: offline KaTeX, CSP, no service worker")
    ap.add_argument("--out", default=str(SITE), help="output directory (default: site/)")
    ap.add_argument("--firmware", default="", help="merged ESP32 image (offset 0x0) for the browser flasher")
    a = ap.parse_args()
    out = Path(a.out)
    if not out.is_absolute():
        out = (Path.cwd() / out).resolve()
    if out != SITE:
        if out.exists():
            shutil.rmtree(out)
        shutil.copytree(SITE / "assets", out / "assets",
                        ignore=shutil.ignore_patterns("diagrams", "img", "vendor"))
    for d in ("guide", "assets/diagrams", "assets/img"):
        if (out / d).exists():
            shutil.rmtree(out / d)  # generated copies only - drop files a previous version left behind
        (out / d).mkdir(parents=True, exist_ok=True)
    for f in (p for p in (ROOT / "hardware" / "diagrams").iterdir() if p.is_file()):
        shutil.copy2(f, out / "assets" / "diagrams" / f.name)
    for f in (ROOT / "docs" / "img").iterdir():
        shutil.copy2(f, out / "assets" / "img" / f.name)
    if a.app:
        kdist = ROOT / "app" / "node_modules" / "katex" / "dist"
        if not kdist.exists():
            raise SystemExit("app/node_modules/katex is missing - run `npm ci` in app/ first")
        dst = out / "assets" / "vendor" / "katex"
        shutil.copytree(kdist, dst, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("*.mjs", "*.ts", "katex.js", "katex.css", "README.md"))

    for src, slug, title in PAGES:
        (out / "guide" / f"{slug}.html").write_text(render_page(src, slug, title, a.app), encoding="utf-8")

    # landing page: embed the live wiring SVG and the net list
    svg = (ROOT / "hardware" / "diagrams" / "wiring_picture.svg").read_text(encoding="utf-8")
    wiring = (ROOT / "docs" / "WIRING.md").read_text(encoding="utf-8")
    block = wiring.split("<!-- NETLIST:BEGIN -->")[1].split("<!-- NETLIST:END -->")[0]
    rows = [l for l in block.strip().splitlines() if l.startswith("|")][2:]
    net = [dict(zip(["id", "wire", "pin", "net", "kind", "notes"], [c.strip() for c in r.strip("|").split("|")]))
           for r in rows]
    extra = {"WIRING_SVG": svg, "NETLIST_JSON": json.dumps(net), "FLASH_BLOCK": flash_block(out, a.firmware, a.app)}
    pages = ("index.html", "live.html") if a.app else ("index.html", "live.html", "flash.html")
    if a.app and (out / "flash.html").exists():
        (out / "flash.html").unlink()
    for name in pages:
        tpl = (SITE / "_templates" / name).read_text(encoding="utf-8")
        (out / name).write_text(fill(tpl, a.app, extra), encoding="utf-8")
    (out / ".nojekyll").write_text("")
    if a.app:
        for f in ("manifest.webmanifest", "sw.js"):
            if (out / f).exists():
                (out / f).unlink()
        print(f"desktop web bundle built -> {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    else:
        version, n = write_pwa(out)
        print(f"site built: {len(PAGES)} guide pages, landing + live console, PWA cache {version} ({n} files) "
              f"-> {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}  (repo link {REPO_URL})")


if __name__ == "__main__":
    main()
