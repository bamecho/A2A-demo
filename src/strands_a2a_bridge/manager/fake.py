"""当前默认的测试用 AgentProvider/Agent 内存实现."""

from __future__ import annotations

import logging

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FakeManagedAgent:
    """测试用执行 agent，记录对话轮次和历史输入."""
    user_id: str
    agent_id: str
    name: str = "phase3-fake-agent"
    description: str = "Phase 3 fake managed agent"
    turn_count: int = 0
    last_user_input: str | None = None

    async def stream_async(
        self,
        content_blocks: Sequence[Any],
        *,
        invocation_state: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        """流式返回当前轮次、输入内容和上一轮输入（用于测试验证）."""
        _ = invocation_state
        current_input = _extract_text_input(content_blocks)
        previous_input = self.last_user_input or "<none>"
        next_turn = self.turn_count + 1
        logger.info(
            "fake-agent stream start user_id=%s agent_id=%s turn=%s input=%r previous=%r",
            self.user_id,
            self.agent_id,
            next_turn,
            current_input,
            previous_input,
        )
        self.turn_count = next_turn
        self.last_user_input = current_input

        for chunk in (
            f"turn {self.turn_count}",
            f"input {current_input}",
            f"previous {previous_input}",
        ):
            logger.info(
                "fake-agent stream chunk user_id=%s agent_id=%s turn=%s chunk=%r",
                self.user_id,
                self.agent_id,
                self.turn_count,
                chunk,
            )
            yield {"data": chunk}
        logger.info(
            "fake-agent stream finish user_id=%s agent_id=%s turn=%s result=%r",
            self.user_id,
            self.agent_id,
            self.turn_count,
            f"turn {self.turn_count}: {current_input}",
        )
        yield {"result": f"turn {self.turn_count}: {current_input}"}


class FakeAgentProvider:
    """内存中的测试 provider，按 user_id 复用或创建执行 agent."""

    def __init__(self) -> None:
        self._agents_by_user_id: dict[str, FakeManagedAgent] = {}
        self._next_agent_index = 1

    def get_or_create_agent(self, user_id: str) -> FakeManagedAgent:
        """获取或创建与用户 ID 绑定的 FakeManagedAgent.
        
        第一个创建的 Agent 使用固定 ID "stub-agent"，后续按序号命名.
        """
        cached = self._agents_by_user_id.get(user_id)
        if cached is not None:
            logger.info(
                "fake-provider resolved agent user_id=%s agent_id=%s created=False",
                user_id,
                cached.agent_id,
            )
            return cached

        # 第一个 Agent 使用固定 ID，方便测试识别
        if not self._agents_by_user_id:
            agent_id = "stub-agent"
        else:
            agent_id = f"fake-agent-{self._next_agent_index}"
            self._next_agent_index += 1

        agent = FakeManagedAgent(user_id=user_id, agent_id=agent_id)
        self._agents_by_user_id[user_id] = agent
        logger.info(
            "fake-provider resolved agent user_id=%s agent_id=%s created=True",
            user_id,
            agent.agent_id,
        )
        return agent


def _extract_text_input(content_blocks: Sequence[Any]) -> str:
    """从 content blocks 中提取文本内容."""
    text_segments: list[str] = []
    for block in content_blocks:
        if isinstance(block, dict):
            text_value = block.get("text")
            if isinstance(text_value, str) and text_value:
                text_segments.append(text_value)
    return "\n".join(text_segments)
