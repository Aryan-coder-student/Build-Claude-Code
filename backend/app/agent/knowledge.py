"""Knowledge retrieval: structured feature lookup + token-overlap text search (no vector infra)."""

import json

from sqlalchemy.orm import Session

from .. import models as m
from .. import repo
from .intent import FeatureIndex, tokens


def location_text(nav_path: list[str], kind: str) -> str:
    """Human-readable place in the product, e.g. 'Analytics › Reports' or 'the main navigation'."""
    path = nav_path[:-1] if kind == "action" else nav_path
    return " › ".join(path) if len(path) > 1 else f"{path[0]} in the main navigation" if path else "the main navigation"


def load_features(session: Session, tenant_id: str, product_id: str) -> list[FeatureIndex]:
    return [
        FeatureIndex(
            id=f.id, name=f.name, slug=f.slug, kind=f.kind, description=f.description, route=f.route,
            nav_path=json.loads(f.nav_path_json), keywords=json.loads(f.keywords_json), questions=json.loads(f.questions_json),
        )
        for f in repo.scoped(session, m.Feature, tenant_id, product_id)
    ]


def _overlap(query: list[str], text: str) -> float:
    tt = set(tokens(text))
    return len(set(query) & tt) / (len(set(query)) or 1)


def search_qna(session: Session, tenant_id: str, product_id: str, message: str, feature_id: str | None = None, limit: int = 3) -> list[tuple[float, m.QnA]]:
    query = tokens(message)
    rows = repo.scoped(session, m.QnA, tenant_id, product_id)
    if feature_id:
        rows = [r for r in rows if r.feature_id == feature_id] or rows
    scored = sorted(((_overlap(query, r.question), r) for r in rows), key=lambda x: x[0], reverse=True)
    return [(s, r) for s, r in scored[:limit] if s > 0]


def search_chunks(session: Session, tenant_id: str, product_id: str, message: str, limit: int = 4) -> list[m.KnowledgeChunk]:
    query = tokens(message)
    rows = repo.scoped(session, m.KnowledgeChunk, tenant_id, product_id)
    scored = sorted(((len(set(query) & set(tokens(r.title + " " + r.text))), r) for r in rows), key=lambda x: x[0], reverse=True)
    return [r for s, r in scored[:limit] if s > 0]
