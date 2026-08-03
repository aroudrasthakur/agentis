"""FastAPI dependencies for authorization."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.services.authorization_service import (
    AuthorizationContext,
    AuthorizationError,
    authorize,
    require_permission as _require_permission,
)
from app.db import get_db
from app.deps import get_current_user
from app.models import User


def forbidden_response(exc: AuthorizationError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "FORBIDDEN",
            "code": "PERMISSION_DENIED",
            "message": str(exc),
            "permission": exc.permission,
            "resourceType": exc.resource_type,
            "resourceId": exc.resource_id,
        },
    )


def RequirePermission(
    permission: str,
    *,
    resource_type: str | None = None,
    resource_id_param: str | None = None,
    workspace_id_param: str | None = None,
) -> Callable:
    async def _dep(
        request: Request,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        resource_id: UUID | str | None = None
        if resource_id_param:
            raw = request.path_params.get(resource_id_param)
            if raw:
                resource_id = raw
        workspace_id = None
        if workspace_id_param:
            raw_ws = request.path_params.get(workspace_id_param)
            if raw_ws:
                workspace_id = UUID(str(raw_ws))
        ctx = AuthorizationContext(
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        try:
            await _require_permission(db, user, permission, ctx)
        except AuthorizationError as exc:
            raise forbidden_response(exc) from exc

    return Depends(_dep)


async def check_permission(
    db: AsyncSession,
    user: User,
    permission: str,
    ctx: AuthorizationContext | None = None,
) -> bool:
    decision = await authorize(db, user, permission, ctx)
    return decision.allowed
