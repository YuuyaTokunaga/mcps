from __future__ import annotations

import asyncio
import base64
from pathlib import Path

import pytest

from markdownify_app import server, storage


def _write_csv(session_id: str, content: str) -> str:
    payload = base64.b64encode(content.encode()).decode()
    return storage.write_input_base64(session_id, "data.csv", payload)


def test_convert_to_markdown_generates_outputs(tmp_path: Path) -> None:
    session_id, _ = storage.create_session()
    input_uri = _write_csv(session_id, "a,b\n1,2")

    result = asyncio.run(
        server.convert_to_markdown(
            session_id=session_id,
            input_uri=input_uri,
            include_images=False,
            inline_result=True,
            limits={"max_rows": 10},
        )
    )

    markdown_uri = result["markdown_uri"]
    meta_uri = result["meta_uri"]

    md_path = storage.path_from_session_uri(markdown_uri)
    meta_path = storage.path_from_session_uri(meta_uri)
    assert md_path.exists()
    assert meta_path.exists()
    assert "markdown_inline" in result

    md_text = md_path.read_text(encoding="utf-8")
    assert "a" in md_text

    meta = meta_path.read_text(encoding="utf-8")
    assert "markdown_uri" in meta


def test_convert_to_markdown_rejects_cross_session_input(tmp_path: Path) -> None:
    session_a, _ = storage.create_session()
    session_b, _ = storage.create_session()
    input_uri = _write_csv(session_b, "a,b\n1,2")

    with pytest.raises(storage.StorageError):
        asyncio.run(
            server.convert_to_markdown(
                session_id=session_a,
                input_uri=input_uri,
                include_images=False,
            )
        )
