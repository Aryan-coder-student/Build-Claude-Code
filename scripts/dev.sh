#!/usr/bin/env bash
# Start backend (8000), dashboard (3001), and demo product (3000) locally. Ctrl-C stops all.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
[ -d backend/.venv ] || (cd backend && uv venv .venv && uv pip install --python .venv/bin/python -e ".[dev]" && .venv/bin/playwright install chromium)
[ -d frontend/node_modules ] || (cd frontend && npm install)
[ -d demo-product/node_modules ] || (cd demo-product && npm install)
trap 'kill 0' EXIT
(cd backend && .venv/bin/uvicorn app.main:app --port 8000 --reload) &
(cd frontend && npm run dev) &
(cd demo-product && npm run dev) &
echo "Backend  http://localhost:8000   Dashboard http://localhost:3001   Demo SaaS http://localhost:3000"
wait
