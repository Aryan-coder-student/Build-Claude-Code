"""Playwright crawler: same-origin BFS over a (SPA-friendly) product, plus click discovery."""

import logging
from collections import deque
from collections.abc import Callable
from urllib.parse import urlparse

from playwright.sync_api import Browser, Error as PlaywrightError, Page, sync_playwright

from ..config import settings
from ..schemas import CrawledElement, CrawledInteraction, CrawledPage, LoginConfig

log = logging.getLogger(__name__)

MAX_INTERACTIONS_PER_PAGE = 6
# Never click these during discovery: destructive, state-changing, or session-ending.
SKIP_PATH_WORDS = ("purge", "delete", "remove", "logout", "reset")  # never interact on these pages
SKIP_BUTTON_WORDS = ("cancel", "close", "sign out", "log out", "logout", "delete", "remove", "save", "submit", "reset", "upload", "purge", "pay")

# Runs inside the page. Ignores anything injected by our own widget ([data-demo-agent]).
SNAPSHOT_JS = r"""
() => {
  const origin = location.origin;
  const ours = (el) => !!el.closest('[data-demo-agent]');
  const visible = (el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const attr = (el, a) => el.getAttribute(a) || '';
  const unique = (sel) => { try { return document.querySelectorAll(sel).length === 1; } catch { return false; } };
  // Framework-generated ids (Vue/Nuxt UI 'v-0-0-6', Reka/Radix 'reka-popover-trigger-v-…', Headless UI, React useId ':r1:') change between renders.
  const volatileId = (id) => /^(v-\d|reka-|radix-|headlessui-|:r|mui-|ember\d|react-aria)/.test(id) || /^[0-9a-f-]{8,}$/i.test(id) || /-\d+(-\d+)+$/.test(id);
  const cssPath = (el) => {  // structural fallback: shortest tag:nth-of-type chain that is unique (max 6 levels)
    const parts = [];
    for (let node = el; node && node.nodeType === 1 && parts.length < 6; node = node.parentElement) {
      const tag = node.tagName.toLowerCase();
      if (node.id && !volatileId(node.id)) { parts.unshift(`#${CSS.escape(node.id)}`); const p = parts.join(' > '); if (unique(p)) return p; break; }
      const siblings = [...(node.parentElement ? node.parentElement.children : [])].filter((c) => c.tagName === node.tagName);
      parts.unshift(siblings.length > 1 ? `${tag}:nth-of-type(${siblings.indexOf(node) + 1})` : tag);
      const p = parts.join(' > '); if (unique(p)) return p;
    }
    return '';
  };
  const selectorFor = (el) => {
    const t = attr(el, 'data-testid'); if (t) return `[data-testid='${t}']`;
    if (el.id && !volatileId(el.id) && unique(`#${CSS.escape(el.id)}`)) return `#${CSS.escape(el.id)}`;
    const tag = el.tagName.toLowerCase();
    const name = attr(el, 'name'); if (name && unique(`${tag}[name='${name}']`)) return `${tag}[name='${name}']`;
    const aria = attr(el, 'aria-label'); if (aria && !aria.includes("'") && unique(`[aria-label='${aria}']`)) return `[aria-label='${aria}']`;
    const ph = attr(el, 'placeholder'); if (ph && !ph.includes("'") && unique(`${tag}[placeholder='${ph}']`)) return `${tag}[placeholder='${ph}']`;
    if (el.tagName === 'A') { const h = attr(el, 'href'); if (h && !h.includes("'") && unique(`a[href='${h}']`)) return `a[href='${h}']`; }
    return cssPath(el);
  };
  const labelFor = (el) => {
    const own = ['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName) ? '' : (el.innerText || '').trim();
    if (own) return own;
    if (attr(el, 'aria-label')) return attr(el, 'aria-label');
    const lab = el.closest('label') || (el.id && document.querySelector(`label[for='${el.id}']`));
    if (lab && (lab.innerText || '').trim()) return lab.innerText.trim().split('\n')[0];
    if (attr(el, 'placeholder')) return attr(el, 'placeholder');
    return attr(el, 'name');
  };
  const samePath = (href) => { try { const u = new URL(href, location.href); return u.origin === origin ? u.pathname : null; } catch { return null; } };
  const seen = new Set();
  const elements = [];
  document.querySelectorAll("a[href], button, input, select, textarea, [role='button'], [data-testid]").forEach((el) => {
    if (ours(el) || !visible(el)) return;
    const selector = selectorFor(el); if (!selector || seen.has(selector)) return;
    let href = '';
    if (el.tagName === 'A') { const p = samePath(attr(el, 'href')); if (p === null) return; href = p; }
    seen.add(selector);
    elements.push({
      tag: el.tagName.toLowerCase(), text: labelFor(el).slice(0, 120), selector, testid: attr(el, 'data-testid'), href,
      input_type: el.tagName === 'INPUT' ? (el.type || 'text') : (el.tagName === 'SELECT' ? 'select' : (el.tagName === 'TEXTAREA' ? 'textarea' : '')),
      placeholder: attr(el, 'placeholder'), in_nav: !!el.closest('nav, aside, header'),
    });
  });
  const links = [...new Set([...document.querySelectorAll('a[href]')].filter((a) => !ours(a)).map((a) => samePath(a.getAttribute('href'))).filter(Boolean))];
  const headings = [...document.querySelectorAll('h1, h2, h3, h4, h5, h6')].filter((h) => !ours(h) && visible(h)).map((h) => h.innerText.trim()).filter(Boolean).slice(0, 20);
  const main = document.querySelector('main') || document.body;
  return { title: document.title, headings, text: (main.innerText || '').slice(0, 6000), elements, links, path: location.pathname };
}
"""


def normalize_path(path: str) -> str:
    path = path.split("#")[0].split("?")[0] or "/"
    return path if path == "/" else path.rstrip("/")


def _login(page: Page, login: LoginConfig) -> None:
    log.info("logging in at %s as %s", login.url, login.username)
    _goto(page, login.url)
    page.fill(login.username_selector, login.username, timeout=10000)
    page.fill(login.password_selector, login.password, timeout=10000)
    page.click(login.submit_selector, timeout=10000)
    login_path = normalize_path(urlparse(login.url).path)
    try:
        page.wait_for_url(lambda url: normalize_path(urlparse(url).path) != login_path, timeout=settings.crawl_page_timeout_ms)
    except PlaywrightError as exc:
        raise RuntimeError("login did not leave the login page — check credentials/selectors") from exc
    try:
        page.wait_for_load_state("networkidle", timeout=settings.crawl_networkidle_ms)
    except PlaywrightError:
        pass
    log.info("logged in; landed on %s", page.url)


def _launch(playwright) -> Browser:
    try:
        return playwright.chromium.launch(headless=settings.crawl_headless)
    except PlaywrightError as exc:  # bundled browser missing; try the system Chrome
        log.warning("Bundled Chromium unavailable (%s); trying system Chrome", str(exc).splitlines()[0])
        return playwright.chromium.launch(headless=settings.crawl_headless, channel="chrome")


def _goto(page: Page, url: str) -> None:
    """Load a URL and let a SPA finish rendering (network idle, falling back to plain load on busy sites)."""
    page.goto(url, wait_until="load", timeout=settings.crawl_page_timeout_ms)
    try:
        page.wait_for_load_state("networkidle", timeout=settings.crawl_networkidle_ms)
    except PlaywrightError:
        pass
    page.wait_for_timeout(settings.crawl_settle_ms)


def _snapshot(page: Page) -> dict:
    return page.evaluate(SNAPSHOT_JS)


def _is_action_button(el: CrawledElement) -> bool:
    """Labelled, non-navigation buttons only: icon-only buttons in tables are noise on generic sites."""
    if el.tag != "button" or el.in_nav or len(el.text.strip()) < 3:
        return False
    return not any(word in el.text.lower() for word in SKIP_BUTTON_WORDS)


def _signature(el: CrawledElement) -> tuple:
    """Identity that survives DOM shifts (structural selectors change when new elements appear)."""
    return (el.tag, el.text, el.input_type, el.placeholder, el.href, el.testid)


def _discover_interactions(page: Page, base: str, url: str, snap_elements: list[CrawledElement]) -> list[CrawledInteraction]:
    """Click each visible action button from a fresh page load and record what it reveals or where it navigates."""
    interactions: list[CrawledInteraction] = []
    if any(word in urlparse(url).path.lower() for word in SKIP_PATH_WORDS):
        return interactions
    before = {_signature(e) for e in snap_elements}
    candidates = sorted((e for e in snap_elements if _is_action_button(e)), key=lambda e: not e.testid)  # data-testid first
    for button in candidates[:MAX_INTERACTIONS_PER_PAGE]:
        try:
            _goto(page, url)
            page.click(button.selector, timeout=3000)
            page.wait_for_timeout(settings.crawl_settle_ms)
            after = _snapshot(page)
            new_path = normalize_path(after["path"])
            revealed = [el for el in (CrawledElement(**e) for e in after["elements"]) if not el.in_nav and _signature(el) not in before]  # header/sidebar widgets are never "revealed"
            navigates_to = new_path if new_path != normalize_path(urlparse(url).path) else ""
            interactions.append(CrawledInteraction(selector=button.selector, label=button.text, navigates_to=navigates_to, revealed=revealed))
            log.info("interaction %s -> navigates_to=%r revealed=%d", button.selector, navigates_to, len(revealed))
        except PlaywrightError as exc:
            log.warning("click discovery failed for %s: %s", button.selector, str(exc).splitlines()[0])
    return interactions


def crawl_product(base_url: str, login: LoginConfig | None = None, max_pages: int | None = None, on_progress: Callable[[int], None] | None = None) -> list[CrawledPage]:
    max_pages = max_pages or settings.crawl_max_pages
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    start = normalize_path(parsed.path)
    queue: deque[str] = deque([start])
    seen: set[str] = {start}
    pages: list[CrawledPage] = []

    with sync_playwright() as p:
        browser = _launch(p)
        page = browser.new_context(viewport={"width": 1400, "height": 900}).new_page()
        if login:
            _login(page, login)
        login_path = normalize_path(urlparse(login.url).path) if login else None
        while queue and len(pages) < max_pages:
            path = queue.popleft()
            url = base + path
            try:
                _goto(page, url)
                snap = _snapshot(page)
            except PlaywrightError as exc:
                log.warning("failed to load %s: %s", url, str(exc).splitlines()[0])
                continue
            landed = normalize_path(snap["path"])
            if login_path and landed == login_path:
                log.warning("redirected to the login page while loading %s; skipping", path)
                continue
            if any(p.path == landed for p in pages):
                log.info("%s redirected to already-crawled %s; skipping", path, landed)
                continue
            elements = [CrawledElement(**e) for e in snap["elements"]]
            interactions = _discover_interactions(page, base, base + landed, elements)  # use the landed URL: redirects may lead elsewhere
            links = sorted({normalize_path(l) for l in snap["links"]} | {i.navigates_to for i in interactions if i.navigates_to})
            links = [l for l in links if l != login_path]
            pages.append(
                CrawledPage(
                    url=url, path=normalize_path(snap["path"]), title=snap["title"], headings=snap["headings"],
                    text=snap["text"], elements=elements, links=links, interactions=interactions,
                )
            )
            log.info("crawled %s (%d elements, %d links)", path, len(elements), len(links))
            if on_progress:
                on_progress(len(pages))
            for link in links:
                if link not in seen:
                    seen.add(link)
                    queue.append(link)
        browser.close()
    return pages
