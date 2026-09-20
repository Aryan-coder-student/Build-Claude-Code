/* Chat app running inside the widget iframe. Talks REST to the backend (same origin) and
 * asks the parent page (widget.js) to execute typed actions via postMessage. */
(function () {
  var params = new URLSearchParams(location.search);
  var productId = params.get("product_id"), sessionId = params.get("session_id"), hostOrigin = params.get("host"), hostPath = params.get("path") || "";
  var runKey = "demo-agent:run:" + productId; // active demo run, so a full page load (multi-page apps) can resume it
  var $ = function (id) { return document.getElementById(id); };
  var messagesEl = $("messages"), suggestionsEl = $("suggestions"), input = $("input"), sendBtn = $("send");
  var demo = { runId: null, stopped: false };
  var pendingActions = {};

  /* ---------- rendering ---------- */
  function addMessage(role, text, cls) {
    var wrap = document.createElement("div"); wrap.className = "msg " + role + (cls ? " " + cls : "");
    var who = document.createElement("div"); who.className = "who"; who.textContent = role === "user" ? "You" : "AI";
    var bubble = document.createElement("div"); bubble.className = "bubble"; bubble.textContent = text;
    wrap.appendChild(who); wrap.appendChild(bubble); messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return wrap;
  }
  function setSuggestions(list) {
    suggestionsEl.innerHTML = "";
    (list || []).slice(0, 4).forEach(function (s) {
      var chip = document.createElement("button"); chip.className = "chip"; chip.type = "button"; chip.textContent = s;
      chip.addEventListener("click", function () { send(s); });
      suggestionsEl.appendChild(chip);
    });
  }
  function setBusy(busy) { sendBtn.disabled = busy; }

  /* ---------- API ---------- */
  function api(path, opts) {
    return fetch(path, Object.assign({ headers: { "content-type": "application/json" } }, opts || {})).then(function (r) {
      if (!r.ok) return r.text().then(function (t) { throw new Error(t || r.statusText); });
      return r.json();
    });
  }

  function send(text) {
    text = (text || input.value).trim();
    if (!text) return;
    input.value = "";
    addMessage("user", text);
    setSuggestions([]);
    setBusy(true);
    var typing = addMessage("assistant", "…", "typing");
    api("/api/widget/chat", { method: "POST", body: JSON.stringify({ product_id: productId, session_id: sessionId, message: text }) })
      .then(function (res) {
        typing.remove();
        addMessage("assistant", res.reply);
        setSuggestions(res.suggestions);
        if (res.demo_run) runDemo(res.demo_run);
      })
      .catch(function (err) { typing.remove(); addMessage("assistant", "Sorry, something went wrong: " + err.message); })
      .then(function () { setBusy(false); input.focus(); });
  }

  /* ---------- demo execution loop (one step at a time) ---------- */
  function hostExecute(action) {
    return new Promise(function (resolve) {
      var id = Math.random().toString(36).slice(2);
      var timer = setTimeout(function () { delete pendingActions[id]; resolve({ ok: false, error: "the page did not respond in time" }); }, 10000);
      pendingActions[id] = function (result) { clearTimeout(timer); resolve(result); };
      parent.postMessage({ type: "demo-agent:action", id: id, action: action }, hostOrigin);
    });
  }
  addEventListener("message", function (event) {
    var msg = event.data;
    if (event.origin !== hostOrigin || !msg || msg.type !== "demo-agent:result") return;
    var cb = pendingActions[msg.id]; if (cb) { delete pendingActions[msg.id]; cb({ ok: msg.ok, error: msg.error || "" }); }
  });

  function showDemoPanel(run) {
    $("demo-title").textContent = run.title; $("demo-step").textContent = "Step 1 / " + run.total_steps;
    $("demo-message").textContent = "Starting…"; $("demo-bar").style.width = "0%"; $("demo").classList.remove("hidden");
  }
  function hideDemoPanel() { $("demo").classList.add("hidden"); parent.postMessage({ type: "demo-agent:clear" }, hostOrigin); }

  function rememberRun(run, action) {
    // A navigate step may trigger a full page load on non-SPA hosts; remember where we expect to land.
    var expect = action && action.type === "navigate" ? new URL(action.path, hostOrigin).pathname : null;
    localStorage.setItem(runKey, JSON.stringify({ run: run, expectPath: expect }));
  }
  function forgetRun() { localStorage.removeItem(runKey); }

  function runDemo(run, initialResult) {
    demo.runId = run.id; demo.stopped = false;
    if (run.total_steps > 1) showDemoPanel(run);
    var advance = function (result) {
      if (demo.stopped || demo.runId !== run.id) return;
      api("/api/demo/runs/" + run.id + "/advance", { method: "POST", body: JSON.stringify({ result: result }) }).then(function (step) {
        if (demo.stopped || demo.runId !== run.id) return;
        if (step.done) {
          forgetRun();
          if (step.message) addMessage("assistant", step.message);
          if (run.total_steps > 1) setTimeout(hideDemoPanel, 1500); else parent.postMessage({ type: "demo-agent:clear" }, hostOrigin);
          demo.runId = null; return;
        }
        rememberRun(run, step.action);
        $("demo-step").textContent = "Step " + (step.step_index + 1) + " / " + step.total_steps;
        $("demo-message").textContent = step.message || "";
        $("demo-bar").style.width = Math.round((step.step_index / step.total_steps) * 100) + "%";
        if (step.action.type === "explain" && step.action.message) addMessage("assistant", step.action.message, "step");
        hostExecute(step.action).then(advance);
      }).catch(function (err) { forgetRun(); addMessage("assistant", "The demo stopped: " + err.message); hideDemoPanel(); demo.runId = null; });
    };
    advance(initialResult || null);
  }

  function resumeRunAfterReload() {
    var saved = null;
    try { saved = JSON.parse(localStorage.getItem(runKey) || "null"); } catch (e) { saved = null; }
    if (!saved) return;
    forgetRun();
    if (saved.expectPath && saved.expectPath !== hostPath) return; // the reload was not our navigation; drop the run
    runDemo(saved.run, { ok: true }); // the pending navigate step succeeded: the page we expected is now loaded
  }
  $("demo-stop").addEventListener("click", function () {
    if (!demo.runId) return;
    demo.stopped = true; forgetRun();
    api("/api/demo/runs/" + demo.runId + "/stop", { method: "POST", body: "{}" }).then(function () {
      addMessage("assistant", "Demo stopped. Ask me anything else whenever you're ready.");
    }).catch(function () {});
    hideDemoPanel(); demo.runId = null;
  });

  /* ---------- boot ---------- */
  $("composer").addEventListener("submit", function (e) { e.preventDefault(); send(); });
  $("close").addEventListener("click", function () { parent.postMessage({ type: "demo-agent:close" }, hostOrigin); });

  api("/api/widget/config?product_id=" + encodeURIComponent(productId)).then(function (cfg) {
    $("title").textContent = cfg.product_name + " Assistant";
    if (!cfg.ready) $("subtitle").textContent = "Still learning this product (" + cfg.status.toLowerCase().replace(/_/g, " ") + ")…";
    return api("/api/widget/sessions/" + encodeURIComponent(sessionId) + "/messages?product_id=" + encodeURIComponent(productId)).then(function (history) {
      if (!history.length) {
        addMessage("assistant", "Hi! I'm the " + cfg.product_name + " assistant. Ask me about the product, tell me where to go, or ask me to show you how something works.");
        setSuggestions(cfg.suggestions);
      } else {
        history.forEach(function (m) { addMessage(m.role, m.content, m.meta && m.meta.event === "explain" ? "step" : ""); });
        var last = history[history.length - 1];
        if (last.meta && last.meta.suggestions) setSuggestions(last.meta.suggestions);
      }
      resumeRunAfterReload();
    });
  }).catch(function (err) {
    addMessage("assistant", "This product isn't registered yet. " + err.message);
  });
})();
