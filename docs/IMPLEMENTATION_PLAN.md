# Implementation Plan

Status legend: TODO · IN PROGRESS · DONE

## Phase 0 — Claude agent + project setup

**Goal:** Claude agent + project setup.

**Tasks:** `.claude/agents/demo-sales-builder.md`, `CLAUDE.md`, docs, scaffolds for backend/frontend/demo-product

**Files:** Agent file, CLAUDE.md, 4 docs, manifests

**API changes:** —

**Database changes:** —

**Acceptance criteria:** `claude --agent demo-sales-builder` loads; docs exist; installs succeed

**Status:** DONE

## Phase 1 — Demo SaaS application

**Goal:** Demo SaaS application.

**Tasks:** Vite React SPA with Dashboard, Projects, Analytics (Overview, Reports), Team (Members, Invite), Billing; sidebar nav with data-testid; New Report form; Invite form; widget snippet in index.html

**Files:** `demo-product/src/*`

**API changes:** —

**Database changes:** —

**Acceptance criteria:** `npm run build` passes; all routes render; testids present

**Status:** DONE

## Phase 2 — Backend + data model + multi-tenancy

**Goal:** Backend + data model + multi-tenancy.

**Tasks:** FastAPI app, SQLAlchemy models with tenant_id/product_id, repo layer, settings, tests for isolation

**Files:** `backend/app/{main,config,db,models,schemas,repo}.py`, `tests/`

**API changes:** `GET /health`

**Database changes:** all tables

**Acceptance criteria:** pytest tenant isolation passes

**Status:** DONE

## Phase 3 — Product registration

**Goal:** Product registration.

**Tasks:** Create tenant/product, crawl job, auto-start worker; dashboard snippet

**Files:** `routers/products.py`

**API changes:** `POST/GET /api/products`, `GET /api/products/{id}`

**Database changes:** products, crawl_jobs

**Acceptance criteria:** Creating a product returns job; job visible

**Status:** DONE

## Phase 4 — Worker pipeline

**Goal:** Worker pipeline.

**Tasks:** Thread-pool worker, stage machine, progress/stats persistence, failure handling

**Files:** `worker/pipeline.py`

**API changes:** `GET /api/products/{id}/job`

**Database changes:** crawl_jobs

**Acceptance criteria:** Stages advance to READY on fixture data

**Status:** DONE

## Phase 5 — Playwright crawler

**Goal:** Playwright crawler.

**Tasks:** BFS same-origin crawl, element extraction, action-button click discovery

**Files:** `worker/crawler.py`

**API changes:** —

**Database changes:** pages

**Acceptance criteria:** Demo SaaS yields ≥7 pages with testid elements and revealed forms

**Status:** DONE

## Phase 6 — Feature extraction + product knowledge

**Goal:** Feature extraction + product knowledge.

**Tasks:** Page features, action features, nav edges, nav paths, knowledge chunks

**Files:** `worker/extract.py`, `worker/generate.py`

**API changes:** `GET /api/products/{id}/features|pages|navigation`

**Database changes:** features, navigation_edges, knowledge_chunks

**Acceptance criteria:** Features include Create Report / Invite Member / Billing with selectors

**Status:** DONE

## Phase 7 — Q&A / chat agent

**Goal:** Q&A / chat agent.

**Tasks:** Templated Q&A + optional Claude; intent classifier; chat orchestrator; knowledge search

**Files:** `worker/generate.py`, `agent/*`, `routers/widget.py`

**API changes:** `POST /api/widget/chat`, `GET /api/widget/sessions/{id}`

**Database changes:** qna, chat_sessions, chat_messages

**Acceptance criteria:** Intent tests pass; chat answers analytics question

**Status:** DONE

## Phase 8 — Embeddable widget

**Goal:** Embeddable widget.

**Tasks:** widget.js injects button + iframe; chat app UI; session persistence

**Files:** `static/widget.js`, `static/chat/*`

**API changes:** `GET /widget.js`, `GET /widget/chat`

**Database changes:** —

**Acceptance criteria:** Widget loads inside demo SaaS; history restored after reload

**Status:** DONE

## Phase 9 — Host page action bridge

**Goal:** Host page action bridge.

**Tasks:** postMessage protocol; typed action executor; highlight overlay; SPA navigate

**Files:** `static/widget.js`

**API changes:** —

**Database changes:** —

**Acceptance criteria:** Actions execute; unknown selector returns error

**Status:** DONE

## Phase 10 — Navigation requests

**Goal:** Navigation requests.

**Tasks:** Intent → feature → single navigate step via demo run

**Files:** `agent/chat.py`, `routers/demo.py`

**API changes:** `POST /api/demo/runs/{id}/advance`

**Database changes:** demo_runs

**Acceptance criteria:** 'Take me to analytics' changes route; chat intact

**Status:** DONE

## Phase 11 — Interactive demo engine

**Goal:** Interactive demo engine.

**Tasks:** Sequential step pull loop, status panel, stop, failure message

**Files:** `routers/demo.py`, `static/chat/*`

**API changes:** `POST /api/demo/runs/{id}/stop`

**Database changes:** demo_runs

**Acceptance criteria:** 'Show me how to create a report' completes visibly

**Status:** DONE

## Phase 12 — Dashboard

**Goal:** Dashboard.

**Tasks:** Products list/create, product detail with stage checklist, features, knowledge, demo flows

**Files:** `frontend/src/*`

**API changes:** —

**Database changes:** —

**Acceptance criteria:** Progress visible; knowledge browsable

**Status:** DONE

## Phase 13 — End-to-end integration

**Goal:** End-to-end integration.

**Tasks:** `scripts/dev.sh`, `scripts/e2e.sh`, Playwright-driven widget test, Docker Compose stack (backend on the Playwright image; crawl URL rewrite so the worker reaches `demo-product:3000`)

**Files:** `scripts/*`, `backend/tests/test_e2e_live.py`

**API changes:** —

**Database changes:** —

**Acceptance criteria:** e2e script passes on a clean DB

**Status:** DONE

## Phase 14 — Hackathon polish

**Goal:** Hackathon polish.

**Tasks:** Chat UI polish, suggestions, README, demo script, reliability retries

**Files:** various

**API changes:** —

**Database changes:** —

**Acceptance criteria:** Demo flow runs 3× reliably

**Status:** IN PROGRESS
