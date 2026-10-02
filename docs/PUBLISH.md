# Publishing: repository, web app and desktop app (Ubuntu)

Two copy-and-paste blocks for an Ubuntu terminal (native or Windows Subsystem for Linux (WSL)).

1. **Publish** — pushes the repository, turns on the **web app** (GitHub Pages) and tags release
   `v5.2.0`; GitHub Actions then builds the **desktop app** (Windows, macOS, Linux), the **firmware
   images** and the **manufacturing kit** and attaches them to the release.
2. **Keep building** — sets up a local workspace: tests, the web app, the desktop app from source and
   (optionally) the firmware compile.

Both run inside `( … )`, so an error stops the block without closing your terminal, and both are safe
to paste again.

## 1 — Publish (repository, web app, desktop app, manufacturing kit)

What it does, in order: installs `git` + GitHub CLI (`gh`), signs you in, unpacks the newest ZIP from
Downloads, commits, creates the public repository, pushes, turns on the **web app** (GitHub Pages,
including the firmware flasher), and tags release **v5.2.0**. The release workflow then builds and
attaches the **desktop apps**, **firmware images** and the **manufacturing kit**.

* Edit `OWNER` on the first line if the repository should belong to another GitHub account.
* The only interactive step is a GitHub browser sign-in (skipped if `gh` is already signed in as `OWNER`).
* On a fresh Ubuntu it installs `gh` from Ubuntu, or from GitHub's own apt repository if Ubuntu's copy is
  missing or older than 2.40.
* If `~/.ssh/config` has `Host github-normansrule`, it pushes over that SSH alias; otherwise over HTTPS
  through `gh` (with the `workflow` scope GitHub requires for `.github/workflows/`).
* ZIP: newest `ultrasonic-radar-scanner*.zip` in `~/Downloads` or the Windows Downloads folders (WSL);
  unpacked to `~/projects/ultrasonic-radar-scanner`. It never runs Git in your home folder.
* `sudo` is used only for package installation. Safe to paste again.
* Web app: about 5 minutes. Release builds: roughly 15–25 minutes; the block waits up to 40 minutes
  and lists the files — **Ctrl+C is safe** by then, everything is already pushed.

```bash
(
set -euo pipefail
OWNER="Normansrule"; REPO="ultrasonic-radar-scanner"; TAG="v5.2.0"; SSH_ALIAS="github-normansrule"
# 1. Install git, unzip, curl and the GitHub CLI (Ubuntu's gh if >= 2.40, else GitHub's official apt repo)
sudo apt-get update -y; sudo apt-get install -y git unzip curl ca-certificates; sudo apt-get install -y gh || true
if ! command -v gh >/dev/null || [ "$(printf '%s\n' 2.40.0 "$(gh --version | awk 'NR==1{print $3}')" | sort -V | head -n1)" != "2.40.0" ]; then sudo install -d -m 755 /etc/apt/keyrings; curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null; sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg; echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null; sudo apt-get update -y; sudo apt-get install -y gh; fi; gh --version | head -n1
# 2. Make sure gh is signed in as $OWNER (switches account if already added; browser sign-in otherwise)
gh auth switch -h github.com -u "$OWNER" >/dev/null 2>&1 || true
[ "$(gh api user -q .login 2>/dev/null || true)" = "$OWNER" ] || gh auth login -h github.com -p https -w -s workflow
[ "$(gh api user -q .login)" = "$OWNER" ] || { echo "gh is signed in as $(gh api user -q .login), not $OWNER - edit OWNER or sign in again"; exit 1; }
# 3. Choose the push route: your SSH alias for this account if it exists, otherwise HTTPS via gh (needs 'workflow' scope)
if grep -qsiE "^[[:space:]]*Host[[:space:]]+$SSH_ALIAS([[:space:]]|$)" ~/.ssh/config; then REMOTE="git@$SSH_ALIAS:$OWNER/$REPO.git"; export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"; else REMOTE="https://github.com/$OWNER/$REPO.git"; gh api -i user 2>/dev/null | grep -i '^x-oauth-scopes:' | grep workflow >/dev/null || gh auth refresh -h github.com -s workflow; gh auth setup-git -h github.com; fi; echo "Push route: $REMOTE"
# 4. Find the newest ZIP (Linux ~/Downloads, then Windows Downloads under WSL) and check it is this version
ZIP="$(ls -t ~/Downloads/$REPO*.zip /mnt/c/Users/*/Downloads/$REPO*.zip 2>/dev/null | head -n1 || true)"; [ -n "$ZIP" ] || { echo "No $REPO*.zip in ~/Downloads"; exit 1; }
unzip -Z1 "$ZIP" | grep -x "$REPO/manufacturing/build_packet.pdf" >/dev/null || { echo "$ZIP is an older ZIP - download the new one"; exit 1; }; echo "Using $ZIP"
# 5. Unpack into ~/projects/$REPO (overwrites files from the ZIP, keeps .git) and enter it
mkdir -p ~/projects; unzip -o -q "$ZIP" -d ~/projects; cd ~/projects/"$REPO"
# 6. Initialise Git on main (guard: never in your home folder); set a commit identity for this repo only if none is configured
[ "$PWD" = "$HOME/projects/$REPO" ] || { echo "Not in ~/projects/$REPO - stopping"; exit 1; }
[ -d .git ] || git init -q -b main
git config user.name >/dev/null || git config user.name "$(gh api user -q '.name // .login')"; git config user.email >/dev/null || git config user.email "$(gh api user -q .id)+$OWNER@users.noreply.github.com"
# 7. Commit everything (only when something changed)
git add -A; git diff --cached --quiet || git commit -q -m "Ultrasonic Radar Scanner $TAG: open-hardware package (CAD, BOM, wiring, build packet, firmware, web + desktop apps)"
# 8. Create the public repository if missing; set description, homepage and topics
gh repo view "$OWNER/$REPO" >/dev/null 2>&1 || gh repo create "$OWNER/$REPO" --public --description "Open-hardware educational ultrasonic (sonar) scanner with a radar-style display - ESP32, HC-SR04, SG90, 3D-printed, web + desktop app"
gh repo edit "$OWNER/$REPO" --homepage "https://${OWNER,,}.github.io/$REPO/" --add-topic open-hardware,esp32,ultrasonic,hc-sr04,sonar,cadquery,3d-printing,electron,education >/dev/null
# 9. Point 'origin' at the repository and push main
git remote get-url origin >/dev/null 2>&1 && git remote set-url origin "$REMOTE" || git remote add origin "$REMOTE"
git branch -M main; git push -u origin main
# 10. WEB APP: enable GitHub Pages (built by the Pages workflow, which also compiles the firmware for the flasher)
gh api -X POST "repos/$OWNER/$REPO/pages" -f build_type=workflow >/dev/null 2>&1 || gh api -X PUT "repos/$OWNER/$REPO/pages" -f build_type=workflow >/dev/null
for i in 1 2 3 4 5 6; do gh workflow run pages.yml -R "$OWNER/$REPO" --ref main >/dev/null 2>&1 && break; sleep 10; done
# 11. RELEASE: tag it; Actions builds desktop apps, firmware images and the manufacturing kit and attaches them
git rev-parse -q --verify "refs/tags/$TAG" >/dev/null || git tag -a "$TAG" -m "Ultrasonic Radar Scanner $TAG"
git push origin "refs/tags/$TAG" || echo "Tag $TAG already exists on GitHub with different contents - bump the version for a new release"
# 12. Wait for the web app (up to 5 min) and print its addresses
URL="$(gh api "repos/$OWNER/$REPO/pages" -q .html_url)"; for i in $(seq 1 30); do [ "$(curl -s -o /dev/null -w '%{http_code}' "$URL")" = "200" ] && break; sleep 10; done; echo; echo "Repository: https://github.com/$OWNER/$REPO"; echo "Web app:    $URL"; echo "Flasher:    ${URL}flash.html"; echo "Console:    ${URL}live.html"
# 13. Wait for the release (up to 40 min; Ctrl+C is safe - everything is pushed) and list the downloads
echo "Release building: https://github.com/$OWNER/$REPO/actions/workflows/release.yml"; for i in $(seq 1 80); do n="$(gh release view "$TAG" -R "$OWNER/$REPO" --json assets -q '.assets|length' 2>/dev/null || echo 0)"; [ "$n" -ge 10 ] && break; printf '.'; sleep 30; done; echo
gh release view "$TAG" -R "$OWNER/$REPO" --json assets -q '.assets[].name' 2>/dev/null | sed 's/^/  /' || echo "Release not ready yet - check the Actions link above"; echo "Release:    https://github.com/$OWNER/$REPO/releases/tag/$TAG"
)
```

If the web app is not live, open the repository's **Actions** tab, read the "Pages" run, fix and paste
again. If a release build failed, re-run it from its run page or with
`gh workflow run release.yml -R Normansrule/ultrasonic-radar-scanner -f tag=v5.2.0`.

## 2 — Keep building locally

Run this after block 1, in the same terminal or a new one. It:

* creates a Python virtual environment for the site and tests;
* runs every fast test;
* builds the web app and serves it at `http://localhost:8000`;
* installs Node.js 22 through nvm if your system Node is older (Electron 44 needs 22.12+), then the desktop app's pinned toolchain, and launches the desktop app;
* optionally compiles the firmware with the pinned ESP32 core (`BUILD_FIRMWARE=1`, about 1–2 GB to download).

```bash
(
set -euo pipefail
BUILD_FIRMWARE=0   # set to 1 to also install arduino-cli + the pinned ESP32 core and compile the firmware
# 1. Tools: Python venv support and curl (the only sudo step)
sudo apt-get update -y; sudo apt-get install -y python3-venv curl
# 1b. Node.js 22+ (Electron 44 needs >= 22.12): use the system one if new enough, else nvm in your home folder (no sudo)
NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
if [ "$NODE_MAJOR" -lt 22 ]; then export NVM_DIR="$HOME/.nvm"; [ -s "$NVM_DIR/nvm.sh" ] || curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.8/install.sh | bash; set +u; . "$NVM_DIR/nvm.sh"; nvm install 22 >/dev/null; nvm use 22 >/dev/null; set -u; fi; echo "Node $(node -v), npm $(npm -v)"
# 2. Enter the project
cd ~/projects/ultrasonic-radar-scanner
# 3. Python environment for the site, generators and tests (CAD regeneration needs Python 3.11 - see README)
[ -x .venv/bin/python ] || python3 -m venv .venv; .venv/bin/python -m pip install -q --upgrade pip; .venv/bin/python -m pip install -q -r requirements-site.txt
# 4. Fast checks: equations, wiring/firmware sync, BOM, CAD report, app hardening, live-console parser
.venv/bin/python -m pytest -q tests; node --test tests/js/*.test.js
# 5. Build the web app (site/) and the desktop app's offline bundle (app/web/)
.venv/bin/python scripts/build_site.py; (cd app; npm ci --no-audit --no-fund; [ -f node_modules/electron/path.txt ] || node node_modules/electron/install.js; ../.venv/bin/python ../scripts/build_site.py --app --out web)
# 6. Optional: compile the firmware exactly as pinned in firmware/Radar_V5/sketch.yaml
if [ "$BUILD_FIRMWARE" = 1 ]; then mkdir -p ~/.local/bin; command -v arduino-cli >/dev/null || curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR="$HOME/.local/bin" sh; PATH="$HOME/.local/bin:$PATH" arduino-cli compile --profile esp32-core3 --warnings all firmware/Radar_V5; fi
# 7. Serve the web app in the background (http://localhost:8000) and open the desktop app (close its window to finish)
(.venv/bin/python -m http.server 8000 -d site >/dev/null 2>&1 &) ; echo "Web app: http://localhost:8000   (stop later with: pkill -f 'http.server 8000')"
cd app; npx electron . || npx electron . --no-sandbox
)
```

* WSL: the desktop window opens through WSLg (Windows 11). The live console's serial link needs the
  **Windows** build of the app (or Chrome/Edge on Windows), because USB serial ports are not passed
  into WSL by default.
* Ubuntu 24.04+ on a real machine: if Electron exits with a sandbox message, the block retries with
  `--no-sandbox` (Ubuntu's AppArmor blocks Chromium's sandbox for apps run from a home folder). The
  same applies to the AppImage.
* Regenerating CAD (`scripts/render_cad.py`, `render_previews.py`) needs `requirements.txt`, which pins
  CadQuery for **Python 3.11**. If your Ubuntu ships a newer Python, make a 3.11 environment, for
  example `conda create -n radar python=3.11`, then `pip install -r requirements.txt`.

## Making the next release

1. Change the code and docs. Run the block-2 checks.
2. Bump `"version"` in `app/package.json` and add a matching `## x.y.z` entry at the top of `CHANGELOG.md`
   (a test enforces both).
3. `git commit -am "…" && git push && git tag -a vX.Y.Z -m "…" && git push origin vX.Y.Z`

The Release workflow refuses a tag that does not match `app/package.json`.

## After the first publish

* **Protect `main`:** Settings → Branches → require the `CI` checks.
* **Private vulnerability reporting:** Settings → Code security → enable it (see [`SECURITY.md`](SECURITY.md)).
* **Live link:** wire the optional telemetry tap before connecting real hardware ([`LIVE_LINK.md`](LIVE_LINK.md)).
