from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import httpx
import pytest

from a2a.client.transports.jsonrpc import JsonRpcTransport
from a2a.types import MessageSendParams

from strands_a2a_bridge.app import create_app
from strands_a2a_bridge.http.context import get_current_request_context


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


@dataclass(slots=True)
class Observation:
    stage: str
    user_id: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    agent_id: str | None = None
    route_action: str | None = None
    content_blocks: list[dict[str, Any]] | None = None
    chunk: str | None = None


class ObservableAgent:
    def __init__(self, user_id: str, agent_id: str, observations: list[Observation]) -> None:
        self.user_id = user_id
        self.agent_id = agent_id
        self.name = "observable-agent"
        self.description = "Observable agent for end-to-end integration testing"
        self._observations = observations

    async def stream_async(
        self,
        content_blocks: Sequence[Any],
        *,
        invocation_state: dict[str, Any] | None = None,
    ):
        _ = invocation_state
        request_context = get_current_request_context()
        normalized_blocks = [dict(block) for block in content_blocks if isinstance(block, dict)]
        self._observe(
            "agent.stream.start",
            request_context=request_context,
            content_blocks=normalized_blocks,
        )
        input_text = "\n".join(
            block["text"]
            for block in normalized_blocks
            if isinstance(block.get("text"), str) and block["text"]
        )
        for chunk in (
            f"agent {self.agent_id}",
            f"user {self.user_id}",
            f"request {request_context.request_id if request_context else '<missing>'}",
            f"trace {request_context.trace_id if request_context else '<missing>'}",
            f"input {input_text}",
        ):
            self._observe(
                "agent.stream.chunk",
                request_context=request_context,
                content_blocks=normalized_blocks,
                chunk=chunk,
            )
            yield {"data": chunk}
        yield {"result": f"done {input_text}"}

    def _observe(
        self,
        stage: str,
        *,
        request_context,
        content_blocks: list[dict[str, Any]] | None = None,
        chunk: str | None = None,
    ) -> None:
        observation = Observation(
            stage=stage,
            user_id=request_context.user_id if request_context else None,
            request_id=request_context.request_id if request_context else None,
            trace_id=request_context.trace_id if request_context else None,
            agent_id=self.agent_id,
            content_blocks=content_blocks,
            chunk=chunk,
        )
        self._observations.append(observation)
        print(
            "[server]",
            observation.stage,
            {
                "user_id": observation.user_id,
                "request_id": observation.request_id,
                "trace_id": observation.trace_id,
                "agent_id": observation.agent_id,
                "content_blocks": observation.content_blocks,
                "chunk": observation.chunk,
            },
        )


class ObservableAgentProvider:
    def __init__(self, observations: list[Observation]) -> None:
        self._observations = observations
        self._agents_by_user_id: dict[str, ObservableAgent] = {}
        self._next_agent_index = 1

    def get_or_create_agent(self, user_id: str) -> ObservableAgent:
        request_context = get_current_request_context()
        route_action = "reuse"
        agent = self._agents_by_user_id.get(user_id)
        if agent is None:
            route_action = "create"
            agent = ObservableAgent(
                user_id=user_id,
                agent_id=f"observable-agent-{self._next_agent_index}",
                observations=self._observations,
            )
            self._next_agent_index += 1
            self._agents_by_user_id[user_id] = agent

        observation = Observation(
            stage="provider.route",
            user_id=user_id,
            request_id=request_context.request_id if request_context else None,
            trace_id=request_context.trace_id if request_context else None,
            agent_id=agent.agent_id,
            route_action=route_action,
        )
        self._observations.append(observation)
        print(
            "[server]",
            observation.stage,
            {
                "user_id": observation.user_id,
                "request_id": observation.request_id,
                "trace_id": observation.trace_id,
                "agent_id": observation.agent_id,
                "route_action": observation.route_action,
            },
        )
        return agent


async def _send_stream(
    app,
    *,
    user_id: str,
    request_id: str,
    trace_id: str,
    message_id: str,
    texts: tuple[str, ...],
) -> list[str]:
    params = _build_streaming_params(message_id, *texts)
    print(
        "[client] send",
        {
            "user_id": user_id,
            "request_id": request_id,
            "trace_id": trace_id,
            "payload": params.model_dump(mode="json", by_alias=True, exclude_none=True),
        },
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={
            "x-user-id": user_id,
            "x-request-id": request_id,
            "x-trace-id": trace_id,
        },
    ) as client:
        jsonrpc = JsonRpcTransport(client, url="http://testserver/a2a/")
        events = []
        async for event in jsonrpc.send_message_streaming(params):
            payload = event.model_dump(mode="json", by_alias=True, exclude_none=True)
            print("[client] recv", payload)
            events.append(event)
    return _collect_non_empty_text_chunks(events)


@pytest.mark.anyio
async def test_a2a_sdk_end_to_end_logs_request_processing_and_agent_routing() -> None:
    observations: list[Observation] = []
    app = create_app(provider=ObservableAgentProvider(observations))

    first_chunks = await _send_stream(
        app,
        user_id="alpha-user",
        request_id="req-e2e-alpha-1",
        trace_id="trace-e2e-alpha-1",
        message_id="msg-e2e-alpha-1",
        texts=("hello", "world"),
    )
    second_chunks = await _send_stream(
        app,
        user_id="alpha-user",
        request_id="req-e2e-alpha-2",
        trace_id="trace-e2e-alpha-2",
        message_id="msg-e2e-alpha-2",
        texts=("follow", "up"),
    )
    third_chunks = await _send_stream(
        app,
        user_id="beta-user",
        request_id="req-e2e-beta-1",
        trace_id="trace-e2e-beta-1",
        message_id="msg-e2e-beta-1",
        texts=("beta", "request"),
    )

    assert first_chunks == [
        "agent observable-agent-1",
        "user alpha-user",
        "request req-e2e-alpha-1",
        "trace trace-e2e-alpha-1",
        "input hello\nworld",
    ]
    assert second_chunks == [
        "agent observable-agent-1",
        "user alpha-user",
        "request req-e2e-alpha-2",
        "trace trace-e2e-alpha-2",
        "input follow\nup",
    ]
    assert third_chunks == [
        "agent observable-agent-2",
        "user beta-user",
        "request req-e2e-beta-1",
        "trace trace-e2e-beta-1",
        "input beta\nrequest",
    ]

    provider_routes = [item for item in observations if item.stage == "provider.route"]
    assert [
        (item.user_id, item.agent_id, item.route_action, item.request_id, item.trace_id)
        for item in provider_routes
    ] == [
        ("alpha-user", "observable-agent-1", "create", "req-e2e-alpha-1", "trace-e2e-alpha-1"),
        ("alpha-user", "observable-agent-1", "reuse", "req-e2e-alpha-2", "trace-e2e-alpha-2"),
        ("beta-user", "observable-agent-2", "create", "req-e2e-beta-1", "trace-e2e-beta-1"),
    ]

    stream_starts = [item for item in observations if item.stage == "agent.stream.start"]
    assert [
        (item.user_id, item.agent_id, item.request_id, item.trace_id, item.content_blocks)
        for item in stream_starts
    ] == [
        (
            "alpha-user",
            "observable-agent-1",
            "req-e2e-alpha-1",
            "trace-e2e-alpha-1",
            [{"text": "hello\nworld"}],
        ),
        (
            "alpha-user",
            "observable-agent-1",
            "req-e2e-alpha-2",
            "trace-e2e-alpha-2",
            [{"text": "follow\nup"}],
        ),
        (
            "beta-user",
            "observable-agent-2",
            "req-e2e-beta-1",
            "trace-e2e-beta-1",
            [{"text": "beta\nrequest"}],
        ),
    ]
