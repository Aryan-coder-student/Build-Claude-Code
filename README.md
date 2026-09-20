# AI Interactive Product Demo Sales Agent

Drop one script tag into any SaaS product. Our worker crawls the product, builds a tenant-isolated
knowledge base (pages → features → navigation → Q&A → demo flows), and an embedded chatbot acts as an
AI sales engineer: it answers questions, **navigates the live product**, and **runs step-by-step
interactive demos** that visibly drive the host UI while the conversation stays open.

```html
<script src="http://localhost:8000/widget.js" data-product-id="prod_demo_saas"></script>
```

## Run it (Docker)

```bash
cp .env.example .env   # add ANTHROPIC_API_KEY (and ANTHROPIC_WORKSPACE_ID if your key is not workspace-scoped)
docker compose up --build
```

| Service | URL |
|---|---|
| Demo SaaS ("Lumen", the product being demoed) | http://localhost:3000 |
| Dashboard (register products, watch indexing, browse knowledge) | http://localhost:3001 |
| Backend API + widget | http://localhost:8000 |

First run downloads the Playwright base image (~850 MB). Reset everything with `docker compose down -v`.

Claude (`claude-opus-5`) writes the knowledge (feature descriptions, product description, the whole Q&A set) and
composes chat answers strictly from retrieved knowledge. Without a key everything still works with templated knowledge.

From the dashboard, each product has an **Open product with assistant** button and a bookmarklet that injects
the assistant into any page of a product that does not have the snippet installed yet.

## Run it (local dev)

```bash
scripts/dev.sh          # installs on first run, then starts all three servers
scripts/e2e.sh          # API-level end-to-end check against the running servers
cd backend && .venv/bin/pytest -q                       # unit/API tests
cd backend && DEMO_SALES_LIVE=1 .venv/bin/pytest -q tests/test_e2e_live.py   # real-browser widget test
```

## Demo script

1. Open the dashboard, register **Demo SaaS** at `http://localhost:3000` (product id `prod_demo_saas`).
2. Watch the stages: discovering pages → extracting features → navigation → Q&A → demos → READY.
3. Browse Features (route, navigation path, selectors, demo steps), Knowledge, Demo flows.
4. Open the Demo SaaS. Click the chat bubble.
5. Ask: *What analytics features do you have?*
6. Ask: *Take me to analytics.* → the app navigates; chat stays open.
7. Ask: *Show me how to create a report.* → Reports opens, "New Report" is highlighted, explained and
   clicked, the form fields are highlighted and filled, step-by-step, with a live status panel.
8. Ask: *Can I also share reports?* → conversation continues.

## Proven on real products

| Product | Type | Result |
|---|---|---|
| Demo SaaS "Lumen" (`demo-product/`) | our React SPA | 7 pages, 9 features, 39 Claude Q&A; full browser test: question → navigate → 9-step demo → follow-up → reload keeps history |
| DentalPin (local Nuxt clinic app, login) | third-party SPA | 25 pages, 38 features, 101 Q&A; **all 15 action demos pass through the chat in a real browser** |
| OrangeHRM demo (login, multi-page) | third-party MPA | 25 pages, 16 features, 56 Q&A |
| Tabler preview (static, multi-page) | third-party MPA | 25 pages, 27 features, 91 Q&A |

Pitch deck: open [docs/slides/index.html](docs/slides/index.html) in a browser (outline in [docs/PRESENTATION.md](docs/PRESENTATION.md)).

## Products you don't control (no source access)

- **Local products on other ports** (e.g. `http://localhost:3010`): the backend container uses host networking, so the crawler reaches them directly. Add the snippet to the product (for Nuxt: `useHead({ script: [{ src: 'http://localhost:8000/widget.js', 'data-product-id': 'prod_x', tagPosition: 'bodyClose' }] })`).
- **Products behind a login:** tick "Product requires login" when registering and give the login URL, credentials, and
  (optionally) field selectors. The crawler signs in first, then discovers pages. Example: OrangeHRM demo
  (`https://opensource-demo.orangehrmlive.com`, Admin / admin123).
- **Injecting the assistant without editing HTML:** the dashboard's bookmarklet works on sites without a strict
  Content-Security-Policy. Sites like OrangeHRM send `default-src 'self'`, which blocks any external script or iframe,
  so use the dev extension in [extension/](extension/README.md): it removes CSP for the configured hosts in *your*
  browser and injects `widget.js`. This is a demo/dev tool; the production integration is always the one-line snippet
  (or a reverse proxy in front of the product that adds the snippet).
- Multi-page products (every navigation is a full load) are supported: the demo run is remembered in the browser and
  resumes on the next page as soon as the widget is injected again (snippet or extension).
- The crawler falls back to structural CSS selectors (`a[href=…]`, `#id`, `nth-of-type` paths) when a site has no
  `data-testid` attributes, so navigation and highlight demos still work on generic sites.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/PRD.md](docs/PRD.md), and
[docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md). Progress: [docs/PROGRESS.md](docs/PROGRESS.md).

- `backend/` FastAPI + SQLite + in-process Playwright worker + chat agent; serves `widget.js` and the chat iframe.
- `frontend/` Dashboard (Vite + React + Tailwind).
- `demo-product/` Example SaaS SPA with `data-testid` selectors.
- Security: the LLM never produces executable code. The bridge accepts only typed actions
  (`navigate`, `click`, `highlight`, `scroll`, `type`, `wait`, `explain`) with CSS selectors.

Project agent for Claude Code: `claude --agent demo-sales-builder`.
