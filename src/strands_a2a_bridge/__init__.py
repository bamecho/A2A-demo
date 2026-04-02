from strands_a2a_bridge.app import create_app
from strands_a2a_bridge.config import AppConfig


def main() -> None:
    import uvicorn

    config = AppConfig()
    uvicorn.run(create_app(config), host=config.host, port=config.port)
