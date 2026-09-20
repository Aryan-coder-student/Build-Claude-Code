# AI Interactive Product Demo Sales Agent — Project Instructions

6-hour hackathon project. Goal: a convincing, reliable, end-to-end local demo.
Project agent: `claude --agent demo-sales-builder` (see `.claude/agents/demo-sales-builder.md`).

## Purpose

A SaaS company drops one script tag into its product. Our backend crawls the product,
builds a tenant-isolated knowledge base (pages, features, navigation, Q&A, demo flows), and an
embedded chatbot acts as an AI sales engineer: it answers questions, navigates the live product,
and runs interactive demos that drive the host UI while the conversation stays alive.

## Repository map

```
.claude/agents/demo-sales-builder.md  project engineering agent
docs/            PRD, ARCHITECTURE, IMPLEMENTATION_PLAN, PROGRESS
backend/         FastAPI + SQLite + Playwright worker + chat agent + widget static files (port 8000)
frontend/        Dashboard: Vite + React + TypeScript + Tailwind (port 3001)
demo-product/    Example SaaS ("Demo SaaS"): Vite + React SPA with data-testid selectors (port 3000)
scripts/         dev.sh (run everything), e2e.sh (full local end-to-end check)
```

## Architecture principles

- One FastAPI backend. In-process background worker (thread pool). No microservices, no Redis/Celery.
- SQLite via SQLAlchemy; schema written so PostgreSQL can replace it (string ids, JSON text columns).
- Multi-tenant: every product-scoped row carries `tenant_id` and `product_id`; repository
  functions take both explicitly and filter on both. Dashboard identifies the tenant via the
  `X-Tenant-Id` header (default `ten_demo`). Widget endpoints are keyed by `product_id` and resolve
  the tenant from the product.
- Structured knowledge, not just scraped text: pages → features → elements/selectors → navigation
  graph → Q&A → demo flows → knowledge chunks. Retrieval = structured lookup + token-overlap text search.
- LLM (Claude via `anthropic` SDK, model `claude-opus-5`) is an **enrichment layer** behind
  `backend/app/agent/llm.py`. Every LLM use has a deterministic fallback; the demo must work with no API key.
- Widget = `widget.js` (host bridge, floating button, iframe) + chat app in the iframe, both served
  by the backend. Bridge and iframe communicate with `postMessage` using typed actions only.
- Demo execution is a pull loop: chat starts a `demo_run`; the iframe asks the backend for the next
  step, executes it through the bridge, reports the result, and repeats. Navigation requests are
  one-step demo runs (same code path).

## Coding rules

- Readable, minimal abstraction. No factories, generic frameworks, or speculative layers.
- Typed models at boundaries (Pydantic schemas in the backend, TypeScript types in frontends).
- Never execute arbitrary LLM-generated JavaScript in the host page. Typed actions + CSS selectors only.
- Prefer `data-testid` selectors everywhere in `demo-product/` and in generated demo steps.
- Log worker stages and demo execution (`logging` in Python, `console.debug` in the widget).
- Fail gracefully with human-readable messages (e.g., selector not found → explain, stop the demo).
- Keep files under ~500 lines; split when a module grows.

## Testing rules

- Backend: `pytest` in `backend/` (tenant isolation, intent classification, pipeline on fixture
  crawl data, demo-run sequencing). Run after meaningful backend changes.
- Frontends: `npm run typecheck` (tsc) and `npm run build` must pass.
- `scripts/e2e.sh` boots everything, registers the demo product, waits for READY, and checks the
  chat/navigation/demo endpoints. Run before claiming an end-to-end milestone.
- Never weaken a test to make it pass. Fix the code.

## Priority order (when choosing what to build or fix)

1. Live navigation and interactive demo working in the demo SaaS with the chat alive.
2. Worker pipeline producing correct features/demo flows for the demo SaaS, with visible progress.
3. Chat answers from discovered knowledge.
4. Dashboard showing status and knowledge.
5. Polish.

## Commands

```
docker compose up --build           # preferred: whole stack (backend 8000, dashboard 3001, demo product 3000)
docker compose down -v              # reset (also required after schema changes: SQLite tables are create_all only)
scripts/dev.sh                      # local dev alternative: same three servers without Docker
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000
cd backend && .venv/bin/pytest -q
cd frontend && npm run dev          # dashboard on http://localhost:3001
cd demo-product && npm run dev      # demo SaaS on http://localhost:3000
scripts/e2e.sh                      # API-level end-to-end check against running servers
cd backend && DEMO_SALES_LIVE=1 .venv/bin/pytest -q tests/test_e2e_live.py   # real-browser widget/navigation/demo test
```

Docker note: `docker` needs the user in the `docker` group (`sg docker -c "docker compose ..."` in a fresh shell).

Environment: `.env` holds `ANTHROPIC_API_KEY` (+ `ANTHROPIC_WORKSPACE_ID` for non-workspace-scoped keys); Docker Compose reads it. Never commit it. Backend settings in
`backend/app/config.py` (`DEMO_SALES_*` env vars).

## Definition of done (MVP)

- [x] Project-level Claude agent exists
- [x] Demo SaaS exists
- [x] Dashboard exists
- [x] Backend exists
- [x] Multi-tenant schema exists
- [x] Product can be registered
- [x] Worker automatically starts
- [x] Pages are discovered
- [x] Features are extracted
- [x] Product knowledge is stored
- [x] Q&A works
- [x] Embeddable widget loads
- [x] Chatbot answers product questions
- [x] Chatbot can navigate the host product
- [x] Chat remains alive during SPA navigation
- [x] Interactive demo executes structured actions
- [x] At least one complete feature demo works reliably
- [x] Worker/indexing status appears in dashboard
- [x] Entire demo can run locally

`docs/PROGRESS.md` tracks the current state; the code is the source of truth.
