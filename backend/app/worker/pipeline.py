"""Discovery pipeline: crawl -> extract -> navigation -> Q&A -> demos -> index. Runs in a worker thread."""

import json
import logging
import traceback
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from .. import models as m
from .. import repo
from ..config import settings
from ..db import session_scope
from ..ids import new_id
from ..schemas import CrawledPage, LoginConfig
from . import extract, generate
from .crawler import crawl_product

log = logging.getLogger(__name__)

STAGES = ["DISCOVERING_PAGES", "EXTRACTING_FEATURES", "BUILDING_NAVIGATION", "GENERATING_QA", "GENERATING_DEMOS", "INDEXING_KNOWLEDGE", "READY"]

Crawler = Callable[..., list[CrawledPage]]  # crawl_product(url, login, on_progress=...)


def _stage(job_id: str, product_id: str, stage: str, message: str, stats: dict[str, int], status: str = "RUNNING") -> None:
    progress = STAGES.index(stage) / (len(STAGES) - 1)
    with session_scope() as session:
        repo.update_job(session, job_id, stage=stage, status=status, progress=progress, message=message, stats=stats)
        product = session.get(m.Product, product_id)
        if product is not None:
            product.status = stage
    log.info("[%s] %s — %s %s", product_id, stage, message, stats)


def run_pipeline(tenant_id: str, product_id: str, job_id: str, crawler: Crawler = crawl_product) -> None:
    stats: dict[str, int] = {}
    try:
        with session_scope() as session:
            product = repo.get_product(session, tenant_id, product_id)
            if product is None:
                raise RuntimeError("product not found for tenant")
            product_name, url = product.name, product.url
            login = LoginConfig.model_validate_json(product.login_json) if product.login_json else None
            if login:
                login = login.model_copy(update={"url": settings.rewrite_crawl_url(login.url)})

        _stage(job_id, product_id, "DISCOVERING_PAGES", f"Crawling {url}…", stats)
        pages = crawler(settings.rewrite_crawl_url(url), login, on_progress=lambda n: _stage(job_id, product_id, "DISCOVERING_PAGES", f"Crawling {url}… {n} pages so far", {"pages": n}))
        if not pages:
            raise RuntimeError(f"No pages could be loaded from {url}")
        stats["pages"] = len(pages)

        _stage(job_id, product_id, "EXTRACTING_FEATURES", "Identifying features and interactive elements…", stats)
        features, edges = extract.extract_features(pages)
        description, features = generate.enrich_features(product_name, features)
        stats["features"] = len(features)

        _stage(job_id, product_id, "BUILDING_NAVIGATION", "Building navigation graph…", stats)
        stats["navigation_edges"] = len(edges)

        _stage(job_id, product_id, "GENERATING_QA", "Generating questions and answers…", stats)
        qna = generate.generate_qna(product_name, features, description)
        stats["questions"] = len(qna)

        _stage(job_id, product_id, "GENERATING_DEMOS", "Creating interactive demo flows…", stats)
        flows = generate.generate_demos(features, pages)
        stats["demo_flows"] = len(flows)

        _stage(job_id, product_id, "INDEXING_KNOWLEDGE", "Indexing knowledge base…", stats)
        chunks = generate.generate_chunks(pages, features)
        stats["chunks"] = len(chunks)

        with session_scope() as session:
            rows = _build_rows(tenant_id, product_id, pages, features, edges, qna, flows, chunks)
            repo.replace_knowledge(session, tenant_id, product_id, rows)
            product = repo.get_product(session, tenant_id, product_id)
            if product is not None:
                product.description = description

        _stage(job_id, product_id, "READY", "Knowledge base ready.", stats, status="DONE")
    except Exception as exc:
        log.error("pipeline failed for %s: %s\n%s", product_id, exc, traceback.format_exc())
        with session_scope() as session:
            repo.update_job(session, job_id, status="FAILED", message=f"Failed: {exc}", stats=stats)
            product = session.get(m.Product, product_id)
            if product is not None:
                product.status = "FAILED"


def _build_rows(tenant_id, product_id, pages, features, edges, qna, flows, chunks) -> list:
    scope = {"tenant_id": tenant_id, "product_id": product_id}
    page_ids = {p.path: new_id("page") for p in pages}
    feature_ids = {f.slug: new_id("feat") for f in features}
    rows: list = [
        m.Page(id=page_ids[p.path], url=p.url, path=p.path, title=p.title, text=p.text, headings_json=json.dumps(p.headings),
               elements_json=json.dumps([e.model_dump() for e in p.elements]), links_json=json.dumps(p.links), **scope)
        for p in pages
    ]
    rows += [
        m.Feature(id=feature_ids[f.slug], page_id=page_ids.get(f.page_path, ""), name=f.name, slug=f.slug, kind=f.kind, description=f.description,
                  route=f.route, nav_path_json=json.dumps(f.nav_path), elements_json=json.dumps([e.model_dump() for e in f.elements]),
                  questions_json=json.dumps(f.questions), keywords_json=json.dumps(f.keywords), **scope)
        for f in features
    ]
    rows += [m.NavigationEdge(id=new_id("edge"), from_path=e.from_path, to_path=e.to_path, selector=e.selector, label=e.label, **scope) for e in edges]
    rows += [m.QnA(id=new_id("qna"), feature_id=feature_ids.get(q.feature_slug, ""), question=q.question, answer=q.answer, **scope) for q in qna]
    rows += [
        m.DemoFlow(id=new_id("flow"), feature_id=feature_ids[fl.feature_slug], name=fl.name, description=fl.description,
                   steps_json=json.dumps([s.model_dump(exclude_none=True) for s in fl.steps]), **scope)
        for fl in flows
    ]
    rows += [m.KnowledgeChunk(id=new_id("chunk"), source_type=st, source_id=sid, title=title, text=text, **scope) for st, sid, title, text in chunks]
    return rows


class Worker:
    """In-process background worker (thread pool). No queue infrastructure needed for the hackathon."""

    def __init__(self) -> None:
        self._pool = ThreadPoolExecutor(max_workers=settings.worker_threads, thread_name_prefix="discovery")

    def submit(self, tenant_id: str, product_id: str, job_id: str) -> None:
        log.info("queued discovery job %s for %s", job_id, product_id)
        self._pool.submit(run_pipeline, tenant_id, product_id, job_id)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)


worker = Worker()
