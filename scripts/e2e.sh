#!/usr/bin/env bash
# End-to-end check against running servers: register the demo product, wait for READY, exercise chat/navigation/demo.
# Usage: scripts/e2e.sh [backend_url] [demo_url]
set -euo pipefail
API="${1:-http://localhost:8000}"
DEMO="${2:-http://localhost:3000}"
TENANT="ten_e2e_$(date +%s)"
PID="prod_e2e_$(date +%s)"
hdr=(-H "content-type: application/json" -H "X-Tenant-Id: $TENANT")

echo "▶ registering $PID for $DEMO"
curl -sf -X POST "$API/api/products" "${hdr[@]}" -d "{\"name\":\"Demo SaaS\",\"url\":\"$DEMO\",\"id\":\"$PID\"}" > /dev/null

for i in $(seq 1 60); do
  status=$(curl -sf "$API/api/products/$PID/job" "${hdr[@]}" | python3 -c 'import json,sys; j=json.load(sys.stdin); print(j["status"], j["stage"], j["stats"])')
  echo "  $status"
  case "$status" in DONE*) break;; FAILED*) echo "✗ indexing failed"; exit 1;; esac
  sleep 2
done
[[ "$status" == DONE* ]] || { echo "✗ timed out"; exit 1; }

chat() { curl -sf -X POST "$API/api/widget/chat" -H "content-type: application/json" -d "{\"product_id\":\"$PID\",\"session_id\":\"sess_e2e\",\"message\":\"$1\"}"; }
py() { python3 -c "import json,sys; d=json.load(sys.stdin); $1"; }

echo "▶ Q&A";        chat "What analytics features do you have?" | py 'assert d["intent"]=="FEATURE_QA" and "analytics" in d["reply"].lower(), d; print("  ", d["reply"][:100])'
echo "▶ navigation"; run=$(chat "Take me to analytics." | py 'assert d["intent"]=="NAVIGATION_REQUEST", d; print(d["demo_run"]["id"])')
curl -sf -X POST "$API/api/demo/runs/$run/advance" -H "content-type: application/json" -d '{"result":null}' | py 'assert d["action"]["type"]=="navigate" and d["action"]["path"]=="/analytics", d; print("   navigate ->", d["action"]["path"])'
echo "▶ demo";       run=$(chat "Show me how to create a report." | py 'assert d["intent"]=="DEMO_REQUEST" and d["demo_run"]["total_steps"]>=6, d; print(d["demo_run"]["id"])')
result='{"result":null}'; steps=0
while :; do
  out=$(curl -sf -X POST "$API/api/demo/runs/$run/advance" -H "content-type: application/json" -d "$result")
  echo "$out" | py 'a=d.get("action") or {}; print("   ", "done" if d["done"] else "step %d/%d %s %s" % (d["step_index"]+1, d["total_steps"], a["type"], a.get("selector") or a.get("path") or ""))'
  echo "$out" | grep -q '"done":true' && break
  result='{"result":{"ok":true}}'; steps=$((steps+1))
done
echo "▶ follow-up";  chat "Can I also share reports?" | py 'assert d["reply"]; print("  ", d["reply"][:100])'
curl -sf "$API/api/widget/sessions/sess_e2e/messages?product_id=$PID" | py 'assert len(d)>=6, len(d); print("   history messages:", len(d))'
echo "✓ e2e passed ($steps demo steps executed)"
