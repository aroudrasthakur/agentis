from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import ActionPolicy, PolicyChangeEvent
from app.schemas import (
    ActionPolicyOut,
    ActionPolicyPatchResponse,
    ActionPolicyUpdate,
    PolicyChangeEventOut,
)
from app.services.hitl import policy_snapshot

router = APIRouter(prefix="/action-policies", tags=["action-policies"])


@router.get("", response_model=list[ActionPolicyOut])
async def list_action_policies(db: AsyncSession = Depends(get_db)) -> list[ActionPolicy]:
    result = await db.execute(select(ActionPolicy).order_by(ActionPolicy.action_type.asc()))
    return list(result.scalars().all())


@router.get("/{action_type}", response_model=ActionPolicyOut)
async def get_action_policy(action_type: str, db: AsyncSession = Depends(get_db)) -> ActionPolicy:
    result = await db.execute(
        select(ActionPolicy).where(ActionPolicy.action_type == action_type)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Action policy not found")
    return policy


@router.patch("/{action_type}", response_model=ActionPolicyPatchResponse)
async def patch_action_policy(
    action_type: str,
    payload: ActionPolicyUpdate,
    db: AsyncSession = Depends(get_db),
) -> ActionPolicyPatchResponse:
    result = await db.execute(
        select(ActionPolicy).where(ActionPolicy.action_type == action_type)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Action policy not found")

    before = policy_snapshot(policy)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No updates provided")
    for key, value in data.items():
        setattr(policy, key, value)
    policy.updated_at = datetime.now(timezone.utc)

    await db.flush()
    after = policy_snapshot(policy)
    change = PolicyChangeEvent(action_type=action_type, before=before, after=after)
    db.add(change)
    await db.commit()
    await db.refresh(policy)
    await db.refresh(change)
    return ActionPolicyPatchResponse(
        policy=ActionPolicyOut.model_validate(policy),
        change=PolicyChangeEventOut.model_validate(change),
    )
