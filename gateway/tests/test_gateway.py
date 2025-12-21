import httpx
import pytest

from gateway_app.config import GatewayConfig
from gateway_app.server import create_app


@pytest.mark.anyio
async def test_returns_502_when_upstream_unavailable() -> None:
    # Use a port that is very likely closed.
    config = GatewayConfig(
        host="127.0.0.1",
        port=7000,
        upstreams={"markdownify": "http://127.0.0.1:1"},
        strip_prefixes=set(),
    )
    app = create_app(config)

    async with httpx.AsyncClient() as upstream_client:
        app.state.http_client = upstream_client

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/markdownify/health")

    assert res.status_code == 502
