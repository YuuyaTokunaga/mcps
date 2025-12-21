from __future__ import annotations

import base64
from pathlib import Path

import pytest

from markdownify_app import storage


def test_create_session_and_write_input(tmp_path: Path) -> None:
    session_id, root_uri = storage.create_session()
    assert root_uri.startswith("session://")

    payload = base64.b64encode(b"hello csv").decode()
    input_uri = storage.write_input_base64(session_id, "sample.csv", payload)
    input_path = storage.path_from_session_uri(input_uri)
    assert input_path.exists()
    assert input_path.read_text() == "hello csv"

    info = storage.input_info(input_uri)
    assert info["original_filename"] == "sample.csv"
    assert info["detected_type"] == "csv"
    assert info["size_bytes"] == len(b"hello csv")


def test_rejects_invalid_extension() -> None:
    session_id, _ = storage.create_session()
    payload = base64.b64encode(b"data").decode()
    with pytest.raises(storage.StorageError):
        storage.write_input_base64(session_id, "evil.exe", payload)


def test_session_uri_escape_is_blocked() -> None:
    with pytest.raises(storage.StorageError):
        storage.path_from_session_uri("session://../etc/passwd")


def test_list_and_read_resource(tmp_path: Path) -> None:
    session_id, _ = storage.create_session()
    session_root = storage.session_dir(session_id)
    out_file = session_root / "out" / "result.md"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("content", encoding="utf-8")

    items = storage.list_session_items(session_id)
    assert any(item["uri"].endswith("result.md") for item in items)

    data, mime = storage.read_resource(storage.session_uri_from_path(out_file))
    assert data == b"content"
    assert mime == "text/markdown"


def test_delete_session_removes_directory() -> None:
    session_id, _ = storage.create_session()
    root = storage.session_dir(session_id)
    assert root.exists()
    storage.delete_session(session_id)
    assert not root.exists()
