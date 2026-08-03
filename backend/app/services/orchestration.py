"""Thin session orchestration: turns, controls, HITL approval / plan gates."""

from __future__ import annotations

import asyncio
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents import TEST_AGENT_KEY
from app.agents.runtime import run_hosted_agent
from app.mcp_client import call_mcp_tool, remote_agent_message
from app.models import (
    Event,
    EventType,
    HostingMode,
    Participant,
    ParticipantKind,
    Session,
    SessionStatus,
)
from app.schemas import EventOut, ParticipantOut, SessionOut
from app.services.access import assert_participant_can_call_tool
from app.services.hitl import (
    ActionProposal,
    build_refund_plan,
    confidence_from_billing,
    decide_gate,
    get_policy,
)
from app.services.session_service import create_event, get_session_full, session_share_url
from app.services.tokens import CapabilityDenied, TokenError
from app.ws.manager import manager

# In-memory orchestration state per session
_tasks: dict[UUID, asyncio.Task] = {}
_paused: set[UUID] = set()
_awaiting_approval: dict[UUID, dict] = {}
_awaiting_plan: dict[UUID, dict] = {}
_plan_running: set[UUID] = set()
_redirect_hint: dict[UUID, str] = {}
# invite token per session for share_url reconstruction in broadcasts
_session_invites: dict[UUID, str] = {}


def remember_invite(session_id: UUID, invite: str | None) -> None:
    if invite:
        _session_invites[session_id] = invite


def _participant_out(p: Participant) -> ParticipantOut:
    return ParticipantOut(
        id=p.id,
        session_id=p.session_id,
        agent_id=p.agent_id,
        name=p.name,
        kind=p.kind,
        org_tag=p.org_tag,
        hosting_mode=p.hosting_mode,
        endpoint_url=p.endpoint_url,
        agent_key=p.agent_key,
        granted_capabilities=list(p.granted_capabilities) if p.granted_capabilities is not None else None,
        token_expires_at=p.token_expires_at,
        token_revoked=p.token_revoked_at is not None,
    )


def _event_payload(event: Event) -> dict:
    return EventOut(
        id=event.id,
        session_id=event.session_id,
        participant_id=event.participant_id,
        type=event.type,
        content=event.content,
        requires_approval=event.requires_approval,
        created_at=event.created_at,
        sequence=event.sequence,
        participant=_participant_out(event.participant) if event.participant else None,
    ).model_dump(mode="json")


def _session_payload(session: Session) -> dict:
    invite = _session_invites.get(session.id)
    events = []
    for ev in sorted(session.events, key=lambda e: e.sequence):
        events.append(
            EventOut(
                id=ev.id,
                session_id=ev.session_id,
                participant_id=ev.participant_id,
                type=ev.type,
                content=ev.content,
                requires_approval=ev.requires_approval,
                created_at=ev.created_at,
                sequence=ev.sequence,
                participant=_participant_out(ev.participant) if ev.participant else None,
            )
        )
    return SessionOut(
        id=session.id,
        title=session.title,
        status=session.status,
        nature=session.nature,
        gathering_id=session.gathering_id,
        active_participant_id=session.active_participant_id,
        created_at=session.created_at,
        share_url=session_share_url(session.id, invite),
        invite_expires_at=session.invite_expires_at,
        participants=[_participant_out(p) for p in session.participants],
        events=events,
    ).model_dump(mode="json")


async def _broadcast_event(db: AsyncSession, session_id: UUID, event: Event) -> None:
    result = await db.execute(
        select(Event).where(Event.id == event.id).options(selectinload(Event.participant))
    )
    event = result.scalar_one()
    await manager.broadcast(session_id, {"type": "event", "event": _event_payload(event)})
    session = await get_session_full(db, session_id)
    if session:
        await manager.broadcast(
            session_id, {"type": "session_updated", "session": _session_payload(session)}
        )


def _timeline_text(session: Session) -> str:
    lines = [f"Session: {session.title}", "Timeline:"]
    for ev in sorted(session.events, key=lambda e: e.sequence):
        name = ev.participant.name if ev.participant else "?"
        lines.append(f"[{ev.sequence}] {name} ({ev.type.value}): {ev.content}")
    return "\n".join(lines)


async def _agent_participants(session: Session) -> list[Participant]:
    return [
        p
        for p in session.participants
        if p.kind != ParticipantKind.human and p.token_revoked_at is None
    ]


async def _wait_while_paused(session_id: UUID) -> None:
    while session_id in _paused:
        await asyncio.sleep(0.4)


async def _wait_for_gates(session_id: UUID) -> None:
    """Block until no approval/plan wait and no in-flight plan execution."""
    while (
        session_id in _awaiting_approval
        or session_id in _awaiting_plan
        or session_id in _plan_running
    ):
        await _wait_while_paused(session_id)
        await asyncio.sleep(0.4)


async def _execute_tool(
    db: AsyncSession,
    *,
    endpoint_url: str,
    participant_id: UUID,
    tool: str,
    arguments: dict,
) -> dict:
    await assert_participant_can_call_tool(db, participant_id, tool)
    return await call_mcp_tool(
        endpoint_url,
        tool,
        arguments,
        db=db,
        participant_id=participant_id,
    )


async def propose_or_execute_action(
    db: AsyncSession,
    session: Session,
    participant: Participant,
    proposal: ActionProposal,
    *,
    within_plan: bool = False,
) -> Event:
    """Apply HITL policy: auto-execute, require approval, or propose a plan."""
    policy = await get_policy(db, proposal.tool)
    decision = decide_gate(policy, proposal, within_plan=within_plan)
    endpoint = participant.endpoint_url or ""

    if decision.outcome == "propose_plan":
        amount = float(proposal.arguments.get("amount") or 0)
        plan = build_refund_plan(
            order_id=str(proposal.arguments.get("order_id") or "ORD-1001"),
            amount=amount,
            reason=str(proposal.arguments.get("reason") or "Customer requested refund"),
            confidence=float(proposal.confidence if proposal.confidence is not None else 0.4),
        )
        event = await create_event(
            db,
            session_id=session.id,
            participant_id=participant.id,
            event_type=EventType.plan_proposed,
            content=json.dumps(plan),
            requires_approval=True,
        )
        _awaiting_plan[session.id] = {
            "participant_id": str(participant.id),
            "endpoint_url": endpoint,
            "plan": plan,
        }
        await db.commit()
        await _broadcast_event(db, session.id, event)
        return event

    payload = {
        "tool": proposal.tool,
        "arguments": proposal.arguments,
        "confidence": proposal.confidence,
        "mode": decision.effective_mode,
        "decision": decision.outcome,
        "reason": decision.reason,
        "within_plan": within_plan,
    }

    if decision.outcome == "auto":
        try:
            result = await _execute_tool(
                db,
                endpoint_url=endpoint,
                participant_id=participant.id,
                tool=proposal.tool,
                arguments=proposal.arguments,
            )
            content = {**payload, "result": result}
            event = await create_event(
                db,
                session_id=session.id,
                participant_id=participant.id,
                event_type=EventType.action_executed,
                content=json.dumps(content),
                requires_approval=False,
            )
        except (TokenError, CapabilityDenied) as exc:
            event = await create_event(
                db,
                session_id=session.id,
                participant_id=participant.id,
                event_type=EventType.action_denied,
                content=f"Blocked {proposal.tool} — access revoked or out of scope: {exc}",
            )
        await db.commit()
        await _broadcast_event(db, session.id, event)
        return event

    # require_approval
    event = await create_event(
        db,
        session_id=session.id,
        participant_id=participant.id,
        event_type=EventType.action_pending,
        content=json.dumps(payload),
        requires_approval=True,
    )
    _awaiting_approval[session.id] = {
        "participant_id": str(participant.id),
        "endpoint_url": endpoint,
        "tool": proposal.tool,
        "arguments": proposal.arguments,
        "confidence": proposal.confidence,
        "mode": decision.effective_mode,
        "within_plan": within_plan,
    }
    await db.commit()
    await _broadcast_event(db, session.id, event)
    return event


async def _execute_approved_plan(
    session_id: UUID,
    *,
    participant_id: UUID,
    endpoint_url: str,
    steps: list[dict],
) -> None:
    """Run approved plan steps sequentially; honor pause between steps."""
    from app.db import AsyncSessionLocal

    _plan_running.add(session_id)
    try:
        async with AsyncSessionLocal() as db:
            for step in steps:
                await _wait_while_paused(session_id)

                session = await get_session_full(db, session_id)
                if not session or session.status == SessionStatus.completed:
                    return

                participant = next(
                    (p for p in session.participants if p.id == participant_id), None
                )
                if participant is None or participant.token_revoked_at is not None:
                    human = next(p for p in session.participants if p.kind == ParticipantKind.human)
                    event = await create_event(
                        db,
                        session_id=session_id,
                        participant_id=human.id,
                        event_type=EventType.message,
                        content="Plan execution stopped — agent detached or token revoked.",
                    )
                    await db.commit()
                    await _broadcast_event(db, session_id, event)
                    return

                proposal = ActionProposal(
                    tool=step["action_type"],
                    arguments=dict(step.get("params") or {}),
                    confidence=step.get("confidence"),
                    description=step.get("description"),
                )
                event = await propose_or_execute_action(
                    db, session, participant, proposal, within_plan=True
                )

                if event.requires_approval:
                    while session_id in _awaiting_approval:
                        await _wait_while_paused(session_id)
                        await asyncio.sleep(0.4)
                    session = await get_session_full(db, session_id)
                    if session and any(
                        e.type in (EventType.action_denied, EventType.plan_denied)
                        for e in session.events[-3:]
                    ):
                        return
    finally:
        _plan_running.discard(session_id)


async def run_agent_turn(db: AsyncSession, session: Session, participant: Participant) -> Event | None:
    hint = _redirect_hint.pop(session.id, None)
    context = _timeline_text(session)

    if participant.hosting_mode == HostingMode.hosted:
        text = await run_hosted_agent(
            db=db,
            participant_id=participant.id,
            agent_key=participant.agent_key or TEST_AGENT_KEY,
            timeline_context=context,
            user_hint=hint,
        )
        event = await create_event(
            db,
            session_id=session.id,
            participant_id=participant.id,
            event_type=EventType.message,
            content=text,
        )
        await db.commit()
        await _broadcast_event(db, session.id, event)
        return event

    # remote_mcp
    endpoint = participant.endpoint_url or ""
    try:
        text, billing = await remote_agent_message(
            endpoint, context, db=db, participant_id=participant.id
        )
    except (TokenError, CapabilityDenied) as exc:
        event = await create_event(
            db,
            session_id=session.id,
            participant_id=participant.id,
            event_type=EventType.message,
            content=f"Access denied: {exc}",
        )
        await db.commit()
        await _broadcast_event(db, session.id, event)
        return event

    event = await create_event(
        db,
        session_id=session.id,
        participant_id=participant.id,
        event_type=EventType.message,
        content=text,
    )
    await db.commit()
    await _broadcast_event(db, session.id, event)

    confidence = confidence_from_billing(billing if isinstance(billing, dict) else None)
    proposal = ActionProposal(
        tool="process_refund",
        arguments={
            "order_id": "ORD-1001",
            "amount": 89.99,
            "reason": "Customer requested refund for defective item",
        },
        confidence=confidence,
    )
    return await propose_or_execute_action(db, session, participant, proposal, within_plan=False)


async def _orchestration_loop(session_id: UUID) -> None:
    from app.db import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            session = await get_session_full(db, session_id)
            if not session:
                return
            agents = await _agent_participants(session)
            if not agents:
                human = next(p for p in session.participants if p.kind == ParticipantKind.human)
                event = await create_event(
                    db,
                    session_id=session.id,
                    participant_id=human.id,
                    event_type=EventType.message,
                    content="No agents attached. Attach agents from the registry to continue.",
                )
                await db.commit()
                await _broadcast_event(db, session.id, event)
                return

            agents = sorted(agents, key=lambda p: p.name or "")

            if not session.active_participant_id:
                session.active_participant_id = agents[0].id
                await db.commit()

            for agent in agents:
                await _wait_while_paused(session_id)

                session = await get_session_full(db, session_id)
                if not session or session.status == SessionStatus.completed:
                    return

                session.active_participant_id = agent.id
                await db.commit()
                session = await get_session_full(db, session_id)
                assert session is not None
                await manager.broadcast(
                    session_id, {"type": "session_updated", "session": _session_payload(session)}
                )

                participant = next(
                    (p for p in session.participants if p.id == agent.id), None
                )
                if participant is None or participant.token_revoked_at is not None:
                    continue
                event = await run_agent_turn(db, session, participant)

                if event and (
                    event.requires_approval
                    or session_id in _awaiting_plan
                    or session_id in _awaiting_approval
                    or session_id in _plan_running
                ):
                    await _wait_for_gates(session_id)
                    session = await get_session_full(db, session_id)
                    if session and any(
                        e.type in (EventType.action_denied, EventType.plan_denied)
                        for e in session.events[-5:]
                    ):
                        break

            async with AsyncSessionLocal() as db2:
                session = await get_session_full(db2, session_id)
                if session and session.status != SessionStatus.completed:
                    session.status = SessionStatus.completed
                    await db2.commit()
                    session = await get_session_full(db2, session_id)
                    if session:
                        await manager.broadcast(
                            session_id,
                            {"type": "session_updated", "session": _session_payload(session)},
                        )
    finally:
        _tasks.pop(session_id, None)


async def start_session(
    db: AsyncSession, session_id: UUID, invite: str | None = None
) -> Session:
    session = await get_session_full(db, session_id)
    if not session:
        raise ValueError("Session not found")
    remember_invite(session_id, invite)
    if session_id in _tasks and not _tasks[session_id].done():
        return session

    session.status = SessionStatus.active
    _paused.discard(session_id)
    await db.commit()

    task = asyncio.create_task(_orchestration_loop(session_id))
    _tasks[session_id] = task
    return session


async def handle_control_action(
    db: AsyncSession, session_id: UUID, action: str | None, data: dict
) -> None:
    session = await get_session_full(db, session_id)
    if not session:
        raise ValueError("Session not found")
    human = next(p for p in session.participants if p.kind == ParticipantKind.human)

    if action == "pause":
        _paused.add(session_id)
        session.status = SessionStatus.paused
        event = await create_event(
            db,
            session_id=session_id,
            participant_id=human.id,
            event_type=EventType.message,
            content="Session paused by human.",
        )
        await db.commit()
        await _broadcast_event(db, session_id, event)
        return

    if action == "resume":
        _paused.discard(session_id)
        session.status = SessionStatus.active
        event = await create_event(
            db,
            session_id=session_id,
            participant_id=human.id,
            event_type=EventType.message,
            content="Session resumed by human.",
        )
        await db.commit()
        await _broadcast_event(db, session_id, event)
        return

    if action == "redirect":
        message = (data.get("message") or "").strip()
        if not message:
            raise ValueError("Redirect requires message")
        _redirect_hint[session_id] = message
        event = await create_event(
            db,
            session_id=session_id,
            participant_id=human.id,
            event_type=EventType.redirect,
            content=message,
        )
        await db.commit()
        await _broadcast_event(db, session_id, event)
        return

    if action == "handoff":
        target_id = data.get("participant_id")
        if not target_id:
            raise ValueError("handoff requires participant_id")
        target = next((p for p in session.participants if str(p.id) == str(target_id)), None)
        if not target or target.kind == ParticipantKind.human:
            raise ValueError("Invalid handoff target")
        session.active_participant_id = target.id
        event = await create_event(
            db,
            session_id=session_id,
            participant_id=human.id,
            event_type=EventType.handoff,
            content=f"Handed off to {target.name}",
        )
        await db.commit()
        await _broadcast_event(db, session_id, event)
        return

    if action == "approve":
        pending = _awaiting_approval.get(session_id)
        if not pending:
            raise ValueError("No action pending approval")
        vendor_pid = UUID(pending["participant_id"])
        try:
            result = await _execute_tool(
                db,
                endpoint_url=pending["endpoint_url"],
                participant_id=vendor_pid,
                tool=pending["tool"],
                arguments=pending["arguments"],
            )
            event = await create_event(
                db,
                session_id=session_id,
                participant_id=human.id,
                event_type=EventType.action_approved,
                content=f"Approved {pending['tool']}: {json.dumps(result)}",
            )
            executed = await create_event(
                db,
                session_id=session_id,
                participant_id=vendor_pid,
                event_type=EventType.action_executed,
                content=json.dumps(
                    {
                        "tool": pending["tool"],
                        "arguments": pending["arguments"],
                        "confidence": pending.get("confidence"),
                        "mode": pending.get("mode"),
                        "decision": "approved",
                        "within_plan": pending.get("within_plan", False),
                        "result": result,
                    }
                ),
            )
        except (TokenError, CapabilityDenied) as exc:
            event = await create_event(
                db,
                session_id=session_id,
                participant_id=human.id,
                event_type=EventType.action_denied,
                content=f"Blocked {pending['tool']} — access revoked or out of scope: {exc}",
            )
            executed = None
        _awaiting_approval.pop(session_id, None)
        await db.commit()
        await _broadcast_event(db, session_id, event)
        if executed is not None:
            await _broadcast_event(db, session_id, executed)
        return

    if action == "deny":
        pending = _awaiting_approval.get(session_id)
        if not pending:
            raise ValueError("No action pending approval")
        event = await create_event(
            db,
            session_id=session_id,
            participant_id=human.id,
            event_type=EventType.action_denied,
            content=f"Denied {pending['tool']}",
        )
        _awaiting_approval.pop(session_id, None)
        await db.commit()
        await _broadcast_event(db, session_id, event)
        return

    if action == "approve_plan":
        pending = _awaiting_plan.get(session_id)
        if not pending:
            raise ValueError("No plan pending approval")
        plan = dict(pending["plan"])
        removed = set(data.get("removed_step_ids") or [])
        steps = [s for s in plan.get("steps", []) if s.get("id") not in removed]
        plan["steps"] = steps
        event = await create_event(
            db,
            session_id=session_id,
            participant_id=human.id,
            event_type=EventType.plan_approved,
            content=json.dumps(plan),
        )
        _awaiting_plan.pop(session_id, None)
        await db.commit()
        await _broadcast_event(db, session_id, event)

        if steps:
            asyncio.create_task(
                _execute_approved_plan(
                    session_id,
                    participant_id=UUID(pending["participant_id"]),
                    endpoint_url=pending["endpoint_url"],
                    steps=steps,
                )
            )
        return

    if action == "deny_plan":
        pending = _awaiting_plan.get(session_id)
        if not pending:
            raise ValueError("No plan pending approval")
        plan = pending["plan"]
        event = await create_event(
            db,
            session_id=session_id,
            participant_id=human.id,
            event_type=EventType.plan_denied,
            content=json.dumps({"plan_id": plan.get("plan_id"), "title": plan.get("title")}),
        )
        _awaiting_plan.pop(session_id, None)
        await db.commit()
        await _broadcast_event(db, session_id, event)
        return

    if action == "ping":
        await manager.broadcast(session_id, {"type": "pong"})
        return

    raise ValueError(f"Unknown action: {action}")
