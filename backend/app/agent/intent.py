"""Deterministic intent classification and feature matching."""

import re
from dataclasses import dataclass, field
from enum import StrEnum


class Intent(StrEnum):
    GENERAL_QA = "GENERAL_QA"
    FEATURE_QA = "FEATURE_QA"
    NAVIGATION_REQUEST = "NAVIGATION_REQUEST"
    DEMO_REQUEST = "DEMO_REQUEST"
    UNKNOWN = "UNKNOWN"


# "How do I…?" is a question: it gets an answer plus a "Show me how" suggestion. Explicit asks to be shown start a demo.
DEMO_RE = re.compile(r"\b(show me how|show (me )?(a )?demo|walk me through|demo(nstrate)?|guide me|teach me|step[- ]by[- ]step|let me see how)\b", re.I)
NAV_RE = re.compile(r"\b(take me|go to|goto|open|navigate|bring me|jump to|switch to|show me the|show me|where is|where (can|do|would) i|get me to)\b", re.I)
OVERVIEW_RE = re.compile(r"\b(what (does|is) (this|the) (product|app|tool|software)|what (can|do) (you|i) do|what features|tell me about (this|the product)|overview|hi|hello|hey)\b", re.I)

STOP = {"the", "a", "an", "to", "of", "and", "or", "for", "in", "on", "me", "i", "you", "my", "this", "that", "is", "it", "do", "does", "can", "how", "show", "take", "go", "open", "want", "please", "with", "your", "feature", "page", "section", "tab", "have", "there", "any", "what", "where", "support", "supports", "product", "app"}


def stem(word: str) -> str:
    for suffix in ("ings", "ing", "ies", "es", "s", "ed"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return word


def tokens(text: str) -> list[str]:
    return [stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP]


@dataclass
class FeatureIndex:
    id: str
    name: str
    slug: str
    kind: str  # page | action
    description: str
    route: str
    nav_path: list[str]
    keywords: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)

    def score(self, message_tokens: list[str]) -> float:
        name_tokens = set(tokens(self.name))
        keyword_tokens = set(stem(k) for k in self.keywords) | set(tokens(" ".join(self.questions)))
        mt = set(message_tokens)
        return 2.0 * len(mt & name_tokens) + 0.5 * len(mt & keyword_tokens)


def classify(message: str) -> Intent:
    if DEMO_RE.search(message):
        return Intent.DEMO_REQUEST
    if NAV_RE.search(message):
        return Intent.NAVIGATION_REQUEST
    if OVERVIEW_RE.search(message):
        return Intent.GENERAL_QA
    return Intent.FEATURE_QA  # refined to GENERAL_QA / UNKNOWN by the orchestrator when nothing matches


def match_feature(message: str, features: list[FeatureIndex], intent: Intent) -> FeatureIndex | None:
    """Best feature by token overlap. Demo requests prefer action features; navigation prefers pages."""
    mt = tokens(message)
    if not mt:
        return None
    preferred = "action" if intent == Intent.DEMO_REQUEST else "page" if intent == Intent.NAVIGATION_REQUEST else ""
    ranked = sorted(features, key=lambda f: (f.score(mt), f.kind == preferred), reverse=True)
    best = ranked[0] if ranked and ranked[0].score(mt) > 0 else None
    if best is None:
        return None
    # A same-score alternative of the preferred kind wins (e.g. "Create Report" over "Reports" for demos).
    for f in ranked:
        if f.score(mt) == best.score(mt) and f.kind == preferred:
            return f
    return best
