import httpx
import pytest

from a2a.client.transports.jsonrpc import JsonRpcTransport
from a2a.types import MessageSendParams


def _collect_non_empty_text_chunks(events) -> list[str]:
    chunks: list[str] = []
    for event in events:
        payload = event.model_dump(mode="json", by_alias=True, exclude_none=True)
        artifact = payload.get("artifact")
        if not artifact:
            continue
        for part in artifact.get("parts", []):
            if part.get("kind") == "text" and part.get("text"):
                chunks.append(part["text"])
    return chunks


def _build_streaming_params(message_id: str, *texts: str) -> MessageSendParams:
    return MessageSendParams.model_validate(
        {
            "message": {
                "kind": "message",
                "messageId": message_id,
                "role": "user",
                "parts": [{"kind": "text", "text": text} for text in texts],
            }
        }
    )


async def _stream_text_chunks(app, user_id: str, message_id: str, *texts: str) -> list[str]:
    transport = httpx.ASGITransport(app=app)
    headers = {"x-user-id": user_id}
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers=headers,
    ) as client:
        jsonrpc = JsonRpcTransport(client, url="http://testserver/a2a/")
        events = []
        async for event in jsonrpc.send_message_streaming(
            _build_streaming_params(message_id, *texts)
        ):
            events.append(event)
    return _collect_non_empty_text_chunks(events)


@pytest.mark.anyio
async def test_phase4_maps_text_input_into_single_internal_prompt(app):
    text_chunks = await _stream_text_chunks(
        app,
        "phase4-mapper-user",
        "msg-phase4-mapper",
        "alpha",
        "beta",
    )

    assert text_chunks == ["turn 1", "input alpha\nbeta", "previous <none>"]


@pytest.mark.anyio
async def test_phase4_same_user_requests_observe_reused_session_state(app):
    first_chunks = await _stream_text_chunks(
        app,
        "phase4-session-user",
        "msg-phase4-session-1",
        "first question",
    )
    second_chunks = await _stream_text_chunks(
        app,
        "phase4-session-user",
        "msg-phase4-session-2",
        "second question",
    )

    assert first_chunks == ["turn 1", "input first question", "previous <none>"]
    assert second_chunks == ["turn 2", "input second question", "previous first question"]


@pytest.mark.anyio
async def test_phase4_different_users_keep_isolated_session_state(app):
    await _stream_text_chunks(
        app,
        "phase4-user-a",
        "msg-phase4-user-a-1",
        "first from user a",
    )
    second_user_chunks = await _stream_text_chunks(
        app,
        "phase4-user-b",
        "msg-phase4-user-b-1",
        "first from user b",
    )

    assert second_user_chunks == ["turn 1", "input first from user b", "previous <none>"]
