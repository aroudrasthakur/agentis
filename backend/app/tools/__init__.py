"""Local tools for hosted agents."""

from __future__ import annotations

import json
from typing import Any


MOCK_EXPLAIN = {
    "query": (
        "SELECT c.name, SUM(o.total) FROM orders o "
        "JOIN customers c ON c.id = o.customer_id "
        "WHERE o.created_at >= '2024-01-01' GROUP BY c.name ORDER BY 2 DESC LIMIT 50"
    ),
    "plan": [
        {"node": "Limit", "cost": "12450..12451", "rows": 50},
        {"node": "Sort", "cost": "12450..12451", "rows": 50},
        {"node": "HashAggregate", "cost": "8200..9100", "rows": 12000},
        {"node": "Hash Join", "cost": "410..7800", "rows": 850000},
        {"node": "Seq Scan on orders o", "cost": "0..3200", "rows": 850000, "filter": "created_at >= ..."},
        {"node": "Seq Scan on customers c", "cost": "0..180", "rows": 4200},
    ],
    "issues": [
        "Sequential scan on orders (850k rows) — no usable index on created_at",
        "Hash join processes full year of orders before aggregate",
    ],
}

MOCK_TABLE_STATS = [
    {
        "table": "orders",
        "seq_scan": 1842,
        "idx_scan": 93,
        "n_live_tup": 850_000,
        "n_dead_tup": 42_000,
        "last_vacuum": "2024-06-01",
    },
    {
        "table": "customers",
        "seq_scan": 12,
        "idx_scan": 8901,
        "n_live_tup": 4_200,
        "n_dead_tup": 120,
        "last_vacuum": "2024-07-10",
    },
]


def fetch_sample_explain(scenario: str = "reporting_join") -> dict[str, Any]:
    return {
        "scenario": scenario,
        **MOCK_EXPLAIN,
    }


def list_table_stats(schema: str = "public") -> dict[str, Any]:
    return {"schema": schema, "tables": MOCK_TABLE_STATS}


def suggest_indexes(
    table: str,
    query_pattern: str,
    workload: str = "read_heavy",
) -> dict[str, Any]:
    suggestions = []
    if table == "orders" or "orders" in query_pattern.lower():
        suggestions.append(
            {
                "ddl": "CREATE INDEX CONCURRENTLY idx_orders_created_at ON orders (created_at);",
                "rationale": "Supports time-range filters and reduces seq scans on reporting queries.",
                "impact": "high",
            }
        )
        suggestions.append(
            {
                "ddl": "CREATE INDEX CONCURRENTLY idx_orders_customer_created ON orders (customer_id, created_at);",
                "rationale": "Covering join + filter path for customer-level aggregates.",
                "impact": "medium",
            }
        )
    if not suggestions:
        suggestions.append(
            {
                "ddl": f"-- Review indexes on {table} for predicates in: {query_pattern[:120]}",
                "rationale": "No mock template for this table; inspect EXPLAIN and pg_stat first.",
                "impact": "unknown",
            }
        )
    return {
        "table": table,
        "query_pattern": query_pattern,
        "workload": workload,
        "recommendations": suggestions,
    }


# Legacy support tools (kept for old sessions; not granted to current test agent)
MOCK_ORDERS = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "status": "delivered",
        "amount": 89.99,
        "currency": "USD",
        "items": ["Wireless headphones"],
        "customer_id": "CUS-42",
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
        "note": "Legacy demo tool.",
    }


TOOL_IMPLS = {
    "fetch_sample_explain": fetch_sample_explain,
    "list_table_stats": list_table_stats,
    "suggest_indexes": suggest_indexes,
    "lookup_order": lookup_order,
    "get_customer_summary": get_customer_summary,
    "propose_refund": propose_refund,
}


OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_sample_explain",
            "description": "Return mock EXPLAIN output for a known slow PostgreSQL reporting query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scenario": {
                        "type": "string",
                        "description": "Scenario id, e.g. reporting_join",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_table_stats",
            "description": "Return mock pg_stat-style table metrics for public schema tables.",
            "parameters": {
                "type": "object",
                "properties": {"schema": {"type": "string"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_indexes",
            "description": "Suggest PostgreSQL indexes for a table and query pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {"type": "string"},
                    "query_pattern": {"type": "string"},
                    "workload": {"type": "string"},
                },
                "required": ["table", "query_pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": "Look up a mock order by order_id (legacy).",
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
            "description": "Get a mock customer snapshot (legacy).",
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
            "description": "Draft a refund intent (legacy).",
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
