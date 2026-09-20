/* AI Product Demo Sales Agent — embeddable widget + host page bridge.
 * Usage: <script src="http://localhost:8000/widget.js" data-product-id="prod_x"></script>
 * The chat UI runs inside an iframe; this file only (1) injects the launcher + iframe and
 * (2) executes typed actions (navigate/click/highlight/scroll/type/wait/explain) requested by the iframe.
 * No code from the server or the LLM is ever evaluated here. */
(function () {
  if (window.__demoAgentLoaded) return;
  window.__demoAgentLoaded = true;

  var script = document.currentScript || Array.prototype.slice.call(document.querySelectorAll("script[data-product-id]")).pop();
  var productId = script && script.getAttribute("data-product-id");
  if (!productId) { console.warn("[demo-agent] missing data-product-id"); return; }
  var origin = new URL(script.src, location.href).origin;
  var storageKey = "demo-agent:session:" + productId;
  var sessionId = localStorage.getItem(storageKey);
  if (!sessionId) { sessionId = "sess_" + Math.random().toString(36).slice(2, 12); localStorage.setItem(storageKey, sessionId); }
  var openKey = "demo-agent:open:" + productId;
  var log = function () { console.debug.apply(console, ["[demo-agent]"].concat(Array.prototype.slice.call(arguments))); };

  /* ---------- UI: launcher + iframe (both marked data-demo-agent so the crawler ignores them) ---------- */
  // Inline styles (not a stylesheet) so host CSS such as Bootstrap/Tailwind resets cannot override the widget's layout.
  var Z = 2147483000;
  var LAUNCHER_CSS = "position:fixed;right:24px;bottom:24px;width:56px;height:56px;margin:0;padding:0;border-radius:50%;border:0;background:#4f46e5;color:#fff;box-shadow:0 10px 30px rgba(79,70,229,.4);cursor:pointer;z-index:" + Z + ";display:flex;align-items:center;justify-content:center;line-height:0;transition:transform .15s;font-family:system-ui,sans-serif;";
  var FRAME_CSS = "position:fixed;right:24px;bottom:92px;width:380px;max-width:calc(100vw - 32px);height:600px;max-height:calc(100vh - 120px);margin:0;padding:0;border:0;border-radius:16px;box-shadow:0 20px 60px rgba(15,23,42,.25);z-index:" + Z + ";background:#fff;display:none;";
  var HIGHLIGHT_CSS = "position:absolute;border:3px solid #6366f1;border-radius:10px;box-shadow:0 0 0 6px rgba(99,102,241,.25),0 0 0 9999px rgba(15,23,42,.18);pointer-events:none;z-index:" + (Z - 1000) + ";transition:all .25s ease;animation:da-pulse 1.4s ease-in-out infinite;";
  var TIP_CSS = "position:absolute;max-width:280px;background:#111827;color:#fff;font:13px/1.45 system-ui,sans-serif;padding:10px 12px;border-radius:10px;z-index:" + (Z - 999) + ";pointer-events:none;box-shadow:0 8px 24px rgba(0,0,0,.25);";
  var root = document.createElement("div");
  root.setAttribute("data-demo-agent", "root");
  root.style.cssText = "all:initial;position:static;";
  var style = document.createElement("style");
  style.textContent = "@keyframes da-pulse{0%,100%{box-shadow:0 0 0 6px rgba(99,102,241,.25),0 0 0 9999px rgba(15,23,42,.18)}50%{box-shadow:0 0 0 12px rgba(99,102,241,.12),0 0 0 9999px rgba(15,23,42,.18)}}";
  var launcher = document.createElement("button");
  launcher.setAttribute("data-demo-agent", "launcher"); launcher.setAttribute("aria-label", "Open product assistant"); launcher.type = "button";
  launcher.style.cssText = LAUNCHER_CSS;
  launcher.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a8 8 0 0 1-8 8H7l-4 3v-6a8 8 0 0 1 0-1V12a8 8 0 0 1 8-8h2a8 8 0 0 1 8 8z"/></svg>';
  var frame = document.createElement("iframe");
  frame.setAttribute("data-demo-agent", "frame"); frame.title = "Product assistant";
  frame.style.cssText = FRAME_CSS;
  root.appendChild(style); root.appendChild(launcher); root.appendChild(frame);
  frame.src = origin + "/widget/chat?product_id=" + encodeURIComponent(productId) + "&session_id=" + encodeURIComponent(sessionId) + "&host=" + encodeURIComponent(location.origin) + "&path=" + encodeURIComponent(location.pathname);
  var setOpen = function (open) { frame.style.display = open ? "block" : "none"; sessionStorage.setItem(openKey, open ? "1" : "0"); };
  launcher.addEventListener("click", function () { setOpen(frame.style.display !== "block"); });
  var mount = function () { document.body.appendChild(root); if (sessionStorage.getItem(openKey) === "1") setOpen(true); };
  if (document.body) mount(); else document.addEventListener("DOMContentLoaded", mount);

  /* ---------- Highlight overlay ---------- */
  var overlay = null, tip = null, overlayTarget = null;
  function clearHighlight() {
    if (overlay) overlay.remove(); if (tip) tip.remove();
    overlay = tip = overlayTarget = null;
  }
  function positionOverlay() {
    if (!overlay || !overlayTarget) return;
    var r = overlayTarget.getBoundingClientRect(), pad = 6;
    overlay.style.left = (r.left + scrollX - pad) + "px"; overlay.style.top = (r.top + scrollY - pad) + "px";
    overlay.style.width = (r.width + pad * 2) + "px"; overlay.style.height = (r.height + pad * 2) + "px";
    if (tip) {
      var below = r.bottom + 16 + tip.offsetHeight < innerHeight;
      tip.style.left = Math.max(12, Math.min(r.left + scrollX, innerWidth - tip.offsetWidth - 12)) + "px";
      tip.style.top = (below ? r.bottom + scrollY + 14 : r.top + scrollY - tip.offsetHeight - 14) + "px";
    }
  }
  function highlight(el, message) {
    clearHighlight();
    overlayTarget = el;
    overlay = document.createElement("div"); overlay.style.cssText = HIGHLIGHT_CSS; overlay.setAttribute("data-demo-agent", "highlight");
    root.appendChild(overlay);
    if (message) { tip = document.createElement("div"); tip.style.cssText = TIP_CSS; tip.setAttribute("data-demo-agent", "tip"); tip.textContent = message; root.appendChild(tip); }
    positionOverlay();
  }
  addEventListener("scroll", positionOverlay, true); addEventListener("resize", positionOverlay);

  /* ---------- Action executor ---------- */
  var sleep = function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); };
  function waitFor(selector, timeoutMs) {
    var deadline = Date.now() + (timeoutMs || 3000);
    return new Promise(function (resolve, reject) {
      (function poll() {
        var el = null;
        try { el = document.querySelector(selector); } catch (e) { return reject(new Error("invalid selector: " + selector)); }
        if (el && el.closest && el.closest("[data-demo-agent]")) el = null;
        if (el) return resolve(el);
        if (Date.now() > deadline) return reject(new Error("element not found: " + selector));
        setTimeout(poll, 120);
      })();
    });
  }
  function navigate(path) {
    var target = new URL(path, location.origin);
    if (target.origin !== location.origin) throw new Error("cross-origin navigation is not allowed");
    if (location.pathname === target.pathname) return Promise.resolve();
    var fingerprint = function () { return document.title + "|" + (document.body.innerText || "").length; };
    var before = fingerprint();
    // 1) Prefer the app's own link for this path: the framework router handles it exactly like a user click.
    var link = Array.prototype.find.call(document.querySelectorAll("a[href]"), function (a) {
      if (a.closest("[data-demo-agent]")) return false;
      try { return new URL(a.getAttribute("href"), location.href).pathname === target.pathname; } catch (e) { return false; }
    });
    if (link) {
      link.click();
    } else {
      // 2) Otherwise push a router-compatible history state (Vue Router keeps position/current in history.state;
      //    an empty state would break its later pushes) and announce it with popstate.
      var prev = history.state || {};
      var state = Object.assign({}, prev, { current: target.pathname + target.search, back: location.pathname + location.search, forward: null,
        position: typeof prev.position === "number" ? prev.position + 1 : 1, replaced: false, scroll: null });
      history.pushState(state, "", target.pathname + target.search);
      dispatchEvent(new PopStateEvent("popstate", { state: state }));
    }
    return sleep(600).then(function () {
      // Non-SPA host: nothing reacted -> fall back to a full load (session persists in localStorage).
      if (location.pathname !== target.pathname || fingerprint() === before) location.assign(target.href);
    });
  }
  function setValue(el, value) {
    el.focus();
    var proto = el.tagName === "SELECT" ? HTMLSelectElement.prototype : el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    var setter = Object.getOwnPropertyDescriptor(proto, "value").set; // works with React's controlled inputs
    setter.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true })); el.dispatchEvent(new Event("change", { bubbles: true }));
  }
  function typeInto(el, value) {
    var i = 0; setValue(el, "");
    return new Promise(function (resolve) {
      (function tick() { i++; setValue(el, value.slice(0, i)); if (i < value.length) setTimeout(tick, 45); else resolve(); })();
    });
  }
  var handlers = {
    navigate: function (a) { clearHighlight(); return navigate(a.path); },
    click: function (a) { return waitFor(a.selector).then(function (el) { el.scrollIntoView({ block: "center", behavior: "smooth" }); highlight(el); return sleep(350); }).then(function () { document.querySelector(a.selector).click(); clearHighlight(); return sleep(300); }); },
    highlight: function (a) { return waitFor(a.selector).then(function (el) { el.scrollIntoView({ block: "center", behavior: "smooth" }); highlight(el, a.message); return sleep(Math.min(2600, 900 + (a.message || "").length * 28)); }); },
    scroll: function (a) { return waitFor(a.selector).then(function (el) { el.scrollIntoView({ block: "center", behavior: "smooth" }); return sleep(500); }); },
    type: function (a) { return waitFor(a.selector).then(function (el) { highlight(el); return typeInto(el, a.value || ""); }).then(function () { return sleep(500); }); },
    wait: function (a) { return sleep(a.ms || 500); },
    explain: function () { return sleep(300); },
  };
  var queue = Promise.resolve(); // actions run strictly one after another, even across overlapping runs
  function execute(action) {
    var handler = handlers[action && action.type];
    if (!handler) return Promise.reject(new Error("unsupported action: " + (action && action.type)));
    var run = queue.then(function () { log("action", action); return handler(action); });
    queue = run.catch(function () {});
    return run;
  }

  /* ---------- Bridge: iframe <-> host ---------- */
  addEventListener("message", function (event) {
    if (event.origin !== origin || !event.data || typeof event.data.type !== "string") return;
    var msg = event.data;
    if (msg.type === "demo-agent:action") {
      execute(msg.action).then(
        function () { frame.contentWindow.postMessage({ type: "demo-agent:result", id: msg.id, ok: true }, origin); },
        function (err) { log("action failed", err); frame.contentWindow.postMessage({ type: "demo-agent:result", id: msg.id, ok: false, error: String(err && err.message || err) }, origin); }
      );
    } else if (msg.type === "demo-agent:clear") {
      clearHighlight();
    } else if (msg.type === "demo-agent:close") {
      setOpen(false);
    }
  });

  window.DemoAgent = { navigate: function (p) { return execute({ type: "navigate", path: p }); }, click: function (s) { return execute({ type: "click", selector: s }); },
    highlight: function (s, m) { return execute({ type: "highlight", selector: s, message: m }); }, scroll: function (s) { return execute({ type: "scroll", selector: s }); },
    type: function (s, v) { return execute({ type: "type", selector: s, value: v }); }, wait: function (ms) { return execute({ type: "wait", ms: ms }); }, clear: clearHighlight, open: function () { setOpen(true); } };
})();
