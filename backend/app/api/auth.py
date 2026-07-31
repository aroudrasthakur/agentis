from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.models import AgoraMember, User
from app.schemas import AuthResponse, UserCreate, UserLogin, UserOut
from app.services.auth import (
    create_user,
    get_user_by_email,
    mint_user_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


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
    # Claim pending agora invites for this email
    pending = await db.execute(
        select(AgoraMember).where(
            AgoraMember.invited_email == email, AgoraMember.user_id.is_(None)
        )
    )
    for membership in pending.scalars().all():
        membership.user_id = user.id
    await db.commit()
    await db.refresh(user)
    token = mint_user_token(user.id, user.email)
    return AuthResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    user = await get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    pending = await db.execute(
        select(AgoraMember).where(
            AgoraMember.invited_email == user.email, AgoraMember.user_id.is_(None)
        )
    )
    for membership in pending.scalars().all():
        membership.user_id = user.id
    await db.commit()
    token = mint_user_token(user.id, user.email)
    return AuthResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
