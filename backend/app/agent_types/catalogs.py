"""Reference catalogs used to validate selector parameters."""

from __future__ import annotations

from app.agents import HOSTED_AGENTS
from app.config import get_settings
from app.tools import TOOL_IMPLS

DATA_SOURCE_CATALOG: tuple[tuple[str, str], ...] = (
    ("session_transcripts", "Session transcripts"),
    ("gathering_documents", "Gathering documents"),
    ("agent_registry", "Agent registry"),
    ("postgres_metrics", "PostgreSQL metrics"),
    ("uploaded_documents", "Uploaded documents"),
    ("vector_index", "Vector index"),
    ("external_api", "External API"),
    ("web_search", "Web search"),
    ("policy_library", "Policy library"),
    ("evaluation_datasets", "Evaluation datasets"),
    ("memory_store", "Memory store"),
)

DATA_SOURCE_KEYS: frozenset[str] = frozenset(key for key, _ in DATA_SOURCE_CATALOG)

_BASE_MODELS: tuple[tuple[str, str], ...] = (
    ("gpt-4o", "GPT-4o"),
    ("gpt-4o-mini", "GPT-4o mini"),
    ("gpt-4.1", "GPT-4.1"),
    ("gpt-4.1-mini", "GPT-4.1 mini"),
    ("o4-mini", "o4-mini"),
)


def model_catalog() -> tuple[tuple[str, str], ...]:
    configured = get_settings().openai_model
    if configured and configured not in {key for key, _ in _BASE_MODELS}:
        return ((configured, configured), *_BASE_MODELS)
    return _BASE_MODELS


def model_keys() -> frozenset[str]:
    return frozenset(key for key, _ in model_catalog())


def tool_catalog() -> tuple[tuple[str, str], ...]:
    """Tools the runtime can execute, plus hosted agent keys usable as tools."""
    tools = tuple((name, name) for name in sorted(TOOL_IMPLS))
    hosted = tuple((key, f"{key} (hosted agent)") for key in sorted(HOSTED_AGENTS))
    return tools + hosted


def tool_keys() -> frozenset[str]:
    return frozenset(key for key, _ in tool_catalog())
