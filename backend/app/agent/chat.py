"""Chat orchestrator: one entry point that classifies intent, consults knowledge, and may start a demo run."""

import json
import logging

from sqlalchemy.orm import Session

from .. import models as m
from .. import repo
from ..schemas import ChatResponse, DemoAction, DemoRunOut
from . import demo, knowledge, llm
from .intent import FeatureIndex, Intent, classify, match_feature

log = logging.getLogger(__name__)


def handle_message(session: Session, product: m.Product, session_id: str, text: str) -> ChatResponse:
    tenant_id, product_id = product.tenant_id, product.id
    repo.ensure_session(session, tenant_id, product_id, session_id)
    repo.add_message(session, tenant_id, product_id, session_id, "user", text)

    features = knowledge.load_features(session, tenant_id, product_id)
    if not features:
        return _finish(session, product, session_id, ChatResponse(
            reply=f"I'm still learning about {product.name} — the knowledge base is being built. Please try again in a moment.", intent=Intent.UNKNOWN))

    intent = classify(text)
    feature = match_feature(text, features, intent)
    log.info("chat [%s] intent=%s feature=%s text=%r", session_id, intent, feature.slug if feature else None, text)

    if intent == Intent.DEMO_REQUEST:
        response = _demo(session, product, session_id, feature, features)
    elif intent == Intent.NAVIGATION_REQUEST:
        response = _navigate(session, product, session_id, feature, features)
    elif feature is not None:
        response = _feature_answer(session, product, feature, text)
    else:
        response = _general_answer(session, product, text, features)
    return _finish(session, product, session_id, response)


def _finish(session: Session, product: m.Product, session_id: str, response: ChatResponse) -> ChatResponse:
    meta = {"intent": response.intent, "demo_run_id": response.demo_run.id if response.demo_run else None, "suggestions": response.suggestions}
    repo.add_message(session, product.tenant_id, product.id, session_id, "assistant", response.reply, meta)
    return response


# ---- intents --------------------------------------------------------------------------


def _demo(session: Session, product: m.Product, session_id: str, feature: FeatureIndex | None, features: list[FeatureIndex]) -> ChatResponse:
    flow = repo.demo_flow_for_feature(session, product.tenant_id, product.id, feature.id) if feature else None
    if feature is None or flow is None:
        options = [f for f in features if f.kind == "action"][:4] or features[:4]
        return ChatResponse(
            reply="I can walk you through these live: " + ", ".join(f.name for f in options) + ". Which one would you like to see?",
            intent=Intent.DEMO_REQUEST, suggestions=[f"Show me how to {f.name.lower()}" for f in options],
        )
    steps = [DemoAction(**s) for s in json.loads(flow.steps_json)]
    run = demo.start_run(session, product.tenant_id, product.id, session_id, flow.name, steps)
    verb = f"how to {feature.name.lower()}" if feature.kind == "action" else feature.name
    return ChatResponse(
        reply=f"Sure — I'll show you {verb}. Watch the screen; I'll explain each step as we go.",
        intent=Intent.DEMO_REQUEST, demo_run=DemoRunOut(id=run.id, title=flow.name, total_steps=len(steps)),
    )


def _navigate(session: Session, product: m.Product, session_id: str, feature: FeatureIndex | None, features: list[FeatureIndex]) -> ChatResponse:
    if feature is None:
        pages = [f for f in features if f.kind == "page"][:6]
        return ChatResponse(
            reply="Where would you like to go? I can open: " + ", ".join(f.name for f in pages) + ".",
            intent=Intent.NAVIGATION_REQUEST, suggestions=[f"Take me to {f.name.lower()}" for f in pages[:4]],
        )
    step = DemoAction(type="navigate", path=feature.route, label=feature.name)
    run = demo.start_run(session, product.tenant_id, product.id, session_id, f"Open {feature.name}", [step])
    suggestions = [f"Show me how to {feature.name.lower()}"] if feature.kind == "action" else _suggestions_for(feature, features)
    where = knowledge.location_text(feature.nav_path, feature.kind)
    return ChatResponse(
        reply=f"Sure — opening {feature.name}. You'll find it under {where}.", intent=Intent.NAVIGATION_REQUEST,
        demo_run=DemoRunOut(id=run.id, title=f"Open {feature.name}", total_steps=1), suggestions=suggestions,
    )


def _feature_answer(session: Session, product: m.Product, feature: FeatureIndex, text: str) -> ChatResponse:
    hits = knowledge.search_qna(session, product.tenant_id, product.id, text, feature_id=feature.id)
    where = knowledge.location_text(feature.nav_path, feature.kind)
    answer = hits[0][1].answer if hits and hits[0][0] >= 0.5 else f"{feature.description} You'll find it under {where}."
    composed = _compose_with_llm(product, text, [f"{feature.name}: {feature.description} (under {where})"] + [f"Q: {q.question} A: {q.answer}" for _, q in hits])
    suggestions = [f"Show me how to {feature.name.lower()}"] if feature.kind == "action" else [f"Take me to {feature.name.lower()}", f"Show me {feature.name.lower()}"]
    return ChatResponse(reply=composed or answer, intent=Intent.FEATURE_QA, suggestions=suggestions)


def _general_answer(session: Session, product: m.Product, text: str, features: list[FeatureIndex]) -> ChatResponse:
    hits = knowledge.search_qna(session, product.tenant_id, product.id, text)
    chunks = knowledge.search_chunks(session, product.tenant_id, product.id, text)
    overview = product.description or next((q.answer for _, q in hits if q.question.startswith("What does")), "")
    context = [overview] + [f"Q: {q.question} A: {q.answer}" for _, q in hits] + [f"{c.title}: {c.text[:400]}" for c in chunks]
    composed = _compose_with_llm(product, text, context)
    actions = [f for f in features if f.kind == "action"][:3]
    suggestions = [f"Show me how to {f.name.lower()}" for f in actions] or [f"Take me to {f.name.lower()}" for f in features[:3]]
    if composed:
        return ChatResponse(reply=composed, intent=Intent.GENERAL_QA, suggestions=suggestions)
    if hits and hits[0][0] >= 0.4:
        return ChatResponse(reply=hits[0][1].answer, intent=Intent.GENERAL_QA, suggestions=suggestions)
    if chunks:
        return ChatResponse(reply=f"Here's what I found: {chunks[0].text[:300].rstrip()}…", intent=Intent.GENERAL_QA, suggestions=suggestions)
    if overview:
        return ChatResponse(reply=f"{overview} What would you like to explore?", intent=Intent.GENERAL_QA, suggestions=suggestions)
    return ChatResponse(reply="I'm not sure about that yet. I can answer questions about the product, open a page, or show you how to do something.", intent=Intent.UNKNOWN, suggestions=suggestions)


def _suggestions_for(feature: FeatureIndex, features: list[FeatureIndex]) -> list[str]:
    """Action features that live under this page (any action when on the home page)."""
    related = [f for f in features if f.kind == "action" and (feature.route == "/" or f.route.startswith(feature.route))][:2]
    return [f"Show me how to {f.name.lower()}" for f in related]


def _compose_with_llm(product: m.Product, question: str, context: list[str]) -> str | None:
    if not llm.enabled:
        return None
    return llm.complete(
        system=(f"You are the friendly AI sales engineer for {product.name}. Answer the visitor's question in 1-3 short sentences using ONLY the product knowledge provided. "
                "If the knowledge doesn't cover it, say so honestly and suggest a related feature. You can offer to show features live. No markdown headers."),
        user="Product knowledge:\n" + "\n".join(f"- {c}" for c in context if c) + f"\n\nVisitor question: {question}",
        max_tokens=1500,
    )
