"""错误定义与转换工具：桥接内部异常到 HTTP/A2A 错误响应."""

from __future__ import annotations

from dataclasses import dataclass

from a2a.types import InternalError, InvalidParamsError
from a2a.utils.errors import ServerError
from fastapi.responses import JSONResponse

from strands_a2a_bridge.concurrency.user_lock import UserBusyError


class AuthenticationFailedError(RuntimeError):
    """认证失败（缺少用户 ID）."""
    pass


class MissingRequestContextError(RuntimeError):
    """请求上下文缺失."""
    pass


class ManagerUnavailableError(RuntimeError):
    """Agent 管理器不可用（获取 Agent 失败）."""
    pass


class AgentExecutionFailedError(RuntimeError):
    """Agent 执行失败."""
    pass


@dataclass(frozen=True, slots=True)
class ErrorContract:
    """错误契约：定义错误的标准化表示."""
    status_code: int          # HTTP 状态码
    error_code: str           # 业务错误码
    message: str              # 用户可读消息
    jsonrpc_code: int         # JSON-RPC 错误码


def _contract_for_error(error: Exception) -> ErrorContract:
    """将内部异常映射为标准化错误契约."""
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
    """将内部异常转换为 FastAPI JSONResponse（用于 HTTP 层错误处理）."""
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
    """将内部异常转换为 A2A ServerError（用于 A2A JSON-RPC 层错误处理）."""
    contract = _contract_for_error(error)
    data = {"code": contract.error_code, "request_id": request_id}
    if contract.jsonrpc_code == -32602:
        return ServerError(error=InvalidParamsError(message=contract.message, data=data))
    return ServerError(error=InternalError(message=contract.message, data=data))
