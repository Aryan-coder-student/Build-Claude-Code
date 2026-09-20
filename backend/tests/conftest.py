import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="demo-sales-test-"))
os.environ["DEMO_SALES_DATABASE_URL"] = f"sqlite:///{_tmp / 'test.db'}"
os.environ["DEMO_SALES_LLM_ENABLED"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas import CrawledElement, CrawledInteraction, CrawledPage  # noqa: E402


def nav(href: str, label: str, testid: str) -> CrawledElement:
    return CrawledElement(tag="a", text=label, selector=f"[data-testid='{testid}']", testid=testid, href=href, in_nav=True)


NAV = [nav("/", "Dashboard", "dashboard-nav"), nav("/analytics", "Analytics", "analytics-nav"), nav("/analytics/reports", "Reports", "reports-nav"),
       nav("/team", "Team", "team-nav"), nav("/team/invite", "Invite Member", "invite-nav"), nav("/billing", "Billing", "billing-nav")]
LINKS = [n.href for n in NAV]


def page(path: str, title: str, subtitle: str, elements: list[CrawledElement] = (), interactions: list[CrawledInteraction] = ()) -> CrawledPage:
    return CrawledPage(url=f"http://demo.test{path}", path=path, title=f"{title} — Lumen", headings=[title], text=f"{title}\n{subtitle}\nSome body text about {title.lower()}.",
                       elements=NAV + list(elements), links=LINKS, interactions=list(interactions))


REPORT_INPUTS = [
    CrawledElement(tag="input", text="Report name", selector="[data-testid='report-name']", testid="report-name", input_type="text", placeholder="e.g. Monthly Retention"),
    CrawledElement(tag="select", text="Report type", selector="[data-testid='report-type']", testid="report-type", input_type="select"),
]
INVITE_INPUTS = [
    CrawledElement(tag="input", text="Email address", selector="[data-testid='invite-email']", testid="invite-email", input_type="email"),
    CrawledElement(tag="select", text="Role", selector="[data-testid='invite-role']", testid="invite-role", input_type="select"),
    CrawledElement(tag="button", text="Send invitation", selector="[data-testid='send-invite']", testid="send-invite"),
]

FIXTURE_PAGES = [
    page("/", "Dashboard", "Overview of your workspace activity, usage, and recent events."),
    page("/analytics", "Analytics", "Track usage, engagement, retention, and conversion across all projects."),
    page("/analytics/reports", "Reports", "Create, schedule, and share analytics reports on retention, funnels, and adoption.",
         [CrawledElement(tag="button", text="New Report", selector="[data-testid='create-report']", testid="create-report")],
         [CrawledInteraction(selector="[data-testid='create-report']", label="New Report", revealed=REPORT_INPUTS)]),
    page("/team", "Team", "Manage who has access to your workspace and what they can do.",
         [CrawledElement(tag="button", text="Invite Member", selector="[data-testid='invite-member']", testid="invite-member")],
         [CrawledInteraction(selector="[data-testid='invite-member']", label="Invite Member", navigates_to="/team/invite")]),
    page("/team/invite", "Invite Member", "Send an email invitation and choose the teammate's role.", INVITE_INPUTS),
    page("/billing", "Billing", "Manage your subscription plan, payment method, and invoices.",
         [CrawledElement(tag="button", text="Manage payment method", selector="[data-testid='manage-payment']", testid="manage-payment")]),
]


@pytest.fixture(scope="session")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def fake_crawler():
    return lambda url, login=None, on_progress=None: FIXTURE_PAGES
