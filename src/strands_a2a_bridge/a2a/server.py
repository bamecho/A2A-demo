"""A2A 服务层：构建路由、执行器及上下文处理."""

from a2a.server.agent_execution import RequestContext
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.apps.jsonrpc.jsonrpc_app import DefaultCallContextBuilder
from a2a.server.context import ServerCallContext
from a2a.server.events import EventQueue
from a2a.types import InternalError, InvalidParamsError, Part, TextPart
from a2a.utils.errors import ServerError
from fastapi import FastAPI
from strands.multiagent.a2a.executor import StrandsA2AExecutor
from strands.multiagent.a2a.server import A2AServer

from strands_a2a_bridge.a2a.mapping import map_text_parts_to_content_blocks
from strands_a2a_bridge.a2a.stub_agent import build_stub_agent
from strands_a2a_bridge.concurrency.user_lock import UserBusyError, UserRequestGuard
from strands_a2a_bridge.config import AppConfig
from strands_a2a_bridge.errors import (
    AgentExecutionFailedError,
    ManagerUnavailableError,
    MissingRequestContextError,
    to_a2a_server_error,
)
from strands_a2a_bridge.http.context import (
    RequestContext as TrustedRequestContext,
    clear_current_request_context,
    get_current_request_context,
    set_current_request_context,
)
from strands_a2a_bridge.manager.contracts import AgentProvider, ManagedAgent
from strands_a2a_bridge.manager.fake import FakeAgentProvider

# 错误消息常量
NON_TEXT_INPUT_ERROR = "Only text input parts are supported in Phase 1"
MISSING_CONTEXT_ERROR = "Missing trusted request context"

# 测试观察用的全局状态
_last_observed_request_context: TrustedRequestContext | None = None
_last_observed_agent_id: str | None = None


def get_last_observed_request_context() -> TrustedRequestContext | None:
    """获取最近一次观察到的请求上下文（仅用于测试）."""
    return _last_observed_request_context


def clear_last_observed_request_context() -> None:
    """清除请求上下文观察状态（仅用于测试）."""
    global _last_observed_request_context
    _last_observed_request_context = None


def get_last_observed_agent_id() -> str | None:
    """获取最近一次观察到的 Agent ID（仅用于测试）."""
    return _last_observed_agent_id


def clear_last_observed_agent_id() -> None:
    """清除 Agent ID 观察状态（仅用于测试）."""
    global _last_observed_agent_id
    _last_observed_agent_id = None


class ManagerBackedStrandsA2AExecutor(StrandsA2AExecutor):
    """基于 AgentProvider 的 A2A 执行器，负责获取或创建用户专属的 Agent."""

    def __init__(
        self,
        provider: AgentProvider,
        bootstrap_agent: ManagedAgent,
        request_guard: UserRequestGuard,
        *,
        enable_a2a_compliant_streaming: bool = False,
    ) -> None:
        super().__init__(
            bootstrap_agent,
            enable_a2a_compliant_streaming=enable_a2a_compliant_streaming,
        )
        self._provider = provider
        self._request_guard = request_guard

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """执行 A2A 请求：验证上下文、获取 Agent 并委托给执行器处理."""
        global _last_observed_agent_id, _last_observed_request_context

        # 从调用上下文或线程本地变量获取受信任的请求上下文
        trusted_context = None
        if context.call_context is not None:
            trusted_context = context.call_context.state.get("trusted_request_context")
        if trusted_context is None:
            trusted_context = get_current_request_context()
        if trusted_context is None:
            raise to_a2a_server_error(
                MissingRequestContextError(MISSING_CONTEXT_ERROR),
                request_id="unknown",
            )

        try:
            _last_observed_request_context = trusted_context
            set_current_request_context(trusted_context)
            async with self._request_guard.claim(trusted_context.user_id):
                try:
                    agent = self._provider.get_or_create_agent(trusted_context.user_id)
                except Exception as exc:
                    raise to_a2a_server_error(
                        ManagerUnavailableError(),
                        request_id=trusted_context.request_id,
                    ) from exc

                _last_observed_agent_id = agent.agent_id
                message = context.message
                if message is None:
                    raise ServerError(error=InvalidParamsError(message="Message is required"))
                if any(not isinstance(part.root, TextPart) for part in message.parts):
                    raise ServerError(error=InvalidParamsError(message=NON_TEXT_INPUT_ERROR))

                local_executor = Phase4TextOnlyStrandsA2AExecutor(
                    agent,
                    enable_a2a_compliant_streaming=self.enable_a2a_compliant_streaming,
                )
                try:
                    await local_executor.execute(context, event_queue)
                except ServerError as exc:
                    if isinstance(exc.error, InternalError):
                        raise to_a2a_server_error(
                            AgentExecutionFailedError(),
                            request_id=trusted_context.request_id,
                        ) from exc
                    raise
                except Exception as exc:
                    raise to_a2a_server_error(
                        AgentExecutionFailedError(),
                        request_id=trusted_context.request_id,
                    ) from exc
        except UserBusyError as exc:
            raise to_a2a_server_error(
                exc,
                request_id=trusted_context.request_id,
            ) from exc
        finally:
            clear_current_request_context()


class Phase4TextOnlyStrandsA2AExecutor(StrandsA2AExecutor):
    """仅支持文本输入的 A2A 执行器."""

    def _convert_a2a_parts_to_content_blocks(self, parts: list[Part]) -> list[dict[str, str]]:
        return map_text_parts_to_content_blocks(parts)


class TrustedRequestContextBuilder(DefaultCallContextBuilder):
    """构建 ServerCallContext，将受信任的请求上下文注入到调用状态中."""

    def build(self, request) -> ServerCallContext:
        call_context = super().build(request)
        trusted_request_context = getattr(request.state, "trusted_request_context", None)
        if trusted_request_context is not None:
            call_context.state["trusted_request_context"] = trusted_request_context
        return call_context


def build_a2a_router(
    config: AppConfig,
    provider: AgentProvider | None = None,
    request_guard: UserRequestGuard | None = None,
) -> FastAPI:
    """构建 A2A FastAPI 子应用，挂载到主应用的 /a2a 路径."""
    resolved_provider = provider or FakeAgentProvider()
    resolved_request_guard = request_guard or UserRequestGuard()
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
        resolved_request_guard,
        enable_a2a_compliant_streaming=True,
    )
    application = A2AFastAPIApplication(
        agent_card=server.public_agent_card,
        http_handler=server.request_handler,
        context_builder=TrustedRequestContextBuilder(),
    )
    return application.build(title=f"{config.service_name} A2A")
