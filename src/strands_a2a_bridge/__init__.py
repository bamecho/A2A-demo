"""Strands A2A Bridge：连接 A2A 协议与 Strands 多 Agent 框架的桥接层."""

from strands_a2a_bridge.app import create_app
from strands_a2a_bridge.config import AppConfig


def main() -> None:
    """命令行入口：启动 Uvicorn 服务器."""
    import uvicorn

    config = AppConfig()
    uvicorn.run(create_app(config), host=config.host, port=config.port)
