"""Request-scoped active role assignment (from JWT)."""

from __future__ import annotations

from contextvars import ContextVar
from uuid import UUID

_session_assignment_id: ContextVar[UUID | None] = ContextVar(
    "session_assignment_id", default=None
)


def set_session_assignment_id(assignment_id: UUID | None) -> None:
    _session_assignment_id.set(assignment_id)


def get_session_assignment_id() -> UUID | None:
    return _session_assignment_id.get()


def clear_session_assignment_id() -> None:
    _session_assignment_id.set(None)
