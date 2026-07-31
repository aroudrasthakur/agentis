"""Local tools for hosted agents."""

from __future__ import annotations

import json
from typing import Any


MOCK_ORDERS = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "status": "delivered",
        "amount": 89.99,
        "currency": "USD",
        "items": ["Wireless headphones"],
        "customer_id": "CUS-42",
    },
    "ORD-2002": {
        "order_id": "ORD-2002",
        "status": "shipped",
        "amount": 45.00,
        "currency": "USD",
        "items": ["USB-C hub"],
        "customer_id": "CUS-17",
    },
}


def lookup_order(order_id: str) -> dict[str, Any]:
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return {"found": False, "order_id": order_id, "error": "Order not found"}
    return {"found": True, **order}


def get_customer_summary(customer_id: str = "CUS-42") -> dict[str, Any]:
    return {
        "customer_id": customer_id,
        "name": "Alex Rivera",
        "refund_eligible": True,
        "prior_refunds_90d": 0,
        "tier": "standard",
    }


def propose_refund(order_id: str, amount: float, reason: str) -> dict[str, Any]:
    return {
        "proposal": "refund",
        "order_id": order_id,
        "amount": amount,
        "reason": reason,
        "note": "Draft only — Vendor Billing must execute process_refund after human approval.",
    }


TOOL_IMPLS = {
    "lookup_order": lookup_order,
    "get_customer_summary": get_customer_summary,
    "propose_refund": propose_refund,
}


# OpenAI Chat Completions tool schema
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": "Look up a mock order by order_id.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_summary",
            "description": "Get a mock customer/refund eligibility snapshot.",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_refund",
            "description": "Draft a refund intent for the vendor agent to execute later.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "amount": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": ["order_id", "amount", "reason"],
            },
        },
    },
]


def run_tool(name: str, arguments: dict[str, Any]) -> str:
    fn = TOOL_IMPLS.get(name)
    if not fn:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        result = fn(**arguments)
    except TypeError as exc:
        return json.dumps({"error": str(exc)})
    return json.dumps(result)
