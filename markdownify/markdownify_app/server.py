import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import storage
from .converters import csv_converter, docx_converter, excel_converter, pdf_converter, pptx_converter

app = FastMCP("markdownify")


def _apply_limits(limits: dict[str, Any] | None) -> dict[str, Any]:
    if not limits:
        return {}
    return {k: v for k, v in limits.items() if isinstance(v, int) and v > 0}


@app.tool()
async def session_create(ttl_seconds: int = storage.DEFAULT_TTL_SECONDS) -> dict[str, str]:
    session_id, root_uri = storage.create_session(ttl_seconds)
    return {"session_id": session_id, "root_uri": root_uri}


@app.tool()
async def session_put_file(session_id: str, filename: str, content_base64: str) -> dict[str, str]:
    input_uri = storage.write_input_base64(session_id, filename, content_base64)
    return {"input_uri": input_uri}


@app.tool()
async def convert_to_markdown(
    session_id: str,
    input_uri: str,
    include_images: bool = False,
    inline_result: bool = False,
    limits: dict[str, Any] | None = None,
) -> dict[str, Any]:
    limits = _apply_limits(limits)
    input_path = storage.path_from_session_uri(input_uri)
    session_root = storage.session_dir(session_id).resolve()
    if not input_path.resolve().is_relative_to(session_root):  # type: ignore[attr-defined]
        raise storage.StorageError("input does not belong to session")

    out_dir = storage.session_dir(session_id) / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    ext = input_path.suffix.lower()
    warnings: list[str] = []
    images: list[Path] = []
    meta: dict[str, Any] = {}
    markdown_body = ""

    if ext == ".csv":
        markdown_body, images, meta, warnings = csv_converter.convert_csv(
            input_path,
            max_rows=limits.get("max_rows", 2000),
            max_cols=limits.get("max_cols", 100),
        )
    elif ext == ".xlsx":
        markdown_body, images, meta, warnings = excel_converter.convert_excel(
            input_path,
            out_dir,
            include_images=include_images,
            max_rows=limits.get("max_rows", 1000),
            max_cols=limits.get("max_cols", 100),
            max_sheets=limits.get("max_sheets", 20),
        )
    elif ext == ".pdf":
        markdown_body, images, meta, warnings = pdf_converter.convert_pdf(
            input_path,
            out_dir,
            include_images=include_images,
            max_pages=limits.get("max_pages", 200),
            render_dpi=limits.get("render_dpi", 200),
        )
    elif ext == ".docx":
        markdown_body, images, meta, warnings = docx_converter.convert_docx(
            input_path,
            max_paragraphs=limits.get("max_paragraphs", 10_000),
            max_tables=limits.get("max_tables", 200),
            max_table_rows=limits.get("max_table_rows", 5_000),
            max_table_cols=limits.get("max_table_cols", 100),
        )
    elif ext == ".pptx":
        markdown_body, images, meta, warnings = pptx_converter.convert_pptx(
            input_path,
            max_slides=limits.get("max_slides", 200),
            max_shapes_per_slide=limits.get("max_shapes_per_slide", 500),
            max_text_lines=limits.get("max_text_lines", 20_000),
            max_table_rows=limits.get("max_table_rows", 5_000),
            max_table_cols=limits.get("max_table_cols", 100),
        )
    else:
        raise storage.StorageError(f"unsupported extension: {ext}")

    result_path = out_dir / "result.md"
    result_path.write_text(markdown_body, encoding="utf-8")

    image_uris = [storage.session_uri_from_path(p) for p in images]
    meta_path = out_dir / "meta.json"
    input_meta = storage.input_info(input_uri)
    meta_payload = {
        "session_id": session_id,
        "input": input_meta,
        "outputs": {
            "markdown_uri": storage.session_uri_from_path(result_path),
            "image_uris": image_uris,
        },
        "limits_applied": limits,
        "converter_meta": meta,
        "warnings": warnings,
    }
    meta_path.write_text(json.dumps(meta_payload, ensure_ascii=True, indent=2), encoding="utf-8")

    response: dict[str, Any] = {
        "markdown_uri": storage.session_uri_from_path(result_path),
        "image_uris": image_uris,
        "meta_uri": storage.session_uri_from_path(meta_path),
    }
    if inline_result and len(markdown_body) < 50_000:
        response["markdown_inline"] = markdown_body
    return response


@app.tool()
async def session_list(session_id: str, prefix: str | None = None) -> dict[str, Any]:
    items = storage.list_session_items(session_id, prefix)
    return {"items": items}


@app.tool()
async def session_delete(session_id: str) -> dict[str, str]:
    storage.delete_session(session_id)
    return {"status": "deleted"}


@app.resource("session://{resource_path}")
async def session_resource(resource_path: str) -> dict[str, Any]:
    uri = f"session://{resource_path}"
    data, mime = storage.read_resource(uri)
    return {
        "uri": storage.normalize_session_uri(uri),
        "mimeType": mime,
        "data": data,
    }


def build_app() -> FastMCP:
    return app
