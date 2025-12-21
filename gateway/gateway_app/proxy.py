from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Final

import httpx
from fastapi import HTTPException, Request
from starlette.responses import StreamingResponse

_HOP_BY_HOP_HEADERS: Final[set[str]] = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def _filtered_request_headers(request: Request) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in request.headers.items():
        key_lower = key.lower()
        if key_lower in _HOP_BY_HOP_HEADERS:
            continue
        if key_lower == "host":
            continue
        headers[key] = value

    headers.setdefault("x-forwarded-proto", request.url.scheme)
    headers.setdefault("x-forwarded-host", request.headers.get("host", ""))
    headers.setdefault("x-forwarded-for", request.client.host if request.client else "")

    return headers


def _filtered_response_headers(headers: httpx.Headers) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if key_lower in _HOP_BY_HOP_HEADERS:
            continue
        if key_lower == "content-length":
            # Streaming response: let the server/framework handle it.
            continue
        out[key] = value
    return out


def _build_upstream_path(service: str, path: str, strip_prefix: bool) -> str:
    path = path or ""
    if strip_prefix:
        suffix = path.lstrip("/")
        return f"/{suffix}" if suffix else "/"

    suffix = path.lstrip("/")
    return f"/{service}/{suffix}" if suffix else f"/{service}"


async def proxy_request(
    *,
    request: Request,
    client: httpx.AsyncClient,
    upstream_base_url: str,
    service: str,
    path: str,
    strip_prefix: bool,
) -> StreamingResponse:
    upstream_path = _build_upstream_path(service, path, strip_prefix)

    upstream_url = httpx.URL(upstream_base_url).copy_with(
        path=upstream_path,
        query=request.url.query.encode("utf-8"),
    )

    try:
        upstream_response = await client.send(
            client.build_request(
                method=request.method,
                url=upstream_url,
                headers=_filtered_request_headers(request),
                content=request.stream(),
            ),
            stream=True,
        )
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise HTTPException(status_code=502, detail=f"Upstream '{service}' is unavailable: {exc!s}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream '{service}' error: {exc!s}") from exc

    async def body_iter() -> AsyncIterator[bytes]:
        try:
            async for chunk in upstream_response.aiter_raw():
                yield chunk
        finally:
            await upstream_response.aclose()

    return StreamingResponse(
        body_iter(),
        status_code=upstream_response.status_code,
        headers=_filtered_response_headers(upstream_response.headers),
        media_type=upstream_response.headers.get("content-type"),
        background=None,
    )
