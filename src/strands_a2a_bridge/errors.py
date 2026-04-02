from __future__ import annotations

from dataclasses import dataclass

from a2a.types import InternalError, InvalidParamsError
from a2a.utils.errors import ServerError
from fastapi.responses import JSONResponse

from strands_a2a_bridge.concurrency.user_lock import UserBusyError


class AuthenticationFailedError(RuntimeError):
    pass


class MissingRequestContextError(RuntimeError):
    pass


class ManagerUnavailableError(RuntimeError):
    pass


class AgentExecutionFailedError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ErrorContract:
    status_code: int
    error_code: str
    message: str
    jsonrpc_code: int


def _contract_for_error(error: Exception) -> ErrorContract:
    if isinstance(error, AuthenticationFailedError):
        return ErrorContract(401, "authentication_failed", "Missing x-user-id header", -32603)
    if isinstance(error, MissingRequestContextError):
        return ErrorContract(400, "missing_request_context", "Missing trusted request context", -32602)
    if isinstance(error, UserBusyError):
        return ErrorContract(409, "user_busy", "Another request is already active for this user", -32603)
    if isinstance(error, ManagerUnavailableError):
        return ErrorContract(503, "manager_unavailable", "Failed to acquire agent", -32603)
    if isinstance(error, AgentExecutionFailedError):
        return ErrorContract(500, "agent_execution_failed", "Agent execution failed", -32603)
    return ErrorContract(500, "internal_error", "Internal server error", -32603)


def to_http_error_response(error: Exception, *, request_id: str) -> JSONResponse:
    contract = _contract_for_error(error)
    return JSONResponse(
        status_code=contract.status_code,
        content={
            "error": {
                "code": contract.error_code,
                "message": contract.message,
                "request_id": request_id,
            }
        },
        headers={"x-request-id": request_id},
    )


def to_a2a_server_error(error: Exception, *, request_id: str) -> ServerError:
    contract = _contract_for_error(error)
    data = {"code": contract.error_code, "request_id": request_id}
    if contract.jsonrpc_code == -32602:
        return ServerError(error=InvalidParamsError(message=contract.message, data=data))
    return ServerError(error=InternalError(message=contract.message, data=data))
