import json

import httpx
import pytest

from app.mcp_client import MCPToolCallError, call_mcp_tool


class FakeAsyncClient:
    def __init__(self, responses: list[httpx.Response | Exception], **_: object) -> None:
        self._responses = iter(responses)

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, url: str, **_: object) -> httpx.Response:
        response = next(self._responses)
        if isinstance(response, Exception):
            raise response
        response.request = httpx.Request("POST", url)
        return response


@pytest.mark.asyncio
async def test_call_mcp_tool_uses_protocol_after_helper_transport_failure(monkeypatch) -> None:
    responses = [
        httpx.ConnectError("helper unavailable"),
        httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}),
    ]
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: FakeAsyncClient(responses, **kwargs),
    )

    result = await call_mcp_tool("https://agent.example/mcp", "check", {})

    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_call_mcp_tool_raises_instead_of_fabricating_http_failure(monkeypatch) -> None:
    responses = [
        httpx.Response(404),
        httpx.Response(503, text="vendor unavailable"),
    ]
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: FakeAsyncClient(responses, **kwargs),
    )

    with pytest.raises(MCPToolCallError, match="HTTP 503: vendor unavailable"):
        await call_mcp_tool("https://agent.example/mcp", "process_refund", {})


@pytest.mark.asyncio
async def test_call_mcp_tool_raises_for_json_rpc_error(monkeypatch) -> None:
    responses = [
        httpx.Response(404),
        httpx.Response(
            200,
            content=json.dumps(
                {"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "missing"}}
            ),
        ),
    ]
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: FakeAsyncClient(responses, **kwargs),
    )

    with pytest.raises(MCPToolCallError, match="returned an error"):
        await call_mcp_tool("https://agent.example/mcp", "missing_tool", {})
