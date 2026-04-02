"""FastAPI 应用入口，挂载 A2A 路由并配置中间件."""

from fastapi import FastAPI, Request

from strands_a2a_bridge.a2a.server import build_a2a_router
from strands_a2a_bridge.config import AppConfig
from strands_a2a_bridge.errors import to_http_error_response
from strands_a2a_bridge.http.auth import (
    AuthenticationError,
    build_request_context_from_headers,
    resolve_request_id,
    should_authenticate_request,
)
from strands_a2a_bridge.http.context import clear_current_request_context, set_current_request_context
from strands_a2a_bridge.manager.contracts import AgentProvider


def create_app(
    config: AppConfig | None = None,
    *,
    provider: AgentProvider | None = None,
) -> FastAPI:
    """创建 FastAPI 应用，配置请求上下文中间件和 A2A 路由."""
    app_config = config or AppConfig()
    app = FastAPI(title=app_config.service_name)

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        """请求中间件：验证请求头、构建请求上下文并注入到请求状态."""
        if not should_authenticate_request(request):
            return await call_next(request)

        request_id = resolve_request_id(request)
        try:
            request_context = build_request_context_from_headers(
                request,
                request_id=request_id,
            )
        except AuthenticationError as exc:
            return to_http_error_response(exc, request_id=request_id)

        request.state.trusted_request_context = request_context
        set_current_request_context(request_context)
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = request_context.request_id
            return response
        finally:
            clear_current_request_context()

    app.mount("/a2a", build_a2a_router(app_config, provider=provider))
    return app
