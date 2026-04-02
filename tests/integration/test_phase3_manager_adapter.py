import httpx
import pytest

from a2a.client.transports.jsonrpc import JsonRpcTransport
from a2a.types import MessageSendParams

from strands_a2a_bridge.a2a.server import (
    clear_last_observed_agent_id,
    get_last_observed_agent_id,
)


def _build_streaming_params(message_id: str) -> MessageSendParams:
    return MessageSendParams.model_validate(
        {
            "message": {
                "kind": "message",
                "messageId": message_id,
                "role": "user",
                "parts": [{"kind": "text", "text": "hi"}],
            }
        }
    )


async def _drain_stream(app, user_id: str, message_id: str) -> str | None:
    transport = httpx.ASGITransport(app=app)
    headers = {"x-user-id": user_id}
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers=headers,
    ) as client:
        jsonrpc = JsonRpcTransport(client, url="http://testserver/a2a/")
        async for _ in jsonrpc.send_message_streaming(_build_streaming_params(message_id)):
            pass
    return get_last_observed_agent_id()


@pytest.mark.anyio
async def test_phase3_reuses_same_agent_for_same_user(app):
    clear_last_observed_agent_id()

    first_agent_id = await _drain_stream(app, "same-user", "msg-phase3-1")
    second_agent_id = await _drain_stream(app, "same-user", "msg-phase3-2")

    assert first_agent_id is not None
    assert second_agent_id == first_agent_id


@pytest.mark.anyio
async def test_phase3_isolates_agents_for_different_users(app):
    clear_last_observed_agent_id()

    first_agent_id = await _drain_stream(app, "user-a", "msg-phase3-a")
    second_agent_id = await _drain_stream(app, "user-b", "msg-phase3-b")

    assert first_agent_id is not None
    assert second_agent_id is not None
    assert first_agent_id != second_agent_id
