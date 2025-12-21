from __future__ import annotations

import argparse
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from starlette.responses import JSONResponse

from gateway_app.config import GatewayConfig, load_config
from gateway_app.proxy import proxy_request


def create_app(config: GatewayConfig) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        timeout = httpx.Timeout(connect=2.0, read=None, write=30.0, pool=5.0)
        limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
            app.state.http_client = client
            yield

    app = FastAPI(lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/{service}/health")
    async def service_health(service: str, request: Request) -> JSONResponse:
        upstream_base_url = config.upstreams.get(service)
        if upstream_base_url is None:
            raise HTTPException(status_code=404, detail=f"Unknown service: {service}")

        client: httpx.AsyncClient = request.app.state.http_client
        try:
            upstream_url = httpx.URL(upstream_base_url).copy_with(path="/health")
            upstream_response = await client.get(upstream_url)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            raise HTTPException(status_code=502, detail=f"Upstream '{service}' is unavailable: {exc!s}") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Upstream '{service}' error: {exc!s}") from exc

        return JSONResponse(content=upstream_response.json(), status_code=upstream_response.status_code)

    @app.api_route(
        "/{service}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    )
    @app.api_route(
        "/{service}/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    )
    async def route_to_upstream(service: str, request: Request, path: str = ""):
        upstream_base_url = config.upstreams.get(service)
        if upstream_base_url is None:
            raise HTTPException(status_code=404, detail=f"Unknown service: {service}")

        client: httpx.AsyncClient = request.app.state.http_client
        return await proxy_request(
            request=request,
            client=client,
            upstream_base_url=upstream_base_url,
            service=service,
            path=path,
            strip_prefix=service in config.strip_prefixes,
        )

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="mcps reverse proxy gateway")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    config = load_config()
    if args.host is not None:
        config = GatewayConfig(
            host=args.host,
            port=config.port,
            upstreams=config.upstreams,
            strip_prefixes=config.strip_prefixes,
        )
    if args.port is not None:
        config = GatewayConfig(
            host=config.host,
            port=args.port,
            upstreams=config.upstreams,
            strip_prefixes=config.strip_prefixes,
        )

    uvicorn.run(create_app(config), host=config.host, port=config.port)


if __name__ == "__main__":
    main()
