"""Shared HTTP client - connection-pooled, retry-enabled.

Eliminates per-request ``httpx.AsyncClient()`` instantiation across
the codebase (ai_service, forms_service, uuid_service, etc.).

Benefits:
- TCP + TLS connection reuse → ~200-400ms saved per request
- Automatic retry with exponential backoff for mobile networks
- Single lifecycle - no socket leak risk
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from core.constants import APP_CLIENT_ID, USER_AGENT

logger = logging.getLogger(__name__)

# Shared headers for every request (NO Content-Type - httpx sets it per request)
COMMON_HEADERS = {
    "X-App-Secret": APP_CLIENT_ID,
    "User-Agent": USER_AGENT,
}

# Module-level shared client - initialized lazily
_client: httpx.AsyncClient | None = None
_is_shutting_down: bool = False


def get_client() -> httpx.AsyncClient:
    """Return the shared async HTTP client (lazy-init, connection-pooled)."""
    global _client
    if _is_shutting_down:
        raise httpx.HTTPError("Client is shutting down")

    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if (
        _client is None
        or _client.is_closed
        or (
            getattr(_client, "_active_loop", None) is not None
            and _client._active_loop is not current_loop
        )
    ):
        _client = httpx.AsyncClient(
            headers=COMMON_HEADERS,
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
                keepalive_expiry=30,
            ),
            http2=False,
        )
        _client._active_loop = current_loop
    return _client


async def close_client() -> None:
    """Gracefully close the shared client (call on app shutdown)."""
    global _client, _is_shutting_down
    _is_shutting_down = True
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def request_with_retry(
    method: str,
    url: str,
    *,
    max_retries: int = 2,
    retry_statuses: set[int] | None = None,
    **kwargs,
) -> httpx.Response:
    """Make an HTTP request with exponential backoff retry.

    Retries on:
    - Network errors (ConnectError, TimeoutException)
    - Specified HTTP status codes (default: 502, 503, 504)

    Args:
        method: HTTP method (GET, POST, etc.)
        url: Full URL to request
        max_retries: Maximum retry attempts (default 2 = 3 total tries)
        retry_statuses: HTTP status codes that trigger a retry
        **kwargs: Passed to httpx.AsyncClient.request()

    Returns:
        httpx.Response
    """
    if retry_statuses is None:
        retry_statuses = {502, 503, 504}

    client = get_client()
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            resp = await client.request(method, url, **kwargs)
            if resp.status_code not in retry_statuses or attempt == max_retries:
                return resp
            logger.warning(
                "Retry %d/%d for %s %s (HTTP %d)",
                attempt + 1,
                max_retries,
                method,
                url,
                resp.status_code,
            )
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            last_exc = e
            if attempt == max_retries:
                raise
            logger.warning(
                "Retry %d/%d for %s %s (%s: %s)",
                attempt + 1,
                max_retries,
                method,
                url,
                type(e).__name__,
                e,
            )

        # Exponential backoff: 0.5s, 1s
        await asyncio.sleep(0.5 * (2**attempt))

    # Should not reach here, but just in case
    if last_exc:
        raise last_exc
    raise httpx.HTTPError(f"Request failed after {max_retries + 1} attempts")
