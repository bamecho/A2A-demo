from a2a.server.agent_execution import RequestContext
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.apps.jsonrpc.jsonrpc_app import DefaultCallContextBuilder
from a2a.server.context import ServerCallContext
from a2a.server.events import EventQueue
from a2a.types import InvalidParamsError, Part, TextPart
from a2a.utils.errors import ServerError
from fastapi import FastAPI
from strands.multiagent.a2a.executor import StrandsA2AExecutor
from strands.multiagent.a2a.server import A2AServer

from strands_a2a_bridge.a2a.mapping import map_text_parts_to_content_blocks
from strands_a2a_bridge.a2a.stub_agent import build_stub_agent
from strands_a2a_bridge.config import AppConfig
from strands_a2a_bridge.http.context import (
    RequestContext as TrustedRequestContext,
    clear_current_request_context,
    get_current_request_context,
    set_current_request_context,
)
from strands_a2a_bridge.manager.contracts import AgentProvider, ManagedAgent
from strands_a2a_bridge.manager.fake import FakeAgentProvider

NON_TEXT_INPUT_ERROR = "Only text input parts are supported in Phase 1"
MISSING_CONTEXT_ERROR = "Missing trusted request context"

_last_observed_request_context: TrustedRequestContext | None = None
_last_observed_agent_id: str | None = None


def get_last_observed_request_context() -> TrustedRequestContext | None:
    return _last_observed_request_context


def clear_last_observed_request_context() -> None:
    global _last_observed_request_context
    _last_observed_request_context = None


def get_last_observed_agent_id() -> str | None:
    return _last_observed_agent_id


def clear_last_observed_agent_id() -> None:
    global _last_observed_agent_id
    _last_observed_agent_id = None


class ManagerBackedStrandsA2AExecutor(StrandsA2AExecutor):
    def __init__(
        self,
        provider: AgentProvider,
        bootstrap_agent: ManagedAgent,
        *,
        enable_a2a_compliant_streaming: bool = False,
    ) -> None:
        super().__init__(
            bootstrap_agent,
            enable_a2a_compliant_streaming=enable_a2a_compliant_streaming,
        )
        self._provider = provider

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        global _last_observed_agent_id, _last_observed_request_context

        trusted_context = None
        if context.call_context is not None:
            trusted_context = context.call_context.state.get("trusted_request_context")
        if trusted_context is None:
            trusted_context = get_current_request_context()
        if trusted_context is None:
            raise ServerError(error=InvalidParamsError(message=MISSING_CONTEXT_ERROR))
        _last_observed_request_context = trusted_context
        set_current_request_context(trusted_context)
        agent = self._provider.get_or_create_agent(trusted_context.user_id)
        _last_observed_agent_id = agent.agent_id

        message = context.message
        try:
            if message is None:
                raise ServerError(error=InvalidParamsError(message="Message is required"))
            if any(not isinstance(part.root, TextPart) for part in message.parts):
                raise ServerError(error=InvalidParamsError(message=NON_TEXT_INPUT_ERROR))
            local_executor = Phase4TextOnlyStrandsA2AExecutor(
                agent,
                enable_a2a_compliant_streaming=self.enable_a2a_compliant_streaming,
            )
            await local_executor.execute(context, event_queue)
        finally:
            clear_current_request_context()


class Phase4TextOnlyStrandsA2AExecutor(StrandsA2AExecutor):
    def _convert_a2a_parts_to_content_blocks(self, parts: list[Part]) -> list[dict[str, str]]:
        return map_text_parts_to_content_blocks(parts)


class TrustedRequestContextBuilder(DefaultCallContextBuilder):
    def build(self, request) -> ServerCallContext:
        call_context = super().build(request)
        trusted_request_context = getattr(request.state, "trusted_request_context", None)
        if trusted_request_context is not None:
            call_context.state["trusted_request_context"] = trusted_request_context
        return call_context


def build_a2a_router(config: AppConfig, provider: AgentProvider | None = None) -> FastAPI:
    resolved_provider = provider or FakeAgentProvider()
    bootstrap_agent = build_stub_agent()
    public_a2a_url = f"{config.public_url.rstrip('/')}/a2a"
    server = A2AServer(
        agent=bootstrap_agent,
        http_url=public_a2a_url,
        serve_at_root=True,
        skills=[],
        enable_a2a_compliant_streaming=True,
    )
    server.request_handler.agent_executor = ManagerBackedStrandsA2AExecutor(
        resolved_provider,
        bootstrap_agent,
        enable_a2a_compliant_streaming=True,
    )
    application = A2AFastAPIApplication(
        agent_card=server.public_agent_card,
        http_handler=server.request_handler,
        context_builder=TrustedRequestContextBuilder(),
    )
    return application.build(title=f"{config.service_name} A2A")
