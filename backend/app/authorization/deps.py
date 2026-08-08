"""FastAPI dependencies for authorization."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.authorization.services.authorization_service import AuthorizationError


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
