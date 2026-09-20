#!/usr/bin/env bash
# Expose the whole stack publicly with Cloudflare quick tunnels (no account needed).
# Starts a tunnel for the backend first, rewires the stack to that public URL, then tunnels the demo product and dashboard.
# Usage: scripts/tunnel.sh            (Ctrl-C stops the tunnels; run `scripts/tunnel.sh down` to restore localhost URLs)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
DOCKER="docker"; docker ps >/dev/null 2>&1 || DOCKER="sg docker -c docker"
compose() { if [ "$DOCKER" = docker ]; then docker compose "$@"; else sg docker -c "docker compose $*"; fi; }
LOGDIR=/tmp/demo-sales-tunnels; mkdir -p "$LOGDIR"

set_env() { # set_env KEY VALUE  (idempotent edit of .env)
  touch .env; grep -q "^$1=" .env && sed -i "s#^$1=.*#$1=$2#" .env || echo "$1=$2" >> .env
}
start_tunnel() { # start_tunnel NAME PORT -> prints public URL
  pkill -f "cloudflared tunnel --url http://localhost:$2" 2>/dev/null || true
  nohup cloudflared tunnel --url "http://localhost:$2" > "$LOGDIR/$1.log" 2>&1 &
  for _ in $(seq 1 40); do
    url=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$LOGDIR/$1.log" | head -1); [ -n "$url" ] && { echo "$url"; return; }; sleep 1
  done
  echo "failed to start tunnel for $1 (see $LOGDIR/$1.log)" >&2; exit 1
}

if [ "${1:-}" = "down" ]; then
  pkill -f "cloudflared tunnel --url" 2>/dev/null || true
  set_env PUBLIC_BACKEND_URL http://localhost:8000
  compose up -d backend demo-product frontend >/dev/null
  echo "tunnels stopped; stack back on http://localhost:8000 / :3000 / :3001"; exit 0
fi

BACKEND_URL=$(start_tunnel backend 8000)
set_env PUBLIC_BACKEND_URL "$BACKEND_URL"
compose up -d --build backend demo-product frontend >/dev/null   # re-create (and rebuild) with the public backend URL
for _ in $(seq 1 60); do curl -sf localhost:8000/health >/dev/null && break; sleep 1; done
DEMO_URL=$(start_tunnel demo-product 3000)
DASH_URL=$(start_tunnel frontend 3001)
for _ in $(seq 1 30); do curl -sf -o /dev/null "$BACKEND_URL/widget.js" && break; sleep 2; done

cat <<MSG

  Public URLs (Cloudflare quick tunnels — they change on every start):

    Demo SaaS   $DEMO_URL
    Dashboard   $DASH_URL
    Backend     $BACKEND_URL      (widget: $BACKEND_URL/widget.js)

  Snippet for any product:  <script src="$BACKEND_URL/widget.js" data-product-id="prod_x"></script>
  Logs: $LOGDIR   ·   Stop + restore localhost: scripts/tunnel.sh down

MSG
