"""Widget API: keyed by public product_id; tenant is resolved from the product row."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models as m
from .. import repo
from ..agent import chat
from ..db import get_session
from ..schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/widget", tags=["widget"])
SessionDep = Annotated[Session, Depends(get_session)]


def _product(session: Session, product_id: str) -> m.Product:
    product = repo.get_product_any_tenant(session, product_id)
    if product is None:
        raise HTTPException(404, "product not registered")
    return product


@router.get("/config")
def config(product_id: str, session: SessionDep):
    product = _product(session, product_id)
    features = repo.scoped(session, m.Feature, product.tenant_id, product.id)
    actions = [f for f in features if f.kind == "action"][:2]
    pages = [f for f in features if f.kind == "page" and f.route != "/"][:2]
    return {
        "product_name": product.name, "status": product.status, "ready": product.status == "READY", "description": product.description,
        "suggestions": ["What does this product do?"] + [f"Take me to {f.name.lower()}" for f in pages[:1]] + [f"Show me how to {f.name.lower()}" for f in actions],
    }


@router.get("/sessions/{session_id}/messages")
def messages(session_id: str, product_id: str, session: SessionDep):
    product = _product(session, product_id)
    return [
        {"id": msg.id, "role": msg.role, "content": msg.content, "meta": json.loads(msg.meta_json), "created_at": msg.created_at.isoformat()}
        for msg in repo.list_messages(session, product.tenant_id, product.id, session_id)
    ]


@router.post("/chat", response_model=ChatResponse)
def post_chat(body: ChatRequest, session: SessionDep):
    product = _product(session, body.product_id)
    text = body.message.strip()
    if not text:
        raise HTTPException(422, "empty message")
    response = chat.handle_message(session, product, body.session_id, text[:1000])
    session.commit()
    return response
