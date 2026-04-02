from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RequestContext:
    user_id: str
    request_id: str
    trace_id: str | None


_CURRENT_REQUEST_CONTEXT: ContextVar[RequestContext | None] = ContextVar(
    "current_request_context",
    default=None,
)


def set_current_request_context(ctx: RequestContext) -> None:
    _CURRENT_REQUEST_CONTEXT.set(ctx)


def get_current_request_context() -> RequestContext | None:
    return _CURRENT_REQUEST_CONTEXT.get()


def clear_current_request_context() -> None:
    _CURRENT_REQUEST_CONTEXT.set(None)
