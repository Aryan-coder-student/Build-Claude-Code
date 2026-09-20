# Presentation — AI Interactive Product Demo Sales Agent

Hackathon pitch, 5-7 minutes, 13 slides. Rendered deck: `docs/slides/index.html` (open the file directly in a browser; arrow keys or click to advance).

Timing guide: slides 1-4 in ~90s, live demo slide ~2 min (run it for real if possible), slides 6-9 ~2 min, slides 10-13 ~1 min.

---

## Slide 1 — Title

**AI Interactive Product Demo Sales Agent**
*An AI sales engineer that shows, not tells.*

- One `<script>` tag → your product gets an assistant that answers, navigates, and demos live
- Built with FastAPI, Playwright, Claude, and a vanilla-JS widget
- Runs end to end with `docker compose up --build`

**Speaker notes:** Open with the one-liner. "Every SaaS has docs and a chatbot. Neither can show you the product. We built one that can — and it learns your product by itself."

---

## Slide 2 — The problem

**Visitors can't find features. Docs tell, they don't show. Sales engineers don't scale.**

- Trials are lost because people can't find or understand a feature, not because it's missing
- Static docs and FAQ bots answer in text; the user still has to go find the button
- A human sales engineer can drive the product live — but there's one of them and thousands of visitors
- Existing tour tools need hand-authored steps for every feature, and go stale with every release

**Speaker notes:** Ground it: "Where do I create a report?" gets a paragraph back, and the visitor still has to go hunting. The gap is between *knowing* and *seeing*.

---

## Slide 3 — The insight

**Turn the product itself into the knowledge base — then let the assistant drive it.**

- A running product already encodes its features: routes, navigation, buttons, forms
- Crawl it like a user would (click things, see what appears) → structured knowledge, not scraped text
- Give the chatbot hands: a small set of typed, safe actions it can perform in the host page
- Result: an assistant that says "Sure — watch the screen" and then does it

**Speaker notes:** The key reframing: we don't ask the customer to write demo scripts. Discovery is automatic; the LLM enriches and explains; the UI actions are deterministic.

---

## Slide 4 — What we built

**One script tag → learns the product → chats, navigates, demos.**

- Customer registers a product URL in the dashboard; the worker crawls it and reports stage progress until READY
- Knowledge base per tenant: pages → features (route, nav path, selectors) → navigation graph → Q&A → demo flows
- Embedded chatbot (floating button + iframe) answers grounded questions from that knowledge
- "Take me to analytics" → in-app navigation; chat stays open
- "Show me how to create a report" → step-by-step demo that highlights, clicks, and types in the live UI
- Dashboard to watch indexing and browse features, Q&A, and demo flows

**Speaker notes:** Emphasize *zero authoring*. The Demo SaaS ("Lumen") indexes in about 12 seconds without Claude: 7 pages, 9 features, 26 Q&A, 9 demo flows.

---

## Slide 5 — Live demo flow

**The 8-step story (from the README demo script)**

1. Dashboard → register **Demo SaaS** (`prod_demo_saas`)
2. Watch stages: discovering pages → extracting features → navigation → Q&A → demos → READY
3. Browse Features (route, nav path, selectors, steps), Knowledge, Demo flows
4. Open the Demo SaaS, click the chat bubble
5. *"What analytics features do you have?"* → grounded answer
6. *"Take me to analytics."* → SPA navigation, chat intact
7. *"Show me how to create a report."* → Reports opens, **New Report** highlighted, explained and clicked; form fields highlighted and filled, live status panel
8. *"Can I also share reports?"* → conversation continues; a reload keeps the history

**Speaker notes:** This exact flow passes in a real browser (Playwright-driven test) — 9 typed steps in the report demo. If the live demo hiccups, the fallback is the recorded run; the same steps also resume after a full page load.

---

## Slide 6 — How it works: architecture

```
 Host product page (customer's SaaS)              Backend (FastAPI :8000)
 ┌───────────────────────────────────┐            ┌──────────────────────────────────┐
 │ <script src=widget.js>            │            │ routers: products / widget / demo│
 │  ├ floating launcher              │   REST     │ agent/  intent → knowledge → reply│
 │  ├ host bridge (typed actions)    │◀──────────▶│ worker/ pipeline (thread pool)   │
 │  └ iframe: chat app  ── postMessage ──┘        │ repo.py tenant-scoped SQL        │
 └───────────────────────────────────┘            │ SQLite · Playwright (Chromium)   │
                                                  │ llm.py  Claude (optional)        │
 Dashboard (Vite + React :3001) ── REST, X-Tenant-Id ──▶└──────────────────────────────────┘
```

- Three processes: host product, dashboard, backend. Backend also serves `widget.js` and the chat iframe (same origin)
- Widget = host bridge (executes actions) + iframe (chat UI). They talk only via `postMessage`
- Worker pipeline stages: DISCOVERING_PAGES → EXTRACTING_FEATURES → BUILDING_NAVIGATION → GENERATING_QA → GENERATING_DEMOS → INDEXING_KNOWLEDGE → READY
- No queues, no vector DB: in-process thread pool, SQLite (PostgreSQL-compatible schema), token-overlap retrieval over structured knowledge

**Speaker notes:** "Explainable in two minutes" was a requirement. One backend, one worker thread pool, one widget file. Everything the LLM touches is behind `agent/llm.py` with a deterministic fallback.

---

## Slide 7 — How discovery works

**Crawl like a user, then structure what you saw.**

- Playwright BFS over same-origin pages (bounded, 25 pages max); optional login step for protected products
- Per page: title, headings, text, links, buttons, inputs, nav elements — with a stable CSS selector for each (`data-testid` → `#id` → `[name]` → `[aria-label]` → `a[href]` → shortest unique `nth-of-type` path)
- **Click discovery:** each labelled action button is clicked from a fresh load; we record what it reveals (form inputs) or where it navigates. Destructive words (delete, logout, pay, …) are never clicked
- Extraction: one *page* feature per page + one *action* feature per meaningful interaction; nav paths from sidebar labels; site-wide controls deduplicated
- Generation: Q&A per feature, a demo flow per feature (navigate → highlight → click → highlight/type inputs → explain), knowledge chunks
- **Claude enrichment:** writes feature descriptions, the product description, and the whole Q&A set from the discovered structure only — templates are the no-key fallback

**Speaker notes:** The click-discovery step is what turns "Reports page" into "Create Report: click New Report, fill name and type". With Claude, Demo SaaS yields 39 Q&A in ~40s; Claude is instructed to never invent features, and in testing it declines questions about integrations it has no evidence for.

---

## Slide 8 — How a demo executes

**A pull loop of typed actions, one step at a time.**

- Chat reply may carry a `demo_run` (navigation requests are one-step runs; same code path)
- Iframe → `POST /api/demo/runs/{id}/advance` → backend returns the next action + a human message
- Iframe → `postMessage` → host bridge executes: `navigate`, `click`, `highlight`, `scroll`, `type`, `wait`, `explain`
- Bridge reports `{ok, error}`; the backend advances or marks the run FAILED with a readable explanation ("I couldn't find the New Report button on this screen…")
- SPA navigation via `pushState` + `popstate`; if the router didn't react, fall back to a full load
- Before each navigate the run is saved in `localStorage`; after a full page load the re-injected widget resumes it if it landed on the expected path — multi-page apps work too
- Status panel with step counter, progress bar and Stop

**Speaker notes:** Each step waits up to ~3s for its selector, scrolls it into view, pulses a highlight overlay and shows a tooltip. Typing goes through the native value setter so React-controlled inputs update correctly.

---

## Slide 9 — Safety & multi-tenancy

**The LLM never emits code. Tenants never see each other.**

- Claude returns text or schema-validated JSON only; it never produces actions, selectors, or scripts
- The host bridge accepts exactly seven typed actions with CSS selectors; unknown action types are rejected; cross-origin navigation is refused
- The chat UI runs in an iframe; bridge ↔ iframe messages are origin-checked both ways
- The crawler never clicks destructive controls and ignores its own injected widget
- Every product-scoped row carries `tenant_id` + `product_id`; the repository has no unscoped reads
- Dashboard authenticates the tenant via header; the widget is keyed by `product_id` and resolves the tenant server-side

**Speaker notes:** This is the answer to "you're letting an AI drive my app?" — no, we let a *whitelist of DOM operations* drive it, and the AI only chooses among pre-generated, deterministic flows.

---

## Slide 10 — Real-world proof

**Not just our sample app.**

| Product | Kind | Pages | Features | Q&A |
|---|---|---|---|---|
| Demo SaaS "Lumen" (ours) | React SPA | 7 | 9 | 26 (39 with Claude) |
| OrangeHRM demo | login-protected, multi-page | 25 | 16 | 56 |
| Tabler | static multi-page site | 25 | 27 | 91 |
| DentalPin (local Nuxt product) | login-protected SPA | 25 | 38 | 101 |

- Demo SaaS: full browser test passes — question → navigation → 9-step demo → follow-up → reload keeps history
- DentalPin: in a real browser the widget answers grounded questions, navigates in-app without reload, and runs "Show me how to create my first patient" (opens the dialog, highlights and fills fields); 15 of 15 action demos pass end to end
- Sites with strict CSP (OrangeHRM) use the dev extension; the production path is always the one-line snippet or a reverse proxy

**Speaker notes:** These numbers come from live indexing runs today. DentalPin: all 15 action demos pass through the chat in a real browser. Two fixes made that possible: the crawler avoids framework-generated ids, and the widget navigates like a user (in-app link click, or router-compatible history state), because an empty pushState broke Vue Router's later navigations.

---

## Slide 11 — Where Claude fits (and where it doesn't)

**An enrichment layer with a deterministic floor.**

- Indexing time: feature descriptions, product description, full Q&A set — structured output validated against Pydantic schemas
- Chat time: composes 1-3 sentence answers from retrieved knowledge only; says so honestly when the knowledge doesn't cover a question
- Never: intent → action mapping, selectors, demo steps, or anything executed in the host page
- Without a key: templated descriptions and Q&A, rule-based intents, best-match answers — the demo still runs end to end

**Speaker notes:** Model: `claude-opus-5`, low effort for chat answers so replies stay fast. The point of the design is that a wrong LLM answer can only be *wrong text*, never a wrong click.

---

## Slide 12 — What's next

- Finish selector robustness for framework-generated ids (the remaining DentalPin demos)
- Semantic retrieval (embeddings) on top of the structured knowledge for fuzzier questions
- Richer demo flows: multi-page journeys, conditional steps, real form submission in sandboxed accounts
- Chat analytics for the customer: what visitors ask, where demos fail, which features convert
- Production hardening: auth, PostgreSQL, hosted widget origin, per-tenant rate limits

**Speaker notes:** Scope was deliberately MVP: no auth, no billing, no vector DB. The architecture was written so PostgreSQL can replace SQLite (string ids, JSON columns).

---

## Slide 13 — Thanks

**One script tag. An AI sales engineer that shows, not tells.**

- Repo: `Build-Claude-Code` — `docker compose up --build`, then open the dashboard and follow the README demo script
- Docs: `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/PROGRESS.md`
- Questions?

**Speaker notes:** Close by inviting them to try it on their own product URL — that's the whole pitch.
