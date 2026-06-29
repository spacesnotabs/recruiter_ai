"""Tests for HTTP retrieval and cleaned page-text helpers."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from tools.web_scraping import HtmlFetchError, fetch_html, html_to_clean_text


class _FakeResponse:
    """Small response double supporting the fields used by ``fetch_html``."""

    def __init__(self, text: str, content_type: str = "text/html", url: str = "https://final.test") -> None:
        self.text = text
        self.headers = {"content-type": content_type}
        self.url = url

    def raise_for_status(self) -> None:
        """Model a successful HTTP response."""


class _FakeAsyncClient:
    """Async HTTP client double with optional request failure."""

    def __init__(self, response: _FakeResponse | None = None, error: Exception | None = None, **kwargs) -> None:
        self.response = response
        self.error = error
        self.kwargs = kwargs

    async def __aenter__(self):
        """Return the client for an async context manager."""
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        """Complete async context-manager cleanup."""

    async def get(self, url: str, *, headers: dict[str, str]) -> _FakeResponse:
        """Return the configured response or raise the configured failure."""
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def test_fetch_html_returns_html_and_follows_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTML response bodies are returned after the client follows redirects."""
    created_clients: list[_FakeAsyncClient] = []

    def create_client(**kwargs) -> _FakeAsyncClient:
        client = _FakeAsyncClient(_FakeResponse("<h1>Role</h1>", url="https://final.test/job"), **kwargs)
        created_clients.append(client)
        return client

    monkeypatch.setattr("tools.web_scraping.httpx.AsyncClient", create_client)

    assert asyncio.run(fetch_html("https://start.test/job")) == "<h1>Role</h1>"
    assert created_clients[0].kwargs["follow_redirects"] is True


def test_fetch_html_rejects_non_html_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """JSON responses are not accepted as job-posting pages."""
    monkeypatch.setattr(
        "tools.web_scraping.httpx.AsyncClient",
        lambda **kwargs: _FakeAsyncClient(_FakeResponse('{"job": "data"}', "application/json"), **kwargs),
    )

    with pytest.raises(HtmlFetchError, match="did not return HTML"):
        asyncio.run(fetch_html("https://example.test/job"))


def test_fetch_html_wraps_http_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """Network errors are exposed through the narrow fetch error type."""
    monkeypatch.setattr(
        "tools.web_scraping.httpx.AsyncClient",
        lambda **kwargs: _FakeAsyncClient(error=httpx.ConnectError("offline"), **kwargs),
    )

    with pytest.raises(HtmlFetchError, match="Could not fetch"):
        asyncio.run(fetch_html("https://example.test/job"))


def test_html_to_clean_text_removes_non_content_elements() -> None:
    """Page chrome and executable content are excluded from cleaned model input."""
    cleaned = html_to_clean_text(
        "<header>Navigation</header><script>alert(1)</script><main><p>Build APIs.</p></main>"
    )

    assert cleaned == "Build APIs."
