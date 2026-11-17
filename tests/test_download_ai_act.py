"""Tests for scripts/download_ai_act.py (no network: `httpx2.get` is faked)."""

import importlib.util
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx2
import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "download_ai_act.py"

GetFake = Callable[..., httpx2.Response]


@pytest.fixture(scope="module")
def script() -> ModuleType:
    """Load the non-package script as a module."""
    spec = importlib.util.spec_from_file_location("download_ai_act", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_get(status_code: int, body: bytes) -> GetFake:
    """Build a fake `httpx2.get` that returns a response with the given status and body."""

    def fake_get(url: str, *args: Any, **kwargs: Any) -> httpx2.Response:
        request = httpx2.Request("GET", url)
        return httpx2.Response(status_code, content=body, request=request)

    return fake_get


def fail_get(url: str, *args: Any, **kwargs: Any) -> httpx2.Response:
    """Fake `httpx2.get` that must never be called."""
    raise AssertionError(f"unexpected request to {url}")


def test_fetch_html_returns_body_when_marker_present(
    script: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = "<html>Article 5 Prohibited AI practices</html>".encode()
    monkeypatch.setattr(script.httpx2, "get", make_get(200, body))

    result = script.fetch_html()

    assert result == body


def test_fetch_html_rejects_empty_202_challenge(
    script: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(script.httpx2, "get", make_get(202, b""))

    with pytest.raises(ValueError, match="status 202"):
        script.fetch_html()


def test_fetch_html_rejects_body_with_normal_space_marker(
    script: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = b"<html>Article 5 Prohibited AI practices</html>"  # ASCII space, not NBSP
    monkeypatch.setattr(script.httpx2, "get", make_get(200, body))

    with pytest.raises(ValueError, match="marker"):
        script.fetch_html()


def test_fetch_html_raises_http_status_error_for_500(
    script: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(script.httpx2, "get", make_get(500, b"boom"))

    with pytest.raises(httpx2.HTTPStatusError):
        script.fetch_html()


def test_download_writes_content_and_creates_parent_dir(
    script: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    body = "<html>Article 5</html>".encode()
    monkeypatch.setattr(script.httpx2, "get", make_get(200, body))
    target = tmp_path / "raw" / "x.html"

    result = script.download(target=target)

    assert result == target
    assert target.read_bytes() == body


def test_download_skips_request_when_target_exists(
    script: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "x.html"
    target.write_bytes(b"original")
    monkeypatch.setattr(script.httpx2, "get", fail_get)

    result = script.download(target=target)

    assert result == target
    assert target.read_bytes() == b"original"
