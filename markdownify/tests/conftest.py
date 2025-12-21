from __future__ import annotations

from pathlib import Path

import pytest

from markdownify_app import storage


@pytest.fixture(autouse=True)
def override_sessions_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate session storage under a temporary directory for each test."""
    root = tmp_path / "sessions"
    root.mkdir()
    monkeypatch.setattr(storage, "_sessions_root", lambda: root)
    return root
