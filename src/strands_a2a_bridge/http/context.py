"""请求上下文管理：基于 ContextVar 的线程安全存储."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RequestContext:
    """单个 HTTP 请求的上下文信息（由网关注入的头解析而来）."""
    user_id: str
    request_id: str
    trace_id: str | None


# 当前请求的上下文变量（默认 None，表示未设置）
_CURRENT_REQUEST_CONTEXT: ContextVar[RequestContext | None] = ContextVar(
    "current_request_context",
    default=None,
)


def set_current_request_context(ctx: RequestContext) -> None:
    """设置当前请求的上下文."""
    _CURRENT_REQUEST_CONTEXT.set(ctx)


def get_current_request_context() -> RequestContext | None:
    """获取当前请求的上下文（若无则返回 None）."""
    return _CURRENT_REQUEST_CONTEXT.get()


def clear_current_request_context() -> None:
    """清除当前请求的上下文."""
    _CURRENT_REQUEST_CONTEXT.set(None)
