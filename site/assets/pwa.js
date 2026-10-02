// Installable web app support. Registers the service worker (offline copy of the
// guide, simulator and live console) and wires the optional "Install app" button.
// Does nothing inside the desktop app (file:// pages) or on unsupported browsers.
(function () {
  "use strict";
  const me = document.currentScript;
  const root = (me && me.dataset.root) || "";
  if (!/^https?:$/.test(location.protocol) || !("serviceWorker" in navigator)) return;
  window.addEventListener("load", () => {
    navigator.serviceWorker.register(root + "sw.js", { scope: root || "./" }).catch(() => {});
  });
  let deferred = null;
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferred = e;
    const b = document.getElementById("b-install");
    if (b) b.hidden = false;
  });
  document.addEventListener("click", async (e) => {
    if (!e.target || e.target.id !== "b-install" || !deferred) return;
    deferred.prompt();
    await deferred.userChoice.catch(() => {});
    deferred = null;
    e.target.hidden = true;
  });
})();
