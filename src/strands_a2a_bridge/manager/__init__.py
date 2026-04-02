"""Agent 管理层：定义 ManagedAgent 接口和提供者实现."""

from strands_a2a_bridge.manager.contracts import AgentProvider, ManagedAgent
from strands_a2a_bridge.manager.fake import FakeAgentProvider, FakeManagedAgent

__all__ = [
    "AgentProvider",
    "ManagedAgent",
    "FakeAgentProvider",
    "FakeManagedAgent",
]
