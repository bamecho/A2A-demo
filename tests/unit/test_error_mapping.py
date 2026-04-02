from fastapi.responses import JSONResponse

from strands_a2a_bridge.errors import (
    AgentExecutionFailedError,
    AuthenticationFailedError,
    ManagerUnavailableError,
    MissingRequestContextError,
    UserBusyError,
    to_a2a_server_error,
    to_http_error_response,
)


def _response_json(response: JSONResponse) -> dict:
    return dict(response.body and __import__("json").loads(response.body) or {})


def test_http_error_mapping_returns_stable_public_contract() -> None:
    response = to_http_error_response(
        AuthenticationFailedError(),
        request_id="req-auth",
    )

    assert response.status_code == 401
    assert response.headers["x-request-id"] == "req-auth"
    assert _response_json(response) == {
        "error": {
            "code": "authentication_failed",
            "message": "Missing x-user-id header",
            "request_id": "req-auth",
        }
    }


def test_busy_error_maps_to_stable_a2a_server_error() -> None:
    server_error = to_a2a_server_error(UserBusyError(), request_id="req-busy")

    assert server_error.error is not None
    assert server_error.error.code == -32603
    assert server_error.error.message == "Another request is already active for this user"
    assert server_error.error.data == {
        "code": "user_busy",
        "request_id": "req-busy",
    }


def test_manager_error_does_not_leak_internal_details() -> None:
    server_error = to_a2a_server_error(
        ManagerUnavailableError(),
        request_id="req-manager",
    )

    assert server_error.error is not None
    assert server_error.error.code == -32603
    assert server_error.error.message == "Failed to acquire agent"
    assert server_error.error.data == {
        "code": "manager_unavailable",
        "request_id": "req-manager",
    }


def test_agent_error_does_not_leak_internal_details() -> None:
    server_error = to_a2a_server_error(
        AgentExecutionFailedError(),
        request_id="req-agent",
    )

    assert server_error.error is not None
    assert server_error.error.code == -32603
    assert server_error.error.message == "Agent execution failed"
    assert server_error.error.data == {
        "code": "agent_execution_failed",
        "request_id": "req-agent",
    }


def test_missing_context_maps_to_invalid_params_contract() -> None:
    server_error = to_a2a_server_error(
        MissingRequestContextError(),
        request_id="req-context",
    )

    assert server_error.error is not None
    assert server_error.error.code == -32602
    assert server_error.error.message == "Missing trusted request context"
    assert server_error.error.data == {
        "code": "missing_request_context",
        "request_id": "req-context",
    }
