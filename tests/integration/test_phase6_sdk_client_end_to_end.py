from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
import pytest

from a2a.client import ClientConfig, ClientFactory, create_text_message_object

from strands_a2a_bridge.a2a.server import (
    clear_last_observed_agent_id,
    clear_last_observed_request_context,
    get_last_observed_agent_id,
    get_last_observed_request_context,
)


@dataclass(slots=True)
class SdkRunTrace:
    task_id: str | None
    task_state: str | None
    text_chunks: list[str]
    event_lines: list[str]


async def _send_message_via_sdk_client(
    app,
    *,
    user_id: str,
    request_id: str,
    trace_id: str,
    text: str,
) -> SdkRunTrace:
    http_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        headers={
            "x-user-id": user_id,
            "x-request-id": request_id,
            "x-trace-id": trace_id,
        },
    )
    sdk_client = await ClientFactory.connect(
        "http://testserver/a2a",
        client_config=ClientConfig(httpx_client=http_client),
    )
    message = create_text_message_object(content=text)
    text_chunks: list[str] = []
    event_lines = [
        f"client connected user_id={user_id} request_id={request_id} trace_id={trace_id}",
        f"client sending message_id={message.message_id} text={text!r}",
    ]
    last_task_id: str | None = None
    last_task_state: str | None = None

    try:
        async for task, update in sdk_client.send_message(message):
            last_task_id = task.id
            last_task_state = task.status.state.value
            update_kind = "initial-task" if update is None else update.kind
            event_lines.append(
                f"client received task_id={task.id} state={task.status.state.value} update={update_kind}"
            )
            if update is None:
                continue

            payload = update.model_dump(mode="json", by_alias=True, exclude_none=True)
            artifact = payload.get("artifact")
            if artifact:
                for part in artifact.get("parts", []):
                    text_value = part.get("text")
                    if text_value:
                        text_chunks.append(text_value)
                        event_lines.append(
                            f"client artifact text task_id={task.id} chunk={text_value!r}"
                        )
    finally:
        await sdk_client.close()

    return SdkRunTrace(
        task_id=last_task_id,
        task_state=last_task_state,
        text_chunks=text_chunks,
        event_lines=event_lines,
    )


@pytest.mark.anyio
async def test_phase6_sdk_client_end_to_end_routes_requests_with_full_trace(app, caplog) -> None:
    caplog.set_level(logging.INFO, logger="strands_a2a_bridge")
    clear_last_observed_request_context()
    clear_last_observed_agent_id()

    first = await _send_message_via_sdk_client(
        app,
        user_id="sdk-user-a",
        request_id="req-phase6-a-1",
        trace_id="trace-phase6-a-1",
        text="alpha from sdk",
    )
    second = await _send_message_via_sdk_client(
        app,
        user_id="sdk-user-a",
        request_id="req-phase6-a-2",
        trace_id="trace-phase6-a-2",
        text="beta from sdk",
    )
    third = await _send_message_via_sdk_client(
        app,
        user_id="sdk-user-b",
        request_id="req-phase6-b-1",
        trace_id="trace-phase6-b-1",
        text="gamma from sdk",
    )

    print("\n=== SDK CLIENT TRACE A1 ===")
    for line in first.event_lines:
        print(line)

    print("\n=== SDK CLIENT TRACE A2 ===")
    for line in second.event_lines:
        print(line)

    print("\n=== SDK CLIENT TRACE B1 ===")
    for line in third.event_lines:
        print(line)

    print("\n=== SERVER LOG TRACE ===")
    for record in caplog.records:
        print(f"{record.levelname} {record.name} {record.getMessage()}")

    observed_context = get_last_observed_request_context()
    assert observed_context is not None
    assert observed_context.user_id == "sdk-user-b"
    assert observed_context.request_id == "req-phase6-b-1"
    assert observed_context.trace_id == "trace-phase6-b-1"

    assert get_last_observed_agent_id() == "fake-agent-1"

    assert first.text_chunks == ["turn 1", "input alpha from sdk", "previous <none>"]
    assert second.text_chunks == ["turn 2", "input beta from sdk", "previous alpha from sdk"]
    assert third.text_chunks == ["turn 1", "input gamma from sdk", "previous <none>"]

    assert first.task_id
    assert second.task_id
    assert third.task_id
    assert first.task_state == "completed"
    assert second.task_state == "completed"
    assert third.task_state == "completed"

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "request_context_middleware authenticated request_id=req-phase6-a-1 user_id=sdk-user-a trace_id=trace-phase6-a-1" in log_text
    assert "executor resolved trusted context request_id=req-phase6-a-1 user_id=sdk-user-a" in log_text
    assert "executor obtained agent request_id=req-phase6-a-1 user_id=sdk-user-a agent_id=stub-agent" in log_text
    assert "fake-provider resolved agent user_id=sdk-user-a agent_id=stub-agent created=True" in log_text
    assert "fake-provider resolved agent user_id=sdk-user-a agent_id=stub-agent created=False" in log_text
    assert "fake-provider resolved agent user_id=sdk-user-b agent_id=fake-agent-1 created=True" in log_text
    assert "fake-agent stream start user_id=sdk-user-a agent_id=stub-agent turn=1 input='alpha from sdk' previous='<none>'" in log_text
    assert "fake-agent stream start user_id=sdk-user-a agent_id=stub-agent turn=2 input='beta from sdk' previous='alpha from sdk'" in log_text
    assert "fake-agent stream start user_id=sdk-user-b agent_id=fake-agent-1 turn=1 input='gamma from sdk' previous='<none>'" in log_text
