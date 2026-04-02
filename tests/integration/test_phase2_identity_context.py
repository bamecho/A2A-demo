import httpx
import pytest

from a2a.client.errors import A2AClientHTTPError
from a2a.client.transports.jsonrpc import JsonRpcTransport
from a2a.types import MessageSendParams

from strands_a2a_bridge.a2a.server import (
    clear_last_observed_request_context,
    get_last_observed_request_context,
)
from strands_a2a_bridge.http.context import get_current_request_context


def _build_streaming_params(payload: str, metadata: dict | None = None) -> MessageSendParams:
    message: dict = {
        "kind": "message",
        "messageId": "msg-phase2",
        "role": "user",
        "parts": [{"kind": "text", "text": payload}],
    }
    if metadata is not None:
        message["metadata"] = metadata
    return MessageSendParams.model_validate({"message": message})


async def _drain_stream(transport: JsonRpcTransport, params: MessageSendParams) -> None:
    async for _ in transport.send_message_streaming(params):
        pass


@pytest.mark.anyio
async def test_phase2_context_is_observed_from_trusted_headers(app):
    clear_last_observed_request_context()
    transport = httpx.ASGITransport(app=app)
    headers = {
        "x-user-id": "trusted-user",
        "x-request-id": "trusted-request",
        "x-trace-id": "trusted-trace",
    }
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", headers=headers) as client:
        jsonrpc = JsonRpcTransport(client, url="http://testserver/a2a/")
        await _drain_stream(jsonrpc, _build_streaming_params("hi"))

    observed = get_last_observed_request_context()
    assert observed is not None
    assert observed.user_id == "trusted-user"
    assert observed.request_id == "trusted-request"
    assert observed.trace_id == "trusted-trace"


@pytest.mark.anyio
async def test_phase2_rejects_missing_x_user_id_before_a2a_execution(app):
    clear_last_observed_request_context()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        jsonrpc = JsonRpcTransport(client, url="http://testserver/a2a/")
        with pytest.raises(A2AClientHTTPError) as exc_info:
            await _drain_stream(
                jsonrpc,
                _build_streaming_params("hi", metadata={"user_id": "spoofed-from-payload"}),
            )

    assert exc_info.value.status_code == 401
    assert get_last_observed_request_context() is None


@pytest.mark.anyio
async def test_phase2_ignores_payload_identity_spoofing(app):
    clear_last_observed_request_context()
    transport = httpx.ASGITransport(app=app)
    headers = {
        "x-user-id": "header-user",
        "x-request-id": "header-request",
    }
    payload_metadata = {
        "user_id": "payload-user",
        "request_id": "payload-request",
        "trace_id": "payload-trace",
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", headers=headers) as client:
        jsonrpc = JsonRpcTransport(client, url="http://testserver/a2a/")
        await _drain_stream(jsonrpc, _build_streaming_params("hi", metadata=payload_metadata))

    observed = get_last_observed_request_context()
    assert observed is not None
    assert observed.user_id == "header-user"
    assert observed.request_id == "header-request"
    assert observed.trace_id is None


@pytest.mark.anyio
async def test_phase2_generates_request_id_and_clears_context_after_request(app):
    clear_last_observed_request_context()
    transport = httpx.ASGITransport(app=app)
    headers = {"x-user-id": "only-user"}
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", headers=headers) as client:
        jsonrpc = JsonRpcTransport(client, url="http://testserver/a2a/")
        await _drain_stream(jsonrpc, _build_streaming_params("hi"))

    observed = get_last_observed_request_context()
    assert observed is not None
    assert observed.user_id == "only-user"
    assert observed.request_id
    assert observed.trace_id is None
    assert get_current_request_context() is None
