"""API-level tests: tenant isolation, chat intents, sequential demo execution."""

from app import repo
from app.db import session_scope
from app.models import Product
from app.worker.pipeline import run_pipeline


def _register_indexed(client, fake_crawler, tenant: str, product_id: str, name: str):
    with session_scope() as s:
        repo.ensure_tenant(s, tenant, tenant)
        if s.get(Product, product_id) is None:
            s.add(Product(id=product_id, tenant_id=tenant, name=name, url="http://demo.test"))
        job_id = repo.create_job(s, tenant, product_id).id
    run_pipeline(tenant, product_id, job_id, crawler=fake_crawler)


def test_tenant_isolation(client, fake_crawler):
    _register_indexed(client, fake_crawler, "ten_a", "prod_a", "Product A")
    _register_indexed(client, fake_crawler, "ten_b", "prod_b", "Product B")
    ids_a = {p["id"] for p in client.get("/api/products", headers={"X-Tenant-Id": "ten_a"}).json()}
    ids_b = {p["id"] for p in client.get("/api/products", headers={"X-Tenant-Id": "ten_b"}).json()}
    assert ids_a == {"prod_a"} and ids_b == {"prod_b"}
    assert client.get("/api/products/prod_a", headers={"X-Tenant-Id": "ten_b"}).status_code == 404
    assert client.get("/api/products/prod_a/knowledge", headers={"X-Tenant-Id": "ten_b"}).status_code == 404
    knowledge = client.get("/api/products/prod_a/knowledge", headers={"X-Tenant-Id": "ten_a"}).json()
    assert knowledge["features"] and all(f["route"] for f in knowledge["features"])


def test_register_product_creates_job(client, monkeypatch):
    submitted = []
    monkeypatch.setattr("app.routers.products.worker.submit", lambda *args: submitted.append(args))
    r = client.post("/api/products", json={"name": "Demo SaaS", "url": "http://localhost:3000"}, headers={"X-Tenant-Id": "ten_reg"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"] == "prod_demo_saas" and "widget.js" in body["snippet"]
    assert submitted and submitted[0][:2] == ("ten_reg", "prod_demo_saas")
    job = client.get("/api/products/prod_demo_saas/job", headers={"X-Tenant-Id": "ten_reg"}).json()
    assert job["status"] == "QUEUED"
    assert client.post("/api/products", json={"name": "Demo SaaS", "url": "http://localhost:3000"}, headers={"X-Tenant-Id": "ten_reg"}).status_code == 409


def _chat(client, product_id, session_id, message):
    r = client.post("/api/widget/chat", json={"product_id": product_id, "session_id": session_id, "message": message})
    assert r.status_code == 200, r.text
    return r.json()


def test_chat_answers_feature_question(client, fake_crawler):
    _register_indexed(client, fake_crawler, "ten_c", "prod_c", "Lumen")
    body = _chat(client, "prod_c", "sess_qa", "What analytics features do you have?")
    assert body["intent"] == "FEATURE_QA"
    assert "analytics" in body["reply"].lower()
    assert body["demo_run"] is None
    overview = _chat(client, "prod_c", "sess_qa", "What does this product do?")
    assert overview["intent"] == "GENERAL_QA" and "Analytics" in overview["reply"]


def test_navigation_request_yields_single_navigate_step(client, fake_crawler):
    _register_indexed(client, fake_crawler, "ten_c", "prod_c", "Lumen")
    body = _chat(client, "prod_c", "sess_nav", "Take me to analytics.")
    assert body["intent"] == "NAVIGATION_REQUEST" and body["demo_run"]["total_steps"] == 1
    step = client.post(f"/api/demo/runs/{body['demo_run']['id']}/advance", json={"result": None}).json()
    assert step["action"] == {"type": "navigate", "path": "/analytics", "label": "Analytics"}
    done = client.post(f"/api/demo/runs/{body['demo_run']['id']}/advance", json={"result": {"ok": True}}).json()
    assert done["done"] and done["status"] == "DONE"


def test_demo_request_runs_sequentially_and_survives_conversation(client, fake_crawler):
    _register_indexed(client, fake_crawler, "ten_c", "prod_c", "Lumen")
    body = _chat(client, "prod_c", "sess_demo", "Show me how to create a report.")
    assert body["intent"] == "DEMO_REQUEST"
    run_id = body["demo_run"]["id"]
    total = body["demo_run"]["total_steps"]
    assert total >= 6
    seen = []
    step = client.post(f"/api/demo/runs/{run_id}/advance", json={"result": None}).json()
    while not step["done"]:
        seen.append(step["action"]["type"])
        step = client.post(f"/api/demo/runs/{run_id}/advance", json={"result": {"ok": True}}).json()
    assert seen[:3] == ["navigate", "highlight", "click"] and len(seen) == total
    follow_up = _chat(client, "prod_c", "sess_demo", "Can I also share reports?")
    assert follow_up["reply"]
    history = client.get("/api/widget/sessions/sess_demo/messages", params={"product_id": "prod_c"}).json()
    # the demo's final "explain" step is persisted as an assistant message so it survives reloads
    assert [m["role"] for m in history] == ["user", "assistant", "assistant", "user", "assistant"]
    assert history[2]["meta"]["event"] == "explain"


def test_demo_failure_returns_friendly_message(client, fake_crawler):
    _register_indexed(client, fake_crawler, "ten_c", "prod_c", "Lumen")
    body = _chat(client, "prod_c", "sess_fail", "Show me how to invite member")
    run_id = body["demo_run"]["id"]
    client.post(f"/api/demo/runs/{run_id}/advance", json={"result": None})
    client.post(f"/api/demo/runs/{run_id}/advance", json={"result": {"ok": True}})
    failed = client.post(f"/api/demo/runs/{run_id}/advance", json={"result": {"ok": False, "error": "selector not found"}}).json()
    assert failed["done"] and failed["status"] == "FAILED"
    assert "couldn't find" in failed["message"]
    history = client.get("/api/widget/sessions/sess_fail/messages", params={"product_id": "prod_c"}).json()
    assert history[-1]["content"] == failed["message"]


def test_same_session_id_under_two_products_does_not_collide(client, fake_crawler):
    _register_indexed(client, fake_crawler, "ten_a", "prod_a", "Product A")
    _register_indexed(client, fake_crawler, "ten_b", "prod_b", "Product B")
    assert _chat(client, "prod_a", "sess_shared", "hello")["reply"]
    assert _chat(client, "prod_b", "sess_shared", "hello")["reply"]
    assert len(client.get("/api/widget/sessions/sess_shared/messages", params={"product_id": "prod_a"}).json()) == 2


def test_widget_config_and_unknown_product(client, fake_crawler):
    _register_indexed(client, fake_crawler, "ten_c", "prod_c", "Lumen")
    cfg = client.get("/api/widget/config", params={"product_id": "prod_c"}).json()
    assert cfg["ready"] and cfg["product_name"] == "Lumen" and cfg["suggestions"]
    assert client.get("/api/widget/config", params={"product_id": "prod_nope"}).status_code == 404
