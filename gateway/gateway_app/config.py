from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class GatewayConfig:
    host: str
    port: int
    upstreams: dict[str, str]
    strip_prefixes: set[str]


def _parse_upstreams(raw: str) -> dict[str, str]:
    upstreams: dict[str, str] = {}
    for item in (part.strip() for part in raw.split(",")):
        if not item:
            continue
        if "=" not in item:
            raise ValueError(f"Invalid MCP_UPSTREAMS entry: {item!r}. Expected 'name=url'.")
        name, url = (part.strip() for part in item.split("=", 1))
        if not name or not url:
            raise ValueError(f"Invalid MCP_UPSTREAMS entry: {item!r}. Expected 'name=url'.")
        upstreams[name] = url
    return upstreams


def _parse_csv_set(raw: str) -> set[str]:
    return {item.strip() for item in raw.split(",") if item.strip()}


def load_config() -> GatewayConfig:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "7000"))

    # Example: MCP_UPSTREAMS="markdownify=http://127.0.0.1:7101,nornicdb=http://127.0.0.1:7102"
    upstreams_raw = os.getenv("MCP_UPSTREAMS", "markdownify=http://127.0.0.1:7101")
    upstreams = _parse_upstreams(upstreams_raw)

    # Example: MCP_STRIP_PREFIXES="nornicdb"  (default: none)
    strip_prefixes = _parse_csv_set(os.getenv("MCP_STRIP_PREFIXES", ""))

    return GatewayConfig(host=host, port=port, upstreams=upstreams, strip_prefixes=strip_prefixes)
