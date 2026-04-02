from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from typing import Any

import anyio
import httpx
import pytest

from a2a.client.errors import A2AClientJSONRPCError
from a2a.client.transports.jsonrpc import JsonRpcTransport
from a2a.types import MessageSendParams

from strands_a2a_bridge.app import create_app


def _build_streaming_params(message_id: str, text: str) -> MessageSendParams:
    return MessageSendParams.model_validate(
        {
            "message": {
                "kind": "message",
                "messageId": message_id,
                "role": "user",
                "parts": [{"kind": "text", "text": text}],
            }
        }
    )


def _build_jsonrpc_payload(message_id: str, text: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "method": "message/stream",
        "params": _build_streaming_params(message_id, text).model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
        ),
    }


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


async def _drain_stream(transport: JsonRpcTransport, params: MessageSendParams) -> list[str]:
    events = []
    async for event in transport.send_message_streaming(params):
        events.append(event)
    return _collect_non_empty_text_chunks(events)


class BlockingAgent:
    def __init__(
        self,
        user_id: str,
        *,
        tracker: "ExecutionTracker",
        fail_during_stream: bool = False,
    ) -> None:
        self.user_id = user_id
        self.agent_id = f"blocking-{user_id}"
        self.name = "phase5-blocking-agent"
        self.description = "Phase 5 blocking agent"
        self._tracker = tracker
        self._fail_during_stream = fail_during_stream

    async def stream_async(
        self,
        content_blocks: Sequence[Any],
        *,
        invocation_state: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        _ = invocation_state
        text = content_blocks[0]["text"]
        await self._tracker.on_stream_start(self.user_id)
        try:
            if self._fail_during_stream:
                raise RuntimeError("agent boom")
            yield {"data": f"user {self.user_id}"}
            yield {"data": f"input {text}"}
            await self._tracker.wait_for_release()
            yield {"result": f"done {text}"}
        finally:
            await self._tracker.on_stream_finish()


class BlockingAgentProvider:
    def __init__(
        self,
        *,
        tracker: "ExecutionTracker",
        failing_user_id: str | None = None,
        fail_on_get: bool = False,
    ) -> None:
        self._tracker = tracker
        self._failing_user_id = failing_user_id
        self._fail_on_get = fail_on_get
        self._agents: dict[str, BlockingAgent] = {}

    def get_or_create_agent(self, user_id: str) -> BlockingAgent:
        if self._fail_on_get:
            raise RuntimeError("provider boom")
        agent = self._agents.get(user_id)
        if agent is None:
            agent = BlockingAgent(
                user_id,
                tracker=self._tracker,
                fail_during_stream=user_id == self._failing_user_id,
            )
            self._agents[user_id] = agent
        return agent


class ExecutionTracker:
    def __init__(self, expected_starts: int = 1) -> None:
        self._lock = anyio.Lock()
        self._release = anyio.Event()
        self._all_started = anyio.Event()
        self.expected_starts = expected_starts
        self.started = 0
        self.active = 0
        self.max_active = 0

    async def on_stream_start(self, user_id: str) -> None:
        _ = user_id
        async with self._lock:
            self.started += 1
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            if self.started >= self.expected_starts:
                self._all_started.set()

    async def on_stream_finish(self) -> None:
        async with self._lock:
            self.active -= 1

    async def wait_until_expected_starts(self) -> None:
        await self._all_started.wait()

    async def wait_for_release(self) -> None:
        await self._release.wait()

    def release(self) -> None:
        self._release.set()


@pytest.mark.anyio
async def test_phase5_rejects_missing_x_user_id_with_stable_http_error_contract() -> None:
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    payload = _build_jsonrpc_payload("msg-phase5-auth", "hello")

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/a2a/",
            json=payload,
            headers={"x-request-id": "req-phase5-auth"},
        )

    assert response.status_code == 401
    assert response.headers["x-request-id"] == "req-phase5-auth"
    assert response.json() == {
        "error": {
            "code": "authentication_failed",
            "message": "Missing x-user-id header",
            "request_id": "req-phase5-auth",
        }
    }


@pytest.mark.anyio
async def test_phase5_rejects_same_user_concurrent_request_as_busy() -> None:
    tracker = ExecutionTracker(expected_starts=1)
    app = create_app(provider=BlockingAgentProvider(tracker=tracker))

    transport = httpx.ASGITransport(app=app)
    headers = {"x-user-id": "busy-user", "x-request-id": "req-phase5-busy-1"}
    params = _build_streaming_params("msg-phase5-busy-1", "hello")

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", headers=headers) as first_client:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"x-user-id": "busy-user", "x-request-id": "req-phase5-busy-2"},
        ) as second_client:
            first_transport = JsonRpcTransport(first_client, url="http://testserver/a2a/")
            second_transport = JsonRpcTransport(second_client, url="http://testserver/a2a/")
            first_chunks: list[str] = []

            async def run_first_request() -> None:
                nonlocal first_chunks
                first_chunks = await _drain_stream(first_transport, params)

            async with anyio.create_task_group() as task_group:
                task_group.start_soon(run_first_request)
                await tracker.wait_until_expected_starts()

                with pytest.raises(A2AClientJSONRPCError) as exc_info:
                    await _drain_stream(
                        second_transport,
                        _build_streaming_params("msg-phase5-busy-2", "follow-up"),
                    )

                assert exc_info.value.error.code == -32603
                assert exc_info.value.error.message == "Another request is already active for this user"
                assert exc_info.value.error.data == {
                    "code": "user_busy",
                    "request_id": "req-phase5-busy-2",
                }

                tracker.release()

            assert first_chunks[:2] == ["user busy-user", "input hello"]


@pytest.mark.anyio
async def test_phase5_allows_different_users_to_run_in_parallel() -> None:
    tracker = ExecutionTracker(expected_starts=2)
    app = create_app(provider=BlockingAgentProvider(tracker=tracker))
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"x-user-id": "parallel-user-a", "x-request-id": "req-phase5-parallel-a"},
    ) as first_client:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"x-user-id": "parallel-user-b", "x-request-id": "req-phase5-parallel-b"},
        ) as second_client:
            first_transport = JsonRpcTransport(first_client, url="http://testserver/a2a/")
            second_transport = JsonRpcTransport(second_client, url="http://testserver/a2a/")
            results: dict[str, list[str]] = {}

            async def run_request(name: str, transport: JsonRpcTransport, message_id: str, text: str) -> None:
                results[name] = await _drain_stream(
                    transport,
                    _build_streaming_params(message_id, text),
                )

            async with anyio.create_task_group() as task_group:
                task_group.start_soon(
                    run_request,
                    "first",
                    first_transport,
                    "msg-phase5-parallel-a",
                    "from a",
                )
                task_group.start_soon(
                    run_request,
                    "second",
                    second_transport,
                    "msg-phase5-parallel-b",
                    "from b",
                )
                await tracker.wait_until_expected_starts()
                tracker.release()

    assert tracker.max_active == 2
    assert results["first"][:2] == ["user parallel-user-a", "input from a"]
    assert results["second"][:2] == ["user parallel-user-b", "input from b"]


@pytest.mark.anyio
async def test_phase5_maps_manager_failure_to_stable_jsonrpc_error() -> None:
    tracker = ExecutionTracker()
    app = create_app(provider=BlockingAgentProvider(tracker=tracker, fail_on_get=True))
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"x-user-id": "manager-user", "x-request-id": "req-phase5-manager"},
    ) as client:
        jsonrpc = JsonRpcTransport(client, url="http://testserver/a2a/")
        with pytest.raises(A2AClientJSONRPCError) as exc_info:
            await _drain_stream(
                jsonrpc,
                _build_streaming_params("msg-phase5-manager", "hello"),
            )

    assert exc_info.value.error.code == -32603
    assert exc_info.value.error.message == "Failed to acquire agent"
    assert exc_info.value.error.data == {
        "code": "manager_unavailable",
        "request_id": "req-phase5-manager",
    }
    assert "provider boom" not in json.dumps(exc_info.value.error.model_dump(mode="json"))


@pytest.mark.anyio
async def test_phase5_maps_agent_failure_to_stable_jsonrpc_error() -> None:
    tracker = ExecutionTracker()
    app = create_app(
        provider=BlockingAgentProvider(
            tracker=tracker,
            failing_user_id="agent-user",
        )
    )
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"x-user-id": "agent-user", "x-request-id": "req-phase5-agent"},
    ) as client:
        jsonrpc = JsonRpcTransport(client, url="http://testserver/a2a/")
        with pytest.raises(A2AClientJSONRPCError) as exc_info:
            await _drain_stream(
                jsonrpc,
                _build_streaming_params("msg-phase5-agent", "hello"),
            )

    assert exc_info.value.error.code == -32603
    assert exc_info.value.error.message == "Agent execution failed"
    assert exc_info.value.error.data == {
        "code": "agent_execution_failed",
        "request_id": "req-phase5-agent",
    }
    assert "agent boom" not in json.dumps(exc_info.value.error.model_dump(mode="json"))
