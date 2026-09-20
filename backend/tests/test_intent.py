import pytest

from app.agent.intent import FeatureIndex, Intent, classify, match_feature

FEATURES = [
    FeatureIndex(id="1", name="Analytics", slug="analytics", kind="page", description="", route="/analytics", nav_path=["Analytics"], keywords=["analytics", "usage", "retention"]),
    FeatureIndex(id="2", name="Reports", slug="reports", kind="page", description="", route="/analytics/reports", nav_path=["Analytics", "Reports"], keywords=["reports", "analytics"]),
    FeatureIndex(id="3", name="Create Report", slug="create_report", kind="action", description="", route="/analytics/reports", nav_path=["Analytics", "Reports", "New Report"], keywords=["report", "reports", "name", "type"]),
    FeatureIndex(id="4", name="Billing", slug="billing", kind="page", description="", route="/billing", nav_path=["Billing"], keywords=["billing", "plan", "invoices", "payment"]),
    FeatureIndex(id="5", name="Invite Member", slug="invite_member", kind="page", description="", route="/team/invite", nav_path=["Team", "Invite Member"], keywords=["invite", "member", "team", "email"]),
]


@pytest.mark.parametrize("message,intent", [
    ("What does this product do?", Intent.GENERAL_QA),
    ("Does it support reports?", Intent.FEATURE_QA),
    ("Take me to reports.", Intent.NAVIGATION_REQUEST),
    ("Show me how to create a report.", Intent.DEMO_REQUEST),
    ("How do I invite a team member?", Intent.FEATURE_QA),
    ("Walk me through inviting a team member", Intent.DEMO_REQUEST),
    ("Show me the billing feature.", Intent.NAVIGATION_REQUEST),
    ("Where can I invite a team member?", Intent.NAVIGATION_REQUEST),
])
def test_classify(message, intent):
    assert classify(message) == intent


@pytest.mark.parametrize("message,slug", [
    ("Show me how to create a report.", "create_report"),
    ("Take me to reports.", "reports"),
    ("Take me to analytics.", "analytics"),
    ("Show me the billing feature.", "billing"),
    ("Where can I invite a team member?", "invite_member"),
    ("Does this support analytics?", "analytics"),
])
def test_match_feature(message, slug):
    intent = classify(message)
    assert match_feature(message, FEATURES, intent).slug == slug


def test_no_match_returns_none():
    assert match_feature("Do you integrate with Salesforce?", FEATURES, Intent.FEATURE_QA) is None
