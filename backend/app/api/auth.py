from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.models import GatheringMember, User
from app.schemas import AuthResponse, UserCreate, UserLogin, UserOut, UserUpdate
from app.services.auth import (
    create_user,
    get_user_by_email,
    mint_user_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


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
    token = mint_user_token(user.id, user.email)
    return AuthResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    user = await get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await _claim_invites(db, user)
    await db.commit()
    token = mint_user_token(user.id, user.email)
    return AuthResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user


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
