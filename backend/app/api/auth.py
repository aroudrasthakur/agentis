from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.models import GatheringMember, User
from app.schemas import AuthResponse, SelectSessionRoleRequest, SessionRoleOut, UserCreate, UserLogin, UserOut, UserUpdate
from app.services.auth import (
    create_user,
    get_user_by_email,
    mint_user_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _session_role_out(option) -> SessionRoleOut:
    return SessionRoleOut(
        assignment_id=option.assignment_id,
        role_id=option.role_id,
        role_name=option.role_name,
        role_slug=option.role_slug,
        category=option.category,
        workspace_id=option.workspace_id,
        workspace_name=option.workspace_name,
    )


async def _auth_response(db: AsyncSession, user: User) -> AuthResponse:
    from app.authorization.services.session_role_service import (
        option_for_assignment,
        resolve_default_session_assignment_id,
        validate_session_assignment,
    )

    session_role: SessionRoleOut | None = None
    assignment_id = await resolve_default_session_assignment_id(db, user.id)
    token_kwargs: dict = {}
    if assignment_id:
        assignment = await validate_session_assignment(db, user.id, assignment_id)
        option = await option_for_assignment(db, assignment)
        session_role = _session_role_out(option)
        token_kwargs["session_assignment_id"] = assignment_id
    token = mint_user_token(user.id, user.email, **token_kwargs)
    return AuthResponse(access_token=token, user=UserOut.model_validate(user), session_role=session_role)


async def _claim_invites(db: AsyncSession, user: User) -> None:
    pending = await db.execute(
        select(GatheringMember).where(
            GatheringMember.invited_email == user.email,
            GatheringMember.user_id.is_(None),
        )
    )
    for membership in pending.scalars().all():
        membership.user_id = user.id


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    email = payload.email.lower().strip()
    if await get_user_by_email(db, email):
        raise HTTPException(status_code=409, detail="Email already registered")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    user = await create_user(
        db,
        email=email,
        display_name=payload.display_name or email.split("@")[0],
        password=payload.password,
    )
    from app.authorization.services.bootstrap import assign_default_roles_for_new_user

    await assign_default_roles_for_new_user(db, user.id)
    await _claim_invites(db, user)
    await db.commit()
    await db.refresh(user)
    return await _auth_response(db, user)


@router.post("/login", response_model=AuthResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    user = await get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await _claim_invites(db, user)
    await db.commit()
    return await _auth_response(db, user)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/session/roles", response_model=list[SessionRoleOut])
async def list_session_roles(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SessionRoleOut]:
    from app.authorization.services.session_role_service import list_session_role_options

    options = await list_session_role_options(db, user.id)
    return [_session_role_out(o) for o in options]


@router.get("/session/role", response_model=SessionRoleOut)
async def get_session_role(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionRoleOut:
    from app.authorization.session_context import get_session_assignment_id
    from app.authorization.services.session_role_service import (
        option_for_assignment,
        validate_session_assignment,
    )

    aid = get_session_assignment_id()
    if not aid:
        raise HTTPException(status_code=404, detail="No session role active")
    assignment = await validate_session_assignment(db, user.id, aid)
    return _session_role_out(await option_for_assignment(db, assignment))


@router.post("/session/role", response_model=AuthResponse)
async def select_session_role(
    payload: SelectSessionRoleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    from app.authorization.services.authorization_service import invalidate_user_cache
    from app.authorization.services.session_role_service import (
        option_for_assignment,
        validate_session_assignment,
    )

    assignment = await validate_session_assignment(db, user.id, payload.assignment_id)
    option = await option_for_assignment(db, assignment)
    invalidate_user_cache(user.id)
    token = mint_user_token(
        user.id, user.email, session_assignment_id=assignment.id
    )
    return AuthResponse(
        access_token=token,
        user=UserOut.model_validate(user),
        session_role=_session_role_out(option),
    )


@router.patch("/me", response_model=UserOut)
async def update_me(
    payload: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No updates provided")
    for key, value in data.items():
        setattr(user, key, value)
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/people/{user_id}", response_model=UserOut)
async def get_person(
    user_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    from uuid import UUID

    person = await db.get(User, UUID(user_id))
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return person
