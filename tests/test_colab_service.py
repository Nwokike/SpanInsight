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
