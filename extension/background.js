// Strips Content-Security-Policy / X-Frame-Options on the configured sites so the widget script,
// its iframe, and its API calls are allowed. Dev/demo tool: the real integration is the one-line snippet.
importScripts("config.js");

function rulesFromConfig() {
  return Object.keys(DEMO_AGENT_CONFIG.sites).map(function (host, i) {
    return {
      id: i + 1,
      priority: 1,
      action: {
        type: "modifyHeaders",
        responseHeaders: [
          { header: "content-security-policy", operation: "remove" },
          { header: "content-security-policy-report-only", operation: "remove" },
          { header: "x-frame-options", operation: "remove" }
        ]
      },
      condition: { urlFilter: "||" + host, resourceTypes: ["main_frame", "sub_frame"] }
    };
  });
}

async function applyRules() {
  const existing = await chrome.declarativeNetRequest.getDynamicRules();
  await chrome.declarativeNetRequest.updateDynamicRules({ removeRuleIds: existing.map((r) => r.id), addRules: rulesFromConfig() });
}

chrome.runtime.onInstalled.addListener(applyRules);
chrome.runtime.onStartup.addListener(applyRules);
