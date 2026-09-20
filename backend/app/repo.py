"""Tenant-scoped data access. Every product-scoped read/write takes tenant_id AND product_id."""

import json
from typing import TypeVar

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from . import models as m
from .ids import new_id

T = TypeVar("T")


def scoped(session: Session, model: type[T], tenant_id: str, product_id: str) -> list[T]:
    return list(session.scalars(select(model).where(model.tenant_id == tenant_id, model.product_id == product_id)))


def clear_scoped(session: Session, model, tenant_id: str, product_id: str) -> None:
    session.execute(delete(model).where(model.tenant_id == tenant_id, model.product_id == product_id))


def count_scoped(session: Session, model, tenant_id: str, product_id: str) -> int:
    return session.scalar(select(func.count()).select_from(model).where(model.tenant_id == tenant_id, model.product_id == product_id)) or 0


# ---- tenants / products -------------------------------------------------------------


def ensure_tenant(session: Session, tenant_id: str, name: str) -> m.Tenant:
    tenant = session.get(m.Tenant, tenant_id)
    if tenant is None:
        tenant = m.Tenant(id=tenant_id, name=name)
        session.add(tenant)
        session.flush()
    return tenant


def get_product(session: Session, tenant_id: str, product_id: str) -> m.Product | None:
    product = session.get(m.Product, product_id)
    return product if product is not None and product.tenant_id == tenant_id else None


def get_product_any_tenant(session: Session, product_id: str) -> m.Product | None:
    """Widget entry point: the product id is the public key; tenant comes from the row."""
    return session.get(m.Product, product_id)


def list_products(session: Session, tenant_id: str) -> list[m.Product]:
    return list(session.scalars(select(m.Product).where(m.Product.tenant_id == tenant_id).order_by(m.Product.created_at)))


def product_counts(session: Session, tenant_id: str, product_id: str) -> dict[str, int]:
    return {
        "pages": count_scoped(session, m.Page, tenant_id, product_id),
        "features": count_scoped(session, m.Feature, tenant_id, product_id),
        "questions": count_scoped(session, m.QnA, tenant_id, product_id),
        "demo_flows": count_scoped(session, m.DemoFlow, tenant_id, product_id),
    }


# ---- jobs -----------------------------------------------------------------------------


def create_job(session: Session, tenant_id: str, product_id: str) -> m.CrawlJob:
    job = m.CrawlJob(id=new_id("job"), tenant_id=tenant_id, product_id=product_id)
    session.add(job)
    session.flush()
    return job


def latest_job(session: Session, tenant_id: str, product_id: str) -> m.CrawlJob | None:
    return session.scalars(
        select(m.CrawlJob)
        .where(m.CrawlJob.tenant_id == tenant_id, m.CrawlJob.product_id == product_id)
        .order_by(m.CrawlJob.created_at.desc())
    ).first()


def update_job(session: Session, job_id: str, **fields) -> None:
    job = session.get(m.CrawlJob, job_id)
    if job is None:
        return
    if "stats" in fields:
        job.stats_json = json.dumps(fields.pop("stats"))
    for key, value in fields.items():
        setattr(job, key, value)


# ---- knowledge ---------------------------------------------------------------------


def replace_knowledge(session: Session, tenant_id: str, product_id: str, rows: list) -> None:
    """Delete all knowledge for the product and insert the new rows (idempotent re-index)."""
    for model in (m.Page, m.Feature, m.NavigationEdge, m.QnA, m.DemoFlow, m.KnowledgeChunk):
        clear_scoped(session, model, tenant_id, product_id)
    session.add_all(rows)


def feature_by_slug(session: Session, tenant_id: str, product_id: str, slug: str) -> m.Feature | None:
    return session.scalars(
        select(m.Feature).where(m.Feature.tenant_id == tenant_id, m.Feature.product_id == product_id, m.Feature.slug == slug)
    ).first()


def demo_flow_for_feature(session: Session, tenant_id: str, product_id: str, feature_id: str) -> m.DemoFlow | None:
    return session.scalars(
        select(m.DemoFlow).where(m.DemoFlow.tenant_id == tenant_id, m.DemoFlow.product_id == product_id, m.DemoFlow.feature_id == feature_id)
    ).first()


# ---- chat ------------------------------------------------------------------------------


def ensure_session(session: Session, tenant_id: str, product_id: str, session_id: str) -> m.ChatSession:
    chat = session.get(m.ChatSession, (session_id, product_id))
    if chat is None:
        chat = m.ChatSession(id=session_id, tenant_id=tenant_id, product_id=product_id)
        session.add(chat)
        session.flush()
    return chat


def list_messages(session: Session, tenant_id: str, product_id: str, session_id: str) -> list[m.ChatMessage]:
    return list(
        session.scalars(
            select(m.ChatMessage)
            .where(m.ChatMessage.tenant_id == tenant_id, m.ChatMessage.product_id == product_id, m.ChatMessage.session_id == session_id)
            .order_by(m.ChatMessage.seq)
        )
    )


def add_message(session: Session, tenant_id: str, product_id: str, session_id: str, role: str, content: str, meta: dict | None = None) -> m.ChatMessage:
    seq = (
        session.scalar(
            select(func.max(m.ChatMessage.seq)).where(
                m.ChatMessage.tenant_id == tenant_id, m.ChatMessage.product_id == product_id, m.ChatMessage.session_id == session_id
            )
        )
        or 0
    ) + 1
    msg = m.ChatMessage(
        id=new_id("msg"), tenant_id=tenant_id, product_id=product_id, session_id=session_id,
        role=role, content=content, meta_json=json.dumps(meta or {}), seq=seq,
    )
    session.add(msg)
    session.flush()
    return msg


def get_run(session: Session, tenant_id: str, product_id: str, run_id: str) -> m.DemoRun | None:
    run = session.get(m.DemoRun, run_id)
    return run if run is not None and run.tenant_id == tenant_id and run.product_id == product_id else None


def get_run_any_tenant(session: Session, run_id: str) -> m.DemoRun | None:
    return session.get(m.DemoRun, run_id)
