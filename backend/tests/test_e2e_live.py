"""Live browser test of the wow-factor: widget loads in the demo SaaS, navigation and a demo drive the host UI.

Requires the three dev servers (scripts/dev.sh). Skipped unless DEMO_SALES_LIVE=1.
"""

import os
import time

import httpx
import pytest
from playwright.sync_api import sync_playwright

API = os.environ.get("DEMO_SALES_API", "http://localhost:8000")
DEMO = os.environ.get("DEMO_SALES_DEMO_URL", "http://localhost:3000")
PRODUCT_ID = "prod_demo_saas"

pytestmark = pytest.mark.skipif(os.environ.get("DEMO_SALES_LIVE") != "1", reason="set DEMO_SALES_LIVE=1 with servers running")


def ensure_indexed():
    r = httpx.get(f"{API}/api/products/{PRODUCT_ID}")
    if r.status_code == 404:
        httpx.post(f"{API}/api/products", json={"name": "Demo SaaS", "url": DEMO, "id": PRODUCT_ID}).raise_for_status()
    for _ in range(60):
        status = httpx.get(f"{API}/api/products/{PRODUCT_ID}").json()["status"]
        if status == "READY":
            return
        assert status != "FAILED"
        time.sleep(2)
    raise AssertionError("product never became READY")


def test_widget_navigation_and_demo_in_real_browser(tmp_path):
    ensure_indexed()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(DEMO, wait_until="load")
        page.click("[data-demo-agent='launcher']")
        chat = page.frame_locator("[data-demo-agent='frame']")
        chat.locator("#input").wait_for()
        page.wait_for_timeout(800)
        assert "Assistant" in chat.locator("#title").inner_text()

        def ask(text):
            chat.locator("#input").fill(text)
            chat.locator("#send").click()
            chat.locator(".msg.typing").wait_for(state="detached", timeout=30000)  # reply arrived (Claude may take a few seconds)

        ask("What analytics features do you have?")
        replies = chat.locator(".msg.assistant .bubble")
        assert "analytics" in replies.last.inner_text().lower()

        ask("Take me to analytics.")
        page.wait_for_url("**/analytics", timeout=8000)
        page.wait_for_function("() => document.querySelector('h1')?.innerText === 'Analytics'", timeout=5000)  # SPA re-rendered
        assert chat.locator(".msg.user").count() == 2, "conversation must survive SPA navigation"

        ask("Show me how to create a report.")
        page.wait_for_url("**/analytics/reports", timeout=8000)
        page.wait_for_selector("[data-testid='report-name']", timeout=15000)  # New Report was clicked → form revealed
        page.wait_for_function("() => document.querySelector(\"[data-testid='report-name']\").value.length > 5", timeout=15000)
        page.screenshot(path=str(tmp_path / "demo.png"))
        chat.locator("#demo.hidden").wait_for(state="attached", timeout=30000)  # demo panel hides when done
        assert chat.locator(".msg.user").count() == 3

        ask("Can I also share reports?")
        assert chat.locator(".msg.user").count() == 4 and chat.locator(".msg.assistant").count() >= 5

        # reload keeps the conversation (session id in localStorage, history from backend)
        page.reload(wait_until="load")
        page.wait_for_timeout(1200)
        chat = page.frame_locator("[data-demo-agent='frame']")
        assert chat.locator(".msg.user").count() == 4

        # multi-page hosts: a full page load right after the navigate step must not kill the demo
        ask("Show me how to create a project.")
        page.wait_for_url("**/projects", timeout=8000)
        page.reload(wait_until="load")
        page.wait_for_selector("[data-testid='project-name']", timeout=20000)  # demo resumed: New Project clicked, form revealed
        page.wait_for_function("() => document.querySelector(\"[data-testid='project-name']\").value.length > 3", timeout=15000)
        browser.close()
