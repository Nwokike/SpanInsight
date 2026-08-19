"""Tests for Colab Service: Auth, sessions, and code execution flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.colab import ColabService


@pytest.mark.asyncio
async def test_colab_service_init():
    colab = ColabService()
    assert colab.is_available is False
    assert colab.default_stdin_hook is None


@pytest.mark.asyncio
async def test_colab_check_auth():
    colab = ColabService()
    with patch(
        "services.colab.auth.check_auth_impl", new_callable=AsyncMock
    ) as mock_auth:
        mock_auth.return_value = {"authenticated": True, "email": "user@example.com"}
        res = await colab.check_auth()
        assert res["authenticated"] is True
        assert res["email"] == "user@example.com"


def test_progress_reader():
    from services.colab.files_ops import ProgressReader

    progress_events = []
    data = b"Hello, World! Testing ProgressReader byte stream."

    def cb(sent, total):
        progress_events.append((sent, total))

    reader = ProgressReader(data, callback=cb)
    assert len(reader) == len(data)

    chunk1 = reader.read(10)
    assert chunk1 == data[:10]
    chunk2 = reader.read()
    assert chunk2 == data[10:]
    assert reader.read() == b""

    assert len(progress_events) >= 2
    assert progress_events[-1] == (len(data), len(data))


@pytest.mark.asyncio
async def test_colab_upload_forwards_progress():
    colab = ColabService()
    with patch(
        "services.colab.files_ops.upload_impl", new_callable=AsyncMock
    ) as mock_upload:
        mock_upload.return_value = True

        called_events = []

        def my_cb(cur, tot):
            called_events.append((cur, tot))

        ok = await colab.upload(
            "dummy.csv", "/content/dummy.csv", "test_sess", progress_callback=my_cb
        )
        assert ok is True
        mock_upload.assert_called_once_with(
            colab,
            "test_sess",
            "dummy.csv",
            "/content/dummy.csv",
            "oauth2",
            my_cb,
        )
