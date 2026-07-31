import json
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.db import AsyncSessionLocal
from app.models import Session
from app.services import orchestration
from app.services.tokens import TokenError, verify_session_invite
from app.ws.manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/sessions/{session_id}/ws")
async def session_ws(
    websocket: WebSocket,
    session_id: UUID,
    invite: str | None = Query(default=None),
) -> None:
    async with AsyncSessionLocal() as db:
        session = await db.get(Session, session_id)
        if not session:
            await websocket.close(code=4404)
            return
        if not invite:
            await websocket.close(code=4401)
            return
        try:
            verify_session_invite(invite, session_id, expected_jti=session.invite_jti)
        except TokenError:
            await websocket.close(code=4401)
            return

    orchestration.remember_invite(session_id, invite)
    await manager.connect(session_id, websocket)
    try:
        await websocket.send_json(
            {
                "type": "connected",
                "session_id": str(session_id),
                "message": "Connected to Agentis session",
            }
        )
        while True:
            if websocket.client_state != WebSocketState.CONNECTED:
                break
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                continue
            action = data.get("action")
            async with AsyncSessionLocal() as db:
                try:
                    await orchestration.handle_control_action(db, session_id, action, data)
                except Exception as exc:  # noqa: BLE001
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json({"type": "error", "detail": str(exc)})
    except WebSocketDisconnect:
        pass
    except RuntimeError:
        pass
    finally:
        await manager.disconnect(session_id, websocket)
