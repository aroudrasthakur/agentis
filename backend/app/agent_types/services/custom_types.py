"""Create, version, duplicate, and archive user-defined agent types.

Custom types are declarative data only: parameters, validation rules, and metric
definitions. No executable code and no human-in-the-loop configuration.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_types.builtin import BASE_PARAMETER_KEYS, BUILT_IN_AGENT_TYPES
from app.agent_types.guards import ForbiddenAgentTypeFieldError, assert_no_human_loop_fields
from app.agent_types.schemas import (
    AgentMetricDefinition,
    AgentTypeParameterDefinition,
    CustomAgentTypeCreate,
    CustomAgentTypeUpdate,
)
from app.agent_types.services import registry
from app.models import CustomAgentType, CustomAgentTypeStatus, User

KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


class CustomAgentTypeError(ValueError):
    """Raised when a custom type payload is not acceptable."""


def _check_parameters(parameters: Iterable[AgentTypeParameterDefinition]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    serialized: list[dict[str, Any]] = []

    for parameter in parameters:
        if not KEY_PATTERN.fullmatch(parameter.key):
            raise CustomAgentTypeError(
                f"Parameter key '{parameter.key}' must be lowercase snake_case."
            )
        if parameter.key in seen:
            raise CustomAgentTypeError(f"Duplicate parameter key '{parameter.key}'.")
        if parameter.key in BASE_PARAMETER_KEYS:
            raise CustomAgentTypeError(
                f"'{parameter.key}' is a shared base parameter and cannot be redefined."
            )
        seen.add(parameter.key)

        if parameter.validation and parameter.validation.pattern:
            try:
                re.compile(parameter.validation.pattern)
            except re.error as exc:
                raise CustomAgentTypeError(
                    f"Invalid pattern for '{parameter.key}': {exc}"
                ) from exc

        if parameter.visible_when and parameter.visible_when.parameter_key == parameter.key:
            raise CustomAgentTypeError(
                f"Parameter '{parameter.key}' cannot depend on its own visibility."
            )

        # Stable, generated id — never the display name.
        serialized.append(
            parameter.model_copy(update={"id": parameter.id or str(uuid.uuid4()), "inherited": False})
            .model_dump(mode="json", by_alias=True)
        )

    return serialized


def _check_metrics(metrics: Iterable[AgentMetricDefinition]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    serialized: list[dict[str, Any]] = []
    for metric in metrics:
        if not KEY_PATTERN.fullmatch(metric.key):
            raise CustomAgentTypeError(f"Metric key '{metric.key}' must be lowercase snake_case.")
        if metric.key in seen:
            raise CustomAgentTypeError(f"Duplicate metric key '{metric.key}'.")
        seen.add(metric.key)
        serialized.append(
            metric.model_copy(update={"id": metric.id or str(uuid.uuid4())}).model_dump(
                mode="json", by_alias=True
            )
        )
    return serialized


def _check_base_type(base_type_id: str | None) -> None:
    if base_type_id in (None, ""):
        return
    if base_type_id == "custom" or base_type_id not in BUILT_IN_AGENT_TYPES:
        raise CustomAgentTypeError(f"'{base_type_id}' is not a built-in agent type.")


def _guard_payload(payload: Any) -> None:
    try:
        assert_no_human_loop_fields(
            payload.model_dump(mode="json", by_alias=True), label="Custom agent type"
        )
    except ForbiddenAgentTypeFieldError as exc:
        raise CustomAgentTypeError(str(exc)) from exc


async def _unique_slug(db: AsyncSession, owner_id: UUID, name: str) -> str:
    base = registry.slugify(name)
    result = await db.execute(
        select(CustomAgentType.slug).where(CustomAgentType.owner_user_id == owner_id)
    )
    taken = set(result.scalars().all())
    if base not in taken:
        return base
    index = 2
    while f"{base}-{index}" in taken:
        index += 1
    return f"{base}-{index}"


async def create_custom_type(
    db: AsyncSession, user: User, payload: CustomAgentTypeCreate
) -> CustomAgentType:
    _guard_payload(payload)
    _check_base_type(payload.base_type_id)

    row = CustomAgentType(
        family_id=uuid.uuid4(),
        version=1,
        name=payload.name.strip(),
        slug=await _unique_slug(db, user.id, payload.name),
        description=payload.description,
        icon=payload.icon,
        base_type_id=payload.base_type_id or None,
        status=CustomAgentTypeStatus(payload.status),
        parameter_definitions=_check_parameters(payload.parameter_definitions),
        metric_definitions=_check_metrics(payload.metric_definitions),
        default_autonomy_level=payload.default_autonomy_level,
        default_risk_level=payload.default_risk_level,
        owner_user_id=user.id,
        created_by=user.id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_custom_type(
    db: AsyncSession, user: User, family_id: UUID, payload: CustomAgentTypeUpdate
) -> tuple[CustomAgentType, bool]:
    """Update in place, or fork a new version when the current one is already in use.

    Returns ``(row, created_new_version)``.
    """
    _guard_payload(payload)
    current = await registry.latest_custom_row(db, family_id)
    if current is None or current.owner_user_id != user.id:
        raise CustomAgentTypeError("Custom agent type not found")

    if payload.base_type_id is not None:
        _check_base_type(payload.base_type_id)

    parameters = (
        _check_parameters(payload.parameter_definitions)
        if payload.parameter_definitions is not None
        else list(current.parameter_definitions or [])
    )
    metrics = (
        _check_metrics(payload.metric_definitions)
        if payload.metric_definitions is not None
        else list(current.metric_definitions or [])
    )

    schema_changed = (
        payload.parameter_definitions is not None and parameters != list(current.parameter_definitions or [])
    ) or (payload.metric_definitions is not None and metrics != list(current.metric_definitions or []))

    in_use = await registry.custom_type_in_use(db, family_id, version=current.version)
    fork = schema_changed and in_use

    if fork:
        row = CustomAgentType(
            family_id=family_id,
            version=current.version + 1,
            name=(payload.name or current.name).strip(),
            slug=current.slug,
            description=payload.description if payload.description is not None else current.description,
            icon=payload.icon if payload.icon is not None else current.icon,
            base_type_id=payload.base_type_id if payload.base_type_id is not None else current.base_type_id,
            status=CustomAgentTypeStatus(payload.status or "active"),
            parameter_definitions=parameters,
            metric_definitions=metrics,
            default_autonomy_level=payload.default_autonomy_level
            if payload.default_autonomy_level is not None
            else current.default_autonomy_level,
            default_risk_level=payload.default_risk_level or current.default_risk_level,
            owner_user_id=current.owner_user_id,
            created_by=user.id,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row, True

    if payload.name is not None:
        current.name = payload.name.strip()
    if payload.description is not None:
        current.description = payload.description
    if payload.icon is not None:
        current.icon = payload.icon
    if payload.base_type_id is not None:
        current.base_type_id = payload.base_type_id or None
    if payload.default_autonomy_level is not None:
        current.default_autonomy_level = payload.default_autonomy_level
    if payload.default_risk_level is not None:
        current.default_risk_level = payload.default_risk_level
    if payload.status is not None:
        current.status = CustomAgentTypeStatus(payload.status)
    current.parameter_definitions = parameters
    current.metric_definitions = metrics

    await db.commit()
    await db.refresh(current)
    return current, False


async def duplicate_custom_type(
    db: AsyncSession, user: User, family_id: UUID, version: int | None = None
) -> CustomAgentType:
    source = await registry.custom_row(db, family_id, version)
    if source is None or source.owner_user_id != user.id:
        raise CustomAgentTypeError("Custom agent type not found")

    name = f"{source.name} copy"
    row = CustomAgentType(
        family_id=uuid.uuid4(),
        version=1,
        name=name,
        slug=await _unique_slug(db, user.id, name),
        description=source.description,
        icon=source.icon,
        base_type_id=source.base_type_id,
        status=CustomAgentTypeStatus.draft,
        parameter_definitions=list(source.parameter_definitions or []),
        metric_definitions=list(source.metric_definitions or []),
        default_autonomy_level=source.default_autonomy_level,
        default_risk_level=source.default_risk_level,
        owner_user_id=user.id,
        created_by=user.id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def archive_custom_type(
    db: AsyncSession, user: User, family_id: UUID
) -> list[CustomAgentType]:
    """Archive every version: no new assignments, deployed agents keep their snapshot."""
    rows = await registry.custom_versions(db, family_id)
    if not rows or rows[0].owner_user_id != user.id:
        raise CustomAgentTypeError("Custom agent type not found")
    for row in rows:
        row.status = CustomAgentTypeStatus.archived
    await db.commit()
    for row in rows:
        await db.refresh(row)
    return rows
