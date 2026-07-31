"""Human-in-the-loop gate decisions for action proposals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActionPolicy, ActionPolicyMode


@dataclass
class ActionProposal:
    tool: str
    arguments: dict[str, Any]
    confidence: float | None = None
    description: str | None = None


@dataclass
class GateDecision:
    """outcome: auto | require_approval | propose_plan"""

    outcome: str
    mode: str
    effective_mode: str
    reason: str


async def get_policy(db: AsyncSession, action_type: str) -> ActionPolicy | None:
    result = await db.execute(
        select(ActionPolicy).where(ActionPolicy.action_type == action_type)
    )
    return result.scalar_one_or_none()


def decide_gate(
    policy: ActionPolicy | None,
    proposal: ActionProposal,
    *,
    within_plan: bool = False,
) -> GateDecision:
    if policy is None:
        return GateDecision(
            outcome="auto",
            mode="none",
            effective_mode="none",
            reason="no_policy",
        )

    mode = policy.mode
    effective = mode

    if within_plan and mode == ActionPolicyMode.plan_then_execute:
        # Nested plans are forbidden — degrade to step_by_step.
        effective = ActionPolicyMode.step_by_step

    if effective == ActionPolicyMode.plan_then_execute:
        return GateDecision(
            outcome="propose_plan",
            mode=mode.value,
            effective_mode=effective.value,
            reason="plan_then_execute",
        )

    if effective == ActionPolicyMode.step_by_step:
        return GateDecision(
            outcome="require_approval",
            mode=mode.value,
            effective_mode=effective.value,
            reason="step_by_step",
        )

    # confidence_gated
    config = policy.config or {}
    gate_on = config.get("gate_on")
    if gate_on is None:
        gate_on = ["amount", "confidence"]
    if not isinstance(gate_on, list) or len(gate_on) == 0:
        return GateDecision(
            outcome="require_approval",
            mode=mode.value,
            effective_mode=effective.value,
            reason="empty_gate_on",
        )

    amount = proposal.arguments.get("amount")
    confidence = proposal.confidence

    for dim in gate_on:
        if dim == "amount":
            max_amount = config.get("max_amount")
            if amount is None or max_amount is None:
                return GateDecision(
                    outcome="require_approval",
                    mode=mode.value,
                    effective_mode=effective.value,
                    reason="amount_missing",
                )
            try:
                if float(amount) > float(max_amount):
                    return GateDecision(
                        outcome="require_approval",
                        mode=mode.value,
                        effective_mode=effective.value,
                        reason="amount_above_max",
                    )
            except (TypeError, ValueError):
                return GateDecision(
                    outcome="require_approval",
                    mode=mode.value,
                    effective_mode=effective.value,
                    reason="amount_invalid",
                )
        elif dim == "confidence":
            min_confidence = config.get("min_confidence")
            if confidence is None or min_confidence is None:
                return GateDecision(
                    outcome="require_approval",
                    mode=mode.value,
                    effective_mode=effective.value,
                    reason="confidence_missing",
                )
            try:
                if float(confidence) < float(min_confidence):
                    return GateDecision(
                        outcome="require_approval",
                        mode=mode.value,
                        effective_mode=effective.value,
                        reason="confidence_below_min",
                    )
            except (TypeError, ValueError):
                return GateDecision(
                    outcome="require_approval",
                    mode=mode.value,
                    effective_mode=effective.value,
                    reason="confidence_invalid",
                )

    return GateDecision(
        outcome="auto",
        mode=mode.value,
        effective_mode=effective.value,
        reason="thresholds_passed",
    )


def confidence_from_billing(status: dict[str, Any] | None) -> float:
    """Demo heuristic: high confidence when refundable, else low."""
    if not status:
        return 0.4
    if status.get("refundable") is True:
        return 0.95
    return 0.4


def build_refund_plan(
    *,
    order_id: str,
    amount: float,
    reason: str,
    confidence: float,
) -> dict[str, Any]:
    import uuid

    return {
        "plan_id": str(uuid.uuid4()),
        "title": f"Refund {order_id}",
        "steps": [
            {
                "id": "s1",
                "action_type": "check_billing_status",
                "description": f"Confirm billing status for {order_id}",
                "params": {"order_id": order_id},
            },
            {
                "id": "s2",
                "action_type": "process_refund",
                "description": f"Process refund of ${amount:.2f}",
                "params": {
                    "order_id": order_id,
                    "amount": amount,
                    "reason": reason,
                },
                "confidence": confidence,
            },
        ],
    }


def policy_snapshot(policy: ActionPolicy) -> dict[str, Any]:
    return {
        "action_type": policy.action_type,
        "mode": policy.mode.value if isinstance(policy.mode, ActionPolicyMode) else policy.mode,
        "config": dict(policy.config or {}),
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
    }
