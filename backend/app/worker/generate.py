"""Generate Q&A, demo flows, and knowledge chunks from features (deterministic, optional Claude enrichment)."""

import json
import logging

from pydantic import BaseModel

from ..agent import llm
from ..agent.knowledge import location_text
from ..schemas import CrawledPage, DemoAction, DemoFlowSpec, FeatureSpec, QnASpec

log = logging.getLogger(__name__)


def _join(items: list[str]) -> str:
    return ", ".join(items[:-1]) + f" and {items[-1]}" if len(items) > 1 else "".join(items)


def product_overview(product_name: str, features: list[FeatureSpec]) -> str:
    pages = [f.name for f in features if f.kind == "page" and f.route != "/"]
    actions = [f.name.lower() for f in features if f.kind == "action"]
    text = f"{product_name} includes {_join(pages)}." if pages else f"{product_name} is a web product."
    if actions:
        text += f" You can {_join(actions)}."
    return text


def generate_qna(product_name: str, features: list[FeatureSpec], description: str = "") -> list[QnASpec]:
    """Claude writes the Q&A from the discovered structure when available; templates are the fallback."""
    ai = _ai_qna(product_name, features, description)
    return ai if ai else templated_qna(product_name, features)


def templated_qna(product_name: str, features: list[FeatureSpec]) -> list[QnASpec]:
    overview = product_overview(product_name, features)
    qna = [
        QnASpec(question="What does this product do?", answer=overview),
        QnASpec(question="What features do you have?", answer=overview + (" Ask me to show you any of them." if len(features) > 1 else " Ask me anything about it.")),
    ]
    for f in features:
        where = location_text(f.nav_path, f.kind)
        if f.kind == "page":
            qna += [
                QnASpec(feature_slug=f.slug, question=f"Does this product have {f.name.lower()}?", answer=f"Yes. {f.description} You can find it under {where}."),
                QnASpec(feature_slug=f.slug, question=f"What does the {f.name} page show?", answer=f.description),
                QnASpec(feature_slug=f.slug, question=f"Where can I find {f.name.lower()}?", answer=f"{f.name} is under {where}. Say 'take me to {f.name.lower()}' and I'll open it."),
            ]
        else:
            inputs = [e.name for e in f.elements if e.role == "input"]
            trigger = next((e.name for e in f.elements if e.role == "trigger"), f.name)
            how = f"Go to {where}, then click '{trigger}'." + (f" Fill in {_join(inputs[:4])}." if inputs else "")
            qna += [
                QnASpec(feature_slug=f.slug, question=f"How do I {f.name.lower()}?", answer=how + " Say 'show me how' and I'll walk you through it live."),
                QnASpec(feature_slug=f.slug, question=f"Can I {f.name.lower()}?", answer=f"Yes. {how}"),
            ]
    return qna


def _sample_value(name: str, placeholder: str = "") -> str:
    if placeholder.lower().startswith("e.g."):
        return placeholder[4:].strip()
    lname = name.lower()
    if "email" in lname:
        return "alex@example.com"
    if "name" in lname:
        return "Weekly Overview"
    return "Demo"


def generate_demos(features: list[FeatureSpec], pages: list[CrawledPage]) -> list[DemoFlowSpec]:
    placeholders = {e.selector: e.placeholder for p in pages for e in p.elements + [r for i in p.interactions for r in i.revealed]}
    flows: list[DemoFlowSpec] = []
    for f in features:
        steps: list[DemoAction] = [DemoAction(type="navigate", path=f.page_path)]
        if f.kind == "page":
            steps += [
                DemoAction(type="highlight", selector="main h1, h1, h2, h3, h4, h5, h6", label=f.name, message=f"This is {f.name}. {f.description}"),
                DemoAction(type="explain", message=f"That's the {f.name} area. Ask me about anything you see here."),
            ]
        else:
            trigger = next((e for e in f.elements if e.role == "trigger"), None)
            inputs = [e for e in f.elements if e.role == "input"][:3]
            if trigger is None:
                continue
            steps += [
                DemoAction(type="highlight", selector=trigger.selector, message=f"Use the '{trigger.name}' button to {f.name.lower()}."),
                DemoAction(type="click", selector=trigger.selector),
                DemoAction(type="wait", ms=500),
            ]
            for i, inp in enumerate(inputs):
                steps.append(DemoAction(type="highlight", selector=inp.selector, message=f"{'Start by entering' if i == 0 else 'Then set'} the {inp.name.lower()} here."))
                if i == 0 and "select" not in inp.selector:
                    steps.append(DemoAction(type="type", selector=inp.selector, value=_sample_value(inp.name, placeholders.get(inp.selector, ""))))
            steps.append(DemoAction(type="explain", message=f"That's how you {f.name.lower()}. Want me to show you anything else?"))
        flows.append(DemoFlowSpec(feature_slug=f.slug, name=f.name if f.kind == "action" else f"Tour: {f.name}", description=f.description, steps=steps))
    return flows


def generate_chunks(pages: list[CrawledPage], features: list[FeatureSpec], size: int = 700) -> list[tuple[str, str, str, str]]:
    """(source_type, source_key, title, text) tuples."""
    chunks: list[tuple[str, str, str, str]] = []
    for page in pages:
        text = " ".join(page.text.split())
        for i in range(0, max(len(text), 1), size):
            chunks.append(("page", page.path, page.title, text[i : i + size]))
    for f in features:
        chunks.append(("feature", f.slug, f.name, f"{f.name}: {f.description} Location: {' › '.join(f.nav_path)}."))
    return chunks


# ---- optional Claude enrichment ------------------------------------------------------


class _GeneratedQnA(BaseModel):
    class Item(BaseModel):
        feature_slug: str  # "" for product-level questions
        question: str
        answer: str

    items: list[Item]


def _ai_qna(product_name: str, features: list[FeatureSpec], description: str) -> list[QnASpec]:
    if not llm.enabled or not features:
        return []
    payload = [f.model_dump(include={"slug", "name", "kind", "description", "route", "nav_path", "elements"}) for f in features]
    result = llm.parse(
        system=("You write the Q&A knowledge base for an AI sales engineer embedded in a SaaS product. Use ONLY the discovered structure "
                "provided; never invent features, pricing, or integrations. Answers: 1-3 friendly, concrete sentences that mention where the "
                "feature lives (navigation path) and, for actions, the steps (button to click, fields to fill). Include 'What does this product do?' "
                "and 'What features do you have?' as product-level items (feature_slug \"\"), then 3-4 questions per feature phrased the way "
                "prospects actually ask (capabilities, how-to, where-is, comparisons within the product)."),
        user=f"Product: {product_name}\nDescription: {description}\nFeatures (JSON):\n{json.dumps(payload, indent=1)}",
        schema=_GeneratedQnA, max_tokens=12000,
    )
    if result is None or len(result.items) < 3:
        return []
    slugs = {f.slug for f in features}
    log.info("LLM generated %d Q&A items", len(result.items))
    return [QnASpec(feature_slug=i.feature_slug if i.feature_slug in slugs else "", question=i.question.strip(), answer=i.answer.strip()) for i in result.items if i.question and i.answer]


class _Enriched(BaseModel):
    class Item(BaseModel):
        slug: str
        description: str
        extra_questions: list[str]

    product_description: str
    features: list[Item]


def enrich_features(product_name: str, features: list[FeatureSpec]) -> tuple[str, list[FeatureSpec]]:
    """Ask Claude for better descriptions and more user questions. Deterministic output if disabled or failing."""
    overview = product_overview(product_name, features)
    if not llm.enabled:
        return overview, features
    payload = [f.model_dump(include={"slug", "name", "kind", "route", "nav_path", "description", "elements"}) for f in features]
    result = llm.parse(
        system="You are a product marketing engineer writing concise, factual product knowledge for a sales chatbot. Never invent capabilities that are not evidenced by the provided UI structure.",
        user=f"Product: {product_name}\nDiscovered features (JSON):\n{json.dumps(payload, indent=1)}\n\nWrite a 1-2 sentence product description and, for every feature slug, a crisp 1-2 sentence description plus 3 natural questions a prospect might ask about it.",
        schema=_Enriched,
    )
    if result is None:
        return overview, features
    by_slug = {item.slug: item for item in result.features}
    enriched = []
    for f in features:
        item = by_slug.get(f.slug)
        if item:
            f = f.model_copy(update={"description": item.description, "questions": list(dict.fromkeys(f.questions + item.extra_questions))})
        enriched.append(f)
    log.info("LLM enriched %d/%d features", len(by_slug), len(features))
    return result.product_description or overview, enriched
