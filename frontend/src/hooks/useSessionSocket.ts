"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Session, SessionEvent } from "@/lib/api";
import { wsUrl } from "@/lib/api";

type WsMessage =
  | { type: "connected"; session_id: string; message: string }
  | { type: "event"; event: SessionEvent }
  | { type: "session_updated"; session: Session }
  | { type: "error"; detail: string }
  | { type: "pong" };

export function useSessionSocket(
  sessionId: string,
  invite: string | null,
  onEvent: (event: SessionEvent) => void,
  onSession: (session: Session) => void
) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const onEventRef = useRef(onEvent);
  const onSessionRef = useRef(onSession);
  onEventRef.current = onEvent;
  onSessionRef.current = onSession;

  useEffect(() => {
    if (!invite) return;
    const ws = new WebSocket(wsUrl(sessionId, invite));
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (msg) => {
      let data: WsMessage;
      try {
        data = JSON.parse(msg.data) as WsMessage;
      } catch (error) {
        console.warn("Ignoring malformed WebSocket message", error);
        return;
      }
      if (data.type === "event") onEventRef.current(data.event);
      if (data.type === "session_updated") onSessionRef.current(data.session);
    };
    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [sessionId, invite]);

  const send = useCallback((payload: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
    }
  }, []);

  return { connected, send };
}
