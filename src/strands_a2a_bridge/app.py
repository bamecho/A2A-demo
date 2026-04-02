from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from strands_a2a_bridge.a2a.server import build_a2a_router
from strands_a2a_bridge.config import AppConfig
from strands_a2a_bridge.http.auth import (
    AuthenticationError,
    build_request_context_from_headers,
    should_authenticate_request,
)
from strands_a2a_bridge.http.context import clear_current_request_context, set_current_request_context


def create_app(config: AppConfig | None = None) -> FastAPI:
    app_config = config or AppConfig()
    app = FastAPI(title=app_config.service_name)

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        if not should_authenticate_request(request):
            return await call_next(request)

        try:
            request_context = build_request_context_from_headers(request)
        except AuthenticationError as exc:
            return JSONResponse(status_code=401, content={"detail": str(exc)})

        request.state.trusted_request_context = request_context
        set_current_request_context(request_context)
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = request_context.request_id
            return response
        finally:
            clear_current_request_context()

    app.mount("/a2a", build_a2a_router(app_config))
    return app
