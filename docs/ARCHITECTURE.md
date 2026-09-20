# Architecture

## Overview

```
Demo SaaS (:3000)                 Dashboard (:3001)            Backend (:8000)
┌────────────────────────┐        ┌───────────────┐            ┌──────────────────────────────┐
│ host page (React SPA)  │        │ Vite + React  │  REST      │ FastAPI                      │
│  <script widget.js>    │        │  X-Tenant-Id  │──────────▶ │  /api/products  /api/widget  │
│   ├ floating button    │        └───────────────┘            │  /api/demo      /widget.js   │
│   ├ host bridge        │                                     │                              │
│   │  (typed actions)   │  postMessage                        │  agent/   chat orchestrator  │
│   └ iframe ───────────────────────────────────┐              │  worker/  pipeline (threads) │
│      chat app (/widget/chat)  ── REST ────────┼────────────▶ │  repo.py  tenant-scoped SQL  │
└────────────────────────┘                      │              │  SQLite (SQLAlchemy)         │
                                                │              │  Playwright (Chromium)       │
                                                               └──────────────────────────────┘
```

Three processes: demo product, dashboard, backend. The backend also serves `widget.js` and the
chat iframe app as static files, so widget ↔ API calls are same-origin.

## Backend layout (`backend/app`)

| Module | Responsibility |
|---|---|
| `main.py` | FastAPI app, CORS, static mounts, routers, startup (DB init, worker pool) |
| `config.py` | Settings (`DEMO_SALES_*` env), model id, limits |
| `db.py`, `models.py` | SQLAlchemy engine/session, ORM tables |
| `schemas.py` | Pydantic API models incl. `DemoAction` |
| `repo.py` | Tenant-scoped queries (every function takes `tenant_id`, `product_id`) |
| `routers/products.py` | Register/list/detail/reindex products, job status, knowledge views |
| `routers/widget.py` | Widget config, session history, chat |
| `routers/demo.py` | Demo run advance/stop |
| `worker/pipeline.py` | Stage orchestrator; writes progress to `crawl_jobs` |
| `worker/crawler.py` | Playwright BFS crawler → `CrawledPage` list |
| `worker/extract.py` | Pages → features, elements, navigation edges |
| `worker/generate.py` | Features → Q&A, demo flows, knowledge chunks (heuristics + optional Claude) |
| `agent/intent.py` | Intent classification + feature matching (deterministic) |
| `agent/chat.py` | Orchestrator: intent → tools → reply + optional demo run |
| `agent/llm.py` | Claude wrapper (`claude-opus-5`), disabled when no credentials |
| `static/widget.js` | Host bridge + iframe injector |
| `static/chat/` | Chat app inside the iframe (vanilla JS/CSS) |

## Data model (SQLite, PostgreSQL-compatible)

All product-scoped tables have `tenant_id`, `product_id`. Lists/objects are stored as JSON text.

- `tenants(id, name)`
- `products(id, tenant_id, name, url, status)`
- `crawl_jobs(id, tenant_id, product_id, type, status, stage, progress, message, stats_json)`
- `pages(id, ..., url, path, title, text, headings_json, elements_json, links_json)`
- `features(id, ..., page_id, name, slug, kind, description, route, nav_path_json, elements_json, questions_json)`
- `navigation_edges(id, ..., from_path, to_path, selector, label)`
- `qna(id, ..., feature_id, question, answer)`
- `demo_flows(id, ..., feature_id, name, description, steps_json)`
- `knowledge_chunks(id, ..., source_type, source_id, title, text)`
- `chat_sessions(id + product_id composite key, tenant_id)` / `chat_messages(id, ..., session_id, role, content, meta_json, seq)`
- `demo_runs(id, ..., session_id, title, steps_json, current_step, status)`

## Worker pipeline

```
POST /api/products ──▶ crawl_job(CREATED) ──▶ ThreadPoolExecutor.submit(run_pipeline)
  DISCOVERING_PAGES     Playwright BFS (same origin, ≤25 pages); click action buttons to find revealed elements
  EXTRACTING_FEATURES   page features (one per page) + action features (buttons that reveal/navigate)
  BUILDING_NAVIGATION   edges from links/nav testids; nav_path per feature from sidebar labels
  GENERATING_QA         templated Q&A per feature/page + product overview (Claude enrichment optional)
  GENERATING_DEMOS      flow per action feature: navigate → highlight → click → highlight revealed inputs → explain
  INDEXING_KNOWLEDGE    knowledge_chunks from page text + feature descriptions
  READY                 product.status = READY
```
Each stage updates `crawl_jobs.stage/progress/message/stats_json`; the dashboard polls every 1.5s.

## Chat runtime

```
iframe ── POST /api/widget/chat {product_id, session_id, message}
   agent.chat: classify intent (deterministic rules; Claude if available)
     GENERAL_QA / FEATURE_QA → search_product_knowledge + get_feature → answer (Claude composes if available)
     NAVIGATION_REQUEST      → get_navigation(feature) → demo_run with 1 navigate step
     DEMO_REQUEST            → get_demo_flow(feature) → demo_run with N steps
   ← {reply, intent, demo_run: {id, title, total_steps} | null, suggestions}
iframe ── POST /api/demo/runs/{id}/advance {result: null | {ok, error}}
   ← {done, step_index, total_steps, action, message}   (one step at a time)
iframe → parent postMessage {type:"demo-agent:action", id, action}
parent (widget.js bridge) executes typed action → postMessage {type:"demo-agent:result", id, ok, error}
iframe → advance with result → next step …
```

Failure: the bridge reports `ok:false, error` (e.g., selector not found after retries). The backend
marks the run FAILED, stores an assistant message ("I couldn't find the New Report button…"), and
returns `done:true` with that message.

## Host bridge actions (typed, no code execution)

`navigate(path)` — same-origin SPA navigation via `history.pushState` + `popstate`; falls back to a
full load if the document did not change (multi-page apps such as OrangeHRM). Before each navigate step the
chat iframe stores `{run, expectPath}` in `localStorage`; after a full load the re-injected widget's iframe
resumes the run if it landed on the expected path, so demos work across page loads. `click(selector)`, `highlight(selector, message)`,
`scroll(selector)`, `type(selector, value)`, `wait(ms)`, `explain(message)`. Selectors are CSS,
preferably `[data-testid='…']`. Each waits up to ~3s for the element.

## Third-party products

`products.login_json` holds an optional `LoginConfig` (login URL, credentials, field selectors); the crawler signs in
before the BFS and skips the login page. Selector fallback order: `data-testid` → unique `#id` → `[name]` → `[aria-label]`
→ `a[href]` → shortest unique `tag:nth-of-type` path. `extension/` is a Manifest V3 dev extension that removes CSP
headers for configured hosts and injects `widget.js`, for sites whose HTML cannot be edited.

## Docker

`docker compose up --build` runs the three services. The backend image is based on the official Playwright
Python image (browsers preinstalled). Because the worker crawls from inside the container, the product URL
`http://localhost:3000` is rewritten to `http://demo-product:3000` for fetching only (`DEMO_SALES_CRAWL_URL_REWRITES`);
stored paths stay relative so the widget in the user's browser navigates correctly. Vite dev servers run with
`allowedHosts: true` so the container hostname is accepted.

## Multi-tenancy

Dashboard requests carry `X-Tenant-Id` (default `ten_demo`, auto-created). Widget/demo endpoints
accept `product_id`, load the product, and use its `tenant_id` for every subsequent query.
`repo.py` never exposes an unscoped read of product data.

## LLM usage

`agent/llm.py` builds an `anthropic.Anthropic()` client only if credentials resolve; otherwise
`llm.enabled` is false and every caller uses its deterministic path. Uses: enrich feature
descriptions and Q&A during generation; classify intent and compose answers at chat time. The LLM
returns text or structured JSON only; never actions with code.
