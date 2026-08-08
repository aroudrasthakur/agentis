"""Guards keeping human-in-the-loop concerns out of agent type definitions.

Human review, approval, and intervention are runtime concerns (see
``app.services.hitl`` and the orchestration flow). Agent type schemas — built-in
or user-authored — must never declare them.
"""

from __future__ import annotations

import re
from typing import Any

FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"approval",
        r"\bapprove\w*",
        r"\bapprover\w*",
        r"\breviewer\w*",
        r"human[\s_-]*review",
        r"review[\s_-]*(threshold|timeout|stage|policy|policies|condition|conditions|step|steps)",
        r"human[\s_-]*in[\s_-]*the[\s_-]*loop",
        r"\bhitl\b",
        r"human[\s_-]*intervention",
        r"intervention[\s_-]*(trigger|triggers|polic\w+|rule|rules)",
        r"escalation",
        r"\bescalate\w*",
        r"human[\s_-]*override",
        r"rejection[\s_-]*behavio\w*",
        r"workflow[\s_-]*resumption",
        r"resume[\s_-]*after[\s_-]*approval",
        r"sign[\s_-]?off",
    )
)

class ForbiddenAgentTypeFieldError(ValueError):
    """Raised when an agent type schema declares human-in-the-loop configuration."""


def find_forbidden_terms(value: Any, *, path: str = "") -> list[str]:
    """Return human-readable locations where forbidden HITL wording appears."""
    findings: list[str] = []

    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            findings.extend(_scan_text(str(key), child_path))
            findings.extend(find_forbidden_terms(item, path=child_path))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            findings.extend(find_forbidden_terms(item, path=f"{path}[{index}]"))
    elif isinstance(value, str):
        findings.extend(_scan_text(value, path or "value"))

    return findings


def _scan_text(text: str, path: str) -> list[str]:
    return [
        f"{path}: contains disallowed human-in-the-loop wording ({pattern.pattern})"
        for pattern in FORBIDDEN_PATTERNS
        if pattern.search(text)
    ]


def assert_no_human_loop_fields(payload: Any, *, label: str = "agent type") -> None:
    """Raise when a schema payload declares approval/review/intervention config."""
    findings = find_forbidden_terms(payload)
    if findings:
        raise ForbiddenAgentTypeFieldError(
            f"{label} may not define human approval, review, or intervention "
            f"configuration: {'; '.join(findings[:5])}"
        )
