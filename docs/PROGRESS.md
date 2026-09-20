# Current Status

MVP completion: 100% (polish ongoing)

## Working

- Project agent (`.claude/agents/demo-sales-builder.md`), `CLAUDE.md`, docs, README
- Demo SaaS "Lumen" (Vite React SPA, 7 routes, `data-testid` selectors) on :3000
- Backend (FastAPI + SQLite + SQLAlchemy) on :8000 with tenant-scoped repository
- Product registration → auto-started in-process worker → stage progress in `crawl_jobs`
- Playwright crawler (BFS + click discovery of revealed forms / navigations): 7 pages in ~12s
- Feature extraction (page + action features, selectors, nav paths), navigation graph, Q&A, demo flows, knowledge chunks
- Chat agent: deterministic intents (GENERAL_QA / FEATURE_QA / NAVIGATION_REQUEST / DEMO_REQUEST / UNKNOWN); answers composed by Claude (claude-opus-5, low effort) from retrieved knowledge
- Claude-generated knowledge: feature descriptions, product description, and the full Q&A set (39 items for Demo SaaS, ~40s indexing); templates remain the no-key fallback
- Embeddable `widget.js` (launcher + iframe + typed-action bridge) and chat app; session persisted in localStorage
- Sequential demo engine (`/api/demo/runs/{id}/advance`), status panel, Stop, graceful selector failures
- Dashboard on :3001: products list/register with snippet, stage checklist, counts, Features / Knowledge / Demo flows
- Docker Compose (`docker compose up --build`) verified: API e2e + real-browser test pass against the containers

## In Progress

- Third-party site support: login-aware crawl, network-idle waits, generic selectors, path-derived page names; OrangeHRM demo indexed (25 pages, 16 features, 56 Claude Q&A); Tabler indexed (25 pages, 27 features, 91 Q&A); DentalPin (local Nuxt app, login) indexed (25 pages, 38 features, 101 Q&A) — all 15 action demos pass through the chat in a real browser. Demos resume after full page loads (multi-page apps). Dev extension for CSP-protected sites written; needs manual verification in Chrome (automated CSP-strip test was not permitted in this session).

- Phase 14 polish (wording, optional Claude enrichment when a key is provided)

## Next

- Rehearse the live demo script in README.md

## Blockers

None. `ANTHROPIC_API_KEY` + `ANTHROPIC_WORKSPACE_ID` are in the git-ignored `.env`; the key is not workspace-scoped so the header is required (`DEMO_SALES_ANTHROPIC_WORKSPACE_ID`).

## End-to-End

Product registration: PASS (API + dashboard)
Worker: PASS (7 pages, 9 features, 26 Q&A, 9 demo flows for Demo SaaS)
Crawler: PASS (live Playwright crawl of :3000)
Q&A: PASS (unit + live browser)
Widget: PASS (loads in demo SaaS, history restored after reload)
Navigation: PASS (live browser: "Take me to analytics" → /analytics, chat intact)
Interactive demo: PASS (real browser, 9 steps drive the UI; verified 3× locally and 2× on Docker)
Docker Compose: PASS (`scripts/e2e.sh` + live browser test against containers)
