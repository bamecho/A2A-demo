from strands_a2a_bridge.http.context import (
    RequestContext,
    clear_current_request_context,
    get_current_request_context,
    set_current_request_context,
)


def test_request_context_set_and_get_roundtrip() -> None:
    clear_current_request_context()
    ctx = RequestContext(user_id="u-1", request_id="req-1", trace_id="trace-1")
    set_current_request_context(ctx)

    current = get_current_request_context()
    assert current is not None
    assert current.user_id == "u-1"
    assert current.request_id == "req-1"
    assert current.trace_id == "trace-1"


def test_request_context_clear_removes_current_value() -> None:
    set_current_request_context(RequestContext(user_id="u-2", request_id="req-2", trace_id=None))
    clear_current_request_context()
    assert get_current_request_context() is None
