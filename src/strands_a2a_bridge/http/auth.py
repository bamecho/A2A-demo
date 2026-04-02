"""HTTP 请求认证与请求上下文构建."""

from __future__ import annotations

from uuid import uuid4

from fastapi import Request

from strands_a2a_bridge.errors import AuthenticationFailedError
from strands_a2a_bridge.http.context import RequestContext

# 受信任请求头（由上游网关注入）
TRUSTED_USER_ID_HEADER = "x-user-id"
TRUSTED_REQUEST_ID_HEADER = "x-request-id"
TRUSTED_TRACE_ID_HEADER = "x-trace-id"


class AuthenticationError(AuthenticationFailedError):
    """认证失败时抛出的异常."""
    pass


def resolve_request_id(request: Request) -> str:
    """解析受信任的 request_id，缺失时自动生成."""
    request_id = (request.headers.get(TRUSTED_REQUEST_ID_HEADER) or "").strip()
    if not request_id:
        request_id = uuid4().hex
    return request_id


def build_request_context_from_headers(
    request: Request,
    *,
    request_id: str | None = None,
) -> RequestContext:
    """从请求头提取用户身份和追踪信息，构建 RequestContext.
    
    Raises:
        AuthenticationError: 缺少必需的 x-user-id 头
    """
    resolved_request_id = request_id or resolve_request_id(request)
    user_id = (request.headers.get(TRUSTED_USER_ID_HEADER) or "").strip()
    if not user_id:
        raise AuthenticationError("Missing x-user-id header")

    # request_id 可选，未提供时自动生成
    trace_id = request.headers.get(TRUSTED_TRACE_ID_HEADER)
    if trace_id is not None:
        trace_id = trace_id.strip() or None

    return RequestContext(
        user_id=user_id,
        request_id=resolved_request_id,
        trace_id=trace_id,
    )


def should_authenticate_request(request: Request) -> bool:
    """判断是否需要对请求进行认证（仅 POST /a2a/* 请求需要）."""
    return request.method.upper() == "POST" and request.url.path.startswith("/a2a")
