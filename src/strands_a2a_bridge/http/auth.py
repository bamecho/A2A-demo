from __future__ import annotations

from uuid import uuid4

from fastapi import Request

from strands_a2a_bridge.http.context import RequestContext

TRUSTED_USER_ID_HEADER = "x-user-id"
TRUSTED_REQUEST_ID_HEADER = "x-request-id"
TRUSTED_TRACE_ID_HEADER = "x-trace-id"


class AuthenticationError(ValueError):
    pass


def build_request_context_from_headers(request: Request) -> RequestContext:
    user_id = (request.headers.get(TRUSTED_USER_ID_HEADER) or "").strip()
    if not user_id:
        raise AuthenticationError("Missing x-user-id header")

    request_id = (request.headers.get(TRUSTED_REQUEST_ID_HEADER) or "").strip()
    if not request_id:
        request_id = uuid4().hex

    trace_id = request.headers.get(TRUSTED_TRACE_ID_HEADER)
    if trace_id is not None:
        trace_id = trace_id.strip() or None

    return RequestContext(user_id=user_id, request_id=request_id, trace_id=trace_id)


def should_authenticate_request(request: Request) -> bool:
    return request.method.upper() == "POST" and request.url.path.startswith("/a2a")
