import httpx
import pytest

from strands_a2a_bridge.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def async_client(app):
    transport = httpx.ASGITransport(app=app)
    headers = {
        "x-user-id": "fixture-user",
        "x-request-id": "fixture-request-id",
        "x-trace-id": "fixture-trace-id",
    }
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers=headers,
    ) as client:
        yield client
