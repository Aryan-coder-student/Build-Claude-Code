// Injects widget.js into configured sites, exactly like the <script> snippet would.
(function () {
  var productId = DEMO_AGENT_CONFIG.sites[location.host];
  if (!productId || document.querySelector("script[data-product-id]")) return;
  var s = document.createElement("script");
  s.src = DEMO_AGENT_CONFIG.backend + "/widget.js";
  s.setAttribute("data-product-id", productId);
  (document.body || document.documentElement).appendChild(s);
})();
