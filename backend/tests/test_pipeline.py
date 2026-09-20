import json

from app import models as m
from app import repo
from app.db import session_scope
from app.worker import extract, generate
from app.worker.pipeline import run_pipeline
from tests.conftest import FIXTURE_PAGES


def test_extract_features_from_fixture_pages():
    features, edges = extract.extract_features(FIXTURE_PAGES)
    by_slug = {f.slug: f for f in features}
    assert {"dashboard", "analytics", "reports", "team", "invite_member", "billing"} <= set(by_slug)
    create_report = by_slug["create_report"]
    assert create_report.kind == "action"
    assert create_report.route == "/analytics/reports"
    assert create_report.nav_path == ["Analytics", "Reports", "New Report"]
    assert [e.selector for e in create_report.elements] == ["[data-testid='create-report']", "[data-testid='report-name']", "[data-testid='report-type']"]
    invite = by_slug["invite_member"]  # the action beats the same-named page
    assert invite.kind == "action" and invite.route == "/team/invite"
    assert [e.selector for e in invite.elements][:2] == ["[data-testid='invite-member']", "[data-testid='invite-email']"]
    assert any(e.from_path == "/team" and e.to_path == "/team/invite" and e.selector == "[data-testid='invite-member']" for e in edges)


def test_generate_demo_flow_for_create_report():
    features, _ = extract.extract_features(FIXTURE_PAGES)
    flows = {f.feature_slug: f for f in generate.generate_demos(features, FIXTURE_PAGES)}
    steps = flows["create_report"].steps
    assert [s.type for s in steps] == ["navigate", "highlight", "click", "wait", "highlight", "type", "highlight", "explain"]
    assert steps[0].path == "/analytics/reports"
    assert steps[2].selector == "[data-testid='create-report']"
    assert steps[5].value == "Monthly Retention"


def test_generate_qna_mentions_features():
    features, _ = extract.extract_features(FIXTURE_PAGES)
    qna = generate.templated_qna("Lumen", features)
    questions = {q.question for q in qna}
    assert "How do I create report?" in questions
    assert "Does this product have analytics?" in questions
    assert any("Analytics" in q.answer for q in qna if q.question == "What does this product do?")


def test_pipeline_persists_scoped_knowledge(client, fake_crawler):
    with session_scope() as s:
        repo.ensure_tenant(s, "ten_p", "P")
        s.add(m.Product(id="prod_pipe", tenant_id="ten_p", name="Lumen", url="http://demo.test"))
        job = repo.create_job(s, "ten_p", "prod_pipe")
        job_id = job.id
    run_pipeline("ten_p", "prod_pipe", job_id, crawler=fake_crawler)
    with session_scope() as s:
        job = s.get(m.CrawlJob, job_id)
        assert job.status == "DONE" and job.stage == "READY"
        stats = json.loads(job.stats_json)
        assert stats["pages"] == 6 and stats["features"] >= 7 and stats["demo_flows"] >= 7
        assert s.get(m.Product, "prod_pipe").status == "READY"
        assert repo.product_counts(s, "ten_p", "prod_pipe")["questions"] > 10
        # re-running replaces instead of duplicating
    run_pipeline("ten_p", "prod_pipe", job_id, crawler=fake_crawler)
    with session_scope() as s:
        assert repo.product_counts(s, "ten_p", "prod_pipe")["pages"] == 6


def test_pipeline_failure_is_recorded(client):
    def broken(url, login=None, on_progress=None):
        raise RuntimeError("boom")

    with session_scope() as s:
        repo.ensure_tenant(s, "ten_f", "F")
        s.add(m.Product(id="prod_fail", tenant_id="ten_f", name="X", url="http://x.test"))
        job_id = repo.create_job(s, "ten_f", "prod_fail").id
    run_pipeline("ten_f", "prod_fail", job_id, crawler=broken)
    with session_scope() as s:
        assert s.get(m.CrawlJob, job_id).status == "FAILED"
        assert s.get(m.Product, "prod_fail").status == "FAILED"
