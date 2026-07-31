"""Vendor Billing MCP-style server (Streamable HTTP + simple tool helpers)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="Vendor Billing MCP", version="0.1.0")


class BillingStatusRequest(BaseModel):
    order_id: str = "ORD-1001"


class RefundRequest(BaseModel):
    order_id: str
    amount: float
    reason: str = Field(default="Customer refund")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tools/check_billing_status")
async def check_billing_status(payload: BillingStatusRequest) -> dict[str, Any]:
    return {
        "order_id": payload.order_id,
        "payment_status": "captured",
        "refundable": True,
        "captured_amount": 89.99,
        "currency": "USD",
    }


@app.post("/tools/process_refund")
async def process_refund(payload: RefundRequest) -> dict[str, Any]:
    return {
        "ok": True,
        "order_id": payload.order_id,
        "amount": payload.amount,
        "reason": payload.reason,
        "confirmation_id": f"REF-{uuid.uuid4().hex[:8].upper()}",
        "status": "refunded",
    }


@app.post("/mcp")
async def mcp_jsonrpc(body: dict[str, Any]) -> dict[str, Any]:
    """Minimal JSON-RPC tools/call shim for Streamable-HTTP-style clients."""
    req_id = body.get("id", 1)
    method = body.get("method")
    params = body.get("params") or {}
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "check_billing_status",
                        "description": "Check mock billing status",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"order_id": {"type": "string"}},
                        },
                    },
                    {
                        "name": "process_refund",
                        "description": "Process a mock refund",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "order_id": {"type": "string"},
                                "amount": {"type": "number"},
                                "reason": {"type": "string"},
                            },
                            "required": ["order_id", "amount"],
                        },
                    },
                ]
            },
        }
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name == "check_billing_status":
            result = await check_billing_status(BillingStatusRequest(**arguments))
        elif name == "process_refund":
            result = await process_refund(RefundRequest(**arguments))
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool {name}"},
            }
        return {"jsonrpc": "2.0", "id": req_id, "result": result}
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "vendor-billing", "version": "0.1.0"},
            },
        }
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8100, reload=False)
