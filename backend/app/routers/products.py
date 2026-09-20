"""Dashboard API: products, jobs, and knowledge views. Tenant comes from the X-Tenant-Id header."""

import json
import re
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .. import models as m
from .. import repo
from ..config import settings
from ..db import get_session
from ..ids import new_id, slug
from ..schemas import JobOut, ProductCreate, ProductOut
from ..worker.pipeline import worker

router = APIRouter(prefix="/api/products", tags=["products"])

SessionDep = Annotated[Session, Depends(get_session)]


def tenant_id(x_tenant_id: Annotated[str | None, Header()] = None) -> str:
    return x_tenant_id or settings.default_tenant_id


TenantDep = Annotated[str, Depends(tenant_id)]


def snippet(product_id: str) -> str:
    return f'<script src="{settings.public_url}/widget.js" data-product-id="{product_id}"></script>'


def to_out(session: Session, product: m.Product) -> ProductOut:
    return ProductOut(
        id=product.id, tenant_id=product.tenant_id, name=product.name, url=product.url, description=product.description,
        status=product.status, requires_login=bool(product.login_json), counts=repo.product_counts(session, product.tenant_id, product.id), snippet=snippet(product.id),
    )


def _load(session: Session, tenant: str, product_id: str) -> m.Product:
    product = repo.get_product(session, tenant, product_id)
    if product is None:
        raise HTTPException(404, "product not found")
    return product


@router.get("", response_model=list[ProductOut])
def list_products(session: SessionDep, tenant: TenantDep):
    return [to_out(session, p) for p in repo.list_products(session, tenant)]


@router.post("", response_model=ProductOut, status_code=201)
def create_product(body: ProductCreate, session: SessionDep, tenant: TenantDep):
    repo.ensure_tenant(session, tenant, settings.default_tenant_name if tenant == settings.default_tenant_id else tenant)
    product_id = body.id or f"prod_{slug(body.name)}"
    if not re.fullmatch(r"prod_[a-z0-9_]{1,60}", product_id):
        raise HTTPException(422, "product id must look like prod_my_product")
    if not re.match(r"^https?://", body.url):
        raise HTTPException(422, "url must start with http:// or https://")
    if session.get(m.Product, product_id) is not None:
        raise HTTPException(409, f"product {product_id} already exists")
    product = m.Product(id=product_id, tenant_id=tenant, name=body.name.strip(), url=body.url.strip().rstrip("/"),
                        login_json=body.login.model_dump_json() if body.login else "")
    session.add(product)
    job = repo.create_job(session, tenant, product.id)
    session.commit()
    worker.submit(tenant, product.id, job.id)
    return to_out(session, product)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: str, session: SessionDep, tenant: TenantDep):
    return to_out(session, _load(session, tenant, product_id))


@router.post("/{product_id}/reindex", response_model=JobOut)
def reindex(product_id: str, session: SessionDep, tenant: TenantDep):
    product = _load(session, tenant, product_id)
    product.status = "CREATED"
    job = repo.create_job(session, tenant, product.id)
    session.commit()
    worker.submit(tenant, product.id, job.id)
    return job_out(job)


def job_out(job: m.CrawlJob) -> JobOut:
    return JobOut(id=job.id, status=job.status, stage=job.stage, progress=job.progress, message=job.message, stats=json.loads(job.stats_json), updated_at=job.updated_at.isoformat())


@router.get("/{product_id}/job", response_model=JobOut | None)
def get_job(product_id: str, session: SessionDep, tenant: TenantDep):
    _load(session, tenant, product_id)
    job = repo.latest_job(session, tenant, product_id)
    return job_out(job) if job else None


@router.get("/{product_id}/knowledge")
def get_knowledge(product_id: str, session: SessionDep, tenant: TenantDep):
    _load(session, tenant, product_id)
    features = repo.scoped(session, m.Feature, tenant, product_id)
    return {
        "pages": [{"id": p.id, "path": p.path, "title": p.title, "headings": json.loads(p.headings_json), "element_count": len(json.loads(p.elements_json)), "links": json.loads(p.links_json)}
                  for p in repo.scoped(session, m.Page, tenant, product_id)],
        "features": [{"id": f.id, "name": f.name, "slug": f.slug, "kind": f.kind, "description": f.description, "route": f.route,
                      "nav_path": json.loads(f.nav_path_json), "elements": json.loads(f.elements_json), "questions": json.loads(f.questions_json)} for f in features],
        "navigation": [{"from": e.from_path, "to": e.to_path, "selector": e.selector, "label": e.label} for e in repo.scoped(session, m.NavigationEdge, tenant, product_id)],
        "qna": [{"id": q.id, "feature_id": q.feature_id, "question": q.question, "answer": q.answer} for q in repo.scoped(session, m.QnA, tenant, product_id)],
        "demo_flows": [{"id": d.id, "feature_id": d.feature_id, "name": d.name, "description": d.description, "steps": json.loads(d.steps_json)} for d in repo.scoped(session, m.DemoFlow, tenant, product_id)],
    }
