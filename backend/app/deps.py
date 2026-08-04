from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization.session_context import clear_session_assignment_id, set_session_assignment_id
from app.authorization.services.session_role_service import (
    resolve_default_session_assignment_id,
    validate_session_assignment,
)
from app.db import get_db
from app.models import User
from app.services.auth import decode_user_token

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    clear_session_assignment_id()
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_user_token(creds.credentials)
        user_id = UUID(payload["uid"])
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    assignment_id: UUID | None = None
    raw_asid = payload.get("asid")
    if raw_asid:
        try:
            assignment_id = UUID(str(raw_asid))
            await validate_session_assignment(db, user.id, assignment_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session role; sign in again or select a role",
            ) from None
    else:
        assignment_id = await resolve_default_session_assignment_id(db, user.id)

    set_session_assignment_id(assignment_id)
    return user
