"""Thin Claude wrapper. Disabled (enabled=False) when no credentials resolve; callers must have a fallback."""

import logging
from typing import TypeVar

from pydantic import BaseModel

from ..config import settings

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

_client = None
enabled = False

if settings.llm_enabled:
    try:
        import anthropic

        headers = {"anthropic-workspace-id": settings.anthropic_workspace_id} if settings.anthropic_workspace_id else {}
        _candidate = anthropic.Anthropic(max_retries=1, timeout=180.0, default_headers=headers)
        # The SDK resolves ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN / `ant auth login` profiles.
        if _candidate.api_key or getattr(_candidate, "auth_token", None):
            _client = _candidate
            enabled = True
    except Exception as exc:  # pragma: no cover - depends on environment
        log.info("LLM disabled: %s", exc)

log.info("LLM enrichment %s (model=%s)", "enabled" if enabled else "disabled", settings.llm_model)


def complete(system: str, user: str, max_tokens: int = 2000) -> str | None:
    """Short chat-style completion at low effort (fast answers). Returns None when disabled or on any API error."""
    if not enabled or _client is None:
        return None
    try:
        response = _client.messages.create(
            model=settings.llm_model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}], output_config={"effort": "low"},
        )
        if response.stop_reason != "end_turn":
            log.warning("LLM completion stopped early: %s", response.stop_reason)
            return None
        return "".join(block.text for block in response.content if block.type == "text").strip() or None
    except Exception as exc:
        log.warning("LLM completion failed: %s", exc)
        return None


def parse(system: str, user: str, schema: type[T], max_tokens: int = 4096) -> T | None:
    """Structured output validated against a Pydantic model. Returns None when disabled or on error."""
    if not enabled or _client is None:
        return None
    try:
        response = _client.messages.parse(
            model=settings.llm_model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}], output_format=schema,
        )
        return response.parsed_output
    except Exception as exc:
        log.warning("LLM structured call failed: %s", exc)
        return None
