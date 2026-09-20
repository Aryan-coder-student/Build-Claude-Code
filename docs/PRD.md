# PRD — AI Interactive Product Demo Sales Agent

## 1. Problem
SaaS teams lose trials because visitors cannot find features or understand how to use them.
Static docs and chatbots answer questions but cannot *show* the product. Sales engineers can, but
do not scale.

## 2. Product vision
An embeddable AI sales engineer. One script tag. Our system learns the product automatically and
the chatbot both answers questions and drives the live product UI to demonstrate features.

## 3. Target customer
SaaS companies (product/growth teams) who want interactive, self-serve product demos inside their app or marketing site.

## 4. Target end-user
Website visitors, trial users, and new customers exploring the product.

## 5. Core user journey
1. Customer registers their product (name + URL) in our dashboard.
2. Worker crawls the product, extracts knowledge, and reports progress until READY.
3. Customer pastes the widget snippet into their product.
4. Visitor opens the chat, asks questions, asks to be taken somewhere, or asks for a demo.
5. The chatbot answers, navigates, and runs step-by-step demos while the conversation continues.

## 6. Customer onboarding
- Dashboard form: Product name, URL, Product ID (prefilled slug, editable).
- Creates tenant-scoped product and a crawl job; worker starts automatically.
- Dashboard shows the snippet: `<script src="http://localhost:8000/widget.js" data-product-id="prod_x"></script>`.

## 7. Chatbot experience
- Floating button → chat panel (iframe). Header "Product Assistant".
- Messages, quick suggestions ("Show me" buttons), demo status panel with step counter and Stop.
- Persisted `session_id` (localStorage) so history survives reloads; SPA navigation never resets it.

## 8. Knowledge Q&A
Answers come from the product knowledge base: features, pages, generated Q&A, and text chunks.
With Claude available, answers are composed from retrieved context; without it, the best matching
Q&A / feature description is returned.

## 9. Navigation requests
"Take me to analytics" → resolve target feature/page → one `navigate` action executed in the host.
Reply confirms ("Opening Analytics.").

## 10. Interactive demos
"Show me how to create a report" → resolve the feature's demo flow → sequential typed actions
(navigate, highlight + explain, click, highlight form fields, explain) with visible overlays in the
host UI. Failures stop the demo with a human-readable explanation.

## 11. Product discovery
Playwright crawls same-origin pages from the product URL (BFS, bounded). For each page: URL, title,
visible text, links, buttons, inputs, navigation elements, `data-testid` elements. Action buttons
are clicked to discover revealed forms/elements and URL changes.

## 12. Worker pipeline
`CREATED → DISCOVERING_PAGES → EXTRACTING_FEATURES → BUILDING_NAVIGATION → GENERATING_QA →
GENERATING_DEMOS → INDEXING_KNOWLEDGE → READY` (or `FAILED`). In-process thread pool. Progress and
stats written to `crawl_jobs` and polled by the dashboard.

## 13. Multi-tenancy
Tenant → Products. Every product-scoped row carries `tenant_id` and `product_id`. Repository
queries filter on both. Dashboard sends `X-Tenant-Id`; the widget is keyed by `product_id` and
resolves the tenant server-side. Tenant A data never appears for Tenant B.

## 14. Functional requirements
- FR1 Register product; auto-start worker.
- FR2 Crawl product pages and interactive elements.
- FR3 Extract features with route, navigation path, elements, selectors, questions.
- FR4 Build navigation graph.
- FR5 Generate Q&A and demo flows.
- FR6 Store tenant-isolated knowledge; dashboard shows progress and knowledge.
- FR7 Embeddable widget via one script tag; iframe chat; survives SPA navigation.
- FR8 Chat intents: GENERAL_QA, FEATURE_QA, NAVIGATION_REQUEST, DEMO_REQUEST, UNKNOWN.
- FR9 Typed host actions: navigate, click, highlight, scroll, type, wait, explain.
- FR10 Sequential demo execution with per-step results and graceful failure.

## 15. Non-functional requirements
- Runs fully locally; works without an LLM API key (deterministic fallback).
- Indexing the demo SaaS completes in under ~60 seconds.
- Chat responses under ~3 seconds (deterministic path near-instant).
- No arbitrary JavaScript execution from the LLM in the host page.
- Understandable architecture (explainable in 2 minutes).

## 16. MVP scope
Demo SaaS, dashboard, backend, worker, crawler, extraction, Q&A, widget, bridge, navigation,
interactive demos, progress UI, local end-to-end run.

## 17. Out of scope
Auth/login, billing, production deployment, universal crawling of arbitrary sites, vector DB,
authenticated crawling, multi-language, analytics on chat usage, cross-origin iframe-embedded hosts.

## 18. Success criteria
All Definition of Done boxes in `CLAUDE.md` checked; the demo flow below runs reliably 3 times in a row.

## 19. Hackathon demo flow
1. Open dashboard → create "Demo SaaS" at http://localhost:3000.
2. Watch stages progress to READY; inspect pages/features/questions/demo flows.
3. Open Demo SaaS → widget appears.
4. Ask "What analytics features do you have?" → answer from knowledge.
5. Ask "Take me to analytics." → product navigates; chat intact.
6. Ask "Show me how to create a report." → Reports opens, New Report highlighted/explained/clicked, form highlighted.
7. Ask "Can I also share reports?" → conversation continues.
