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


@pytest.mark.asyncio
async def test_chunked_upload_multi_chunk(tmp_path):
    from unittest.mock import MagicMock

    from services.colab.files_ops import upload_impl

    # Create a 5MB test file (which requires 3 chunks with 2MB chunk size)
    test_file = tmp_path / "large_dataset.bin"
    file_bytes = b"X" * (5 * 1024 * 1024)
    test_file.write_bytes(file_bytes)

    mock_service = MagicMock()
    mock_service._ensure_online = AsyncMock()

    mock_session = MagicMock()
    mock_session.url = "https://colab.research.google.com/test"
    mock_session.token = "test_token"

    mock_state = MagicMock()
    mock_state.store.get.return_value = mock_session

    progress_ticks = []

    def cb(cur, tot):
        progress_ticks.append((cur, tot))

    with (
        patch("colab_cli.common.State", return_value=mock_state),
        patch("requests.put") as mock_put,
    ):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_put.return_value = mock_resp

        ok = await upload_impl(
            mock_service,
            "sess1",
            str(test_file),
            "/content/large_dataset.bin",
            progress_callback=cb,
        )
        assert ok is True
        # 5MB with 2MB chunks -> 3 chunks sent (2MB, 2MB, 1MB)
        assert mock_put.call_count == 3
        # Check last chunk had chunk = -1
        last_call_json = mock_put.call_args_list[-1].kwargs.get("json")
        assert last_call_json["chunk"] == -1
        assert len(progress_ticks) > 0
        assert progress_ticks[-1][0] == len(file_bytes)
