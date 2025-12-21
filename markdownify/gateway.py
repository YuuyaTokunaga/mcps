import argparse
import os

import uvicorn
from fastapi import FastAPI

from markdownify_app.server import build_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Markdownify MCP gateway")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 7000)))
    parser.add_argument("--path", default=os.getenv("MCP_PATH", "/markdownify"))
    parser.add_argument(
        "--transport",
        choices=["http", "streamable-http", "stdio"],
        default=os.getenv("MCP_TRANSPORT", "streamable-http"),
    )
    args = parser.parse_args()

    transport = "streamable-http" if args.transport == "http" else args.transport

    app = build_app()
    if transport == "stdio":
        app.run(transport="stdio")
        return

    # HTTP系（streamable-http）: FastAPIでヘルスチェックを追加し、MCPをマウント
    app.settings.host = args.host
    app.settings.port = args.port
    app.settings.streamable_http_path = "/"  # 内部アプリのルートを mount path に直結
    app.settings.mount_path = "/"

    streamable_http_app = app.streamable_http_app()
    session_manager = app._session_manager  # Uses FastMCP's internally created manager

    async def lifespan(_: FastAPI):
        if session_manager is None:
            raise RuntimeError("Streamable HTTP session manager is not initialized")
        async with session_manager.run():
            yield

    http_app = FastAPI(lifespan=lifespan)

    @http_app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    http_app.mount(args.path, streamable_http_app)

    uvicorn.run(http_app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
