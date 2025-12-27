import base64
import hashlib
import json
import mimetypes
import re
import shutil
import time
import uuid
from pathlib import Path

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".pdf", ".docx", ".pptx"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
DEFAULT_TTL_SECONDS = 24 * 60 * 60

_SESSION_SCHEME = "session"


class StorageError(Exception):
    pass


def _sessions_root() -> Path:
    return Path(__file__).resolve().parent.parent / "sessions"


def _session_dir(session_id: str) -> Path:
    return _sessions_root() / session_id


def session_dir(session_id: str) -> Path:
    return _session_dir(session_id)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def generate_session_id() -> str:
    return uuid.uuid4().hex


def _sanitize_filename(filename: str) -> str:
    if not filename:
        raise StorageError("filename is required")
    cleaned = Path(filename).name
    if cleaned in {"", ".", ".."}:
        raise StorageError("invalid filename")
    if re.search(r"[\\\n\r\x00]", cleaned):
        raise StorageError("filename contains invalid characters")
    return cleaned


def _validate_extension(filename: str) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise StorageError(f"extension not allowed: {ext}")


def _session_uri_from_path(path: Path) -> str:
    rel = path.relative_to(_sessions_root())
    return f"{_SESSION_SCHEME}://{rel.as_posix()}"


def session_uri_from_path(path: Path) -> str:
    return _session_uri_from_path(path)


def _path_from_session_uri(uri: str) -> Path:
    if not uri.startswith(f"{_SESSION_SCHEME}://"):
        raise StorageError("uri must start with session://")
    rel = uri[len(f"{_SESSION_SCHEME}://") :]
    rel_path = Path(rel)
    if rel_path.is_absolute() or ".." in rel_path.parts:
        raise StorageError("invalid session uri")
    resolved = (_sessions_root() / rel_path).resolve()
    if _sessions_root() not in resolved.parents and resolved != _sessions_root():
        raise StorageError("uri escapes session root")
    return resolved


def path_from_session_uri(uri: str) -> Path:
    return _path_from_session_uri(uri)


def create_session(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> tuple[str, str]:
    session_id = generate_session_id()
    root = _session_dir(session_id)
    _ensure_dir(root / "in")
    _ensure_dir(root / "out")
    meta = {
        "session_id": session_id,
        "created_at": int(time.time()),
        "ttl_seconds": ttl_seconds,
    }
    (root / "session.json").write_text(json.dumps(meta, ensure_ascii=True, indent=2), encoding="utf-8")
    return session_id, f"{_SESSION_SCHEME}://{session_id}/"


def write_input_base64(session_id: str, filename: str, content_base64: str) -> str:
    safe_name = _sanitize_filename(filename)
    _validate_extension(safe_name)
    try:
        data = base64.b64decode(content_base64, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise StorageError("failed to decode base64") from exc
    if len(data) > MAX_UPLOAD_BYTES:
        raise StorageError("file too large")
    session_root = _session_dir(session_id)
    if not session_root.exists():
        raise StorageError("session not found")
    dest = session_root / "in" / safe_name
    _ensure_dir(dest.parent)
    dest.write_bytes(data)
    return _session_uri_from_path(dest)


def read_resource(uri: str) -> tuple[bytes, str | None]:
    path = _path_from_session_uri(uri)
    if not path.exists() or not path.is_file():
        raise StorageError("resource not found")
    data = path.read_bytes()
    mime, _ = mimetypes.guess_type(path.name)
    return data, mime


def list_session_items(session_id: str, prefix: str | None = None) -> list[dict[str, object]]:
    root = _session_dir(session_id)
    if not root.exists():
        raise StorageError("session not found")
    items: list[dict[str, object]] = []
    base = root
    if prefix:
        safe_prefix = Path(prefix)
        if safe_prefix.is_absolute() or ".." in safe_prefix.parts:
            raise StorageError("invalid prefix")
        base = root / safe_prefix
    if not base.exists():
        return []
    for path in base.rglob("*"):
        if path.is_file():
            items.append(
                {
                    "uri": _session_uri_from_path(path),
                    "mimeType": mimetypes.guess_type(path.name)[0],
                    "sizeBytes": path.stat().st_size,
                }
            )
    return items


def delete_session(session_id: str) -> None:
    root = _session_dir(session_id)
    if root.exists():
        shutil.rmtree(root)


def normalize_session_uri(uri: str) -> str:
    path = _path_from_session_uri(uri)
    return _session_uri_from_path(path)


def input_info(uri: str) -> dict[str, object]:
    path = _path_from_session_uri(uri)
    if not path.exists():
        raise StorageError("resource not found")
    data = path.read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()
    ext = Path(path.name).suffix.lower()
    return {
        "original_filename": path.name,
        "detected_type": ext.lstrip("."),
        "size_bytes": len(data),
        "sha256": sha256,
    }
