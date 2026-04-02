import pytest

from a2a.client.errors import A2AClientJSONRPCError
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


@pytest.mark.anyio
async def test_a2a_endpoint_is_mounted_inside_fastapi_app(async_client):
    response = await async_client.get("/a2a/.well-known/agent-card.json")
    assert response.status_code == 200
    card = response.json()
    assert card["defaultInputModes"] == ["text"]
    assert card["defaultOutputModes"] == ["text"]
    assert card["capabilities"]["streaming"] is True


@pytest.mark.anyio
async def test_a2a_streaming_returns_multiple_text_chunks(async_client):
    transport = JsonRpcTransport(async_client, url="http://testserver/a2a/")
    params = MessageSendParams.model_validate(
        {
            "message": {
                "kind": "message",
                "messageId": "msg-phase1-stream",
                "role": "user",
                "parts": [{"kind": "text", "text": "hi"}],
            }
        }
    )

    events = []
    async for event in transport.send_message_streaming(params):
        events.append(event)

    text_chunks = _collect_non_empty_text_chunks(events)
    assert text_chunks == ["hello", "from", "stub-agent"]
    assert len(text_chunks) > 1


@pytest.mark.anyio
async def test_a2a_streaming_rejects_non_text_parts(async_client):
    transport = JsonRpcTransport(async_client, url="http://testserver/a2a/")
    params = MessageSendParams.model_validate(
        {
            "message": {
                "kind": "message",
                "messageId": "msg-phase1-non-text",
                "role": "user",
                "parts": [
                    {
                        "kind": "file",
                        "file": {
                            "uri": "https://example.com/image.png",
                            "mimeType": "image/png",
                            "name": "image.png",
                        },
                    }
                ],
            }
        }
    )

    with pytest.raises(A2AClientJSONRPCError) as exc_info:
        async for _ in transport.send_message_streaming(params):
            pass

    assert exc_info.value.error.code == -32602
    assert exc_info.value.error.message == "Only text input parts are supported in Phase 1"
