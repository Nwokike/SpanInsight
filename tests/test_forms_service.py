"""Tests for Forms API client schema creation and validation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.forms_service import create_form


@pytest.mark.asyncio
async def test_create_form_validation():
    invalid_schema = [{"invalid": "field"}]
    res = await create_form("proj_1", "Title", "Desc", invalid_schema)
    assert res is None


@pytest.mark.asyncio
async def test_create_form_valid():
    valid_schema = [
        {"name": "satisfaction", "label": "How satisfied are you?", "type": "rating"},
        {"name": "feedback", "label": "Any comments?", "type": "textarea"},
    ]
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": "form_123",
        "url": "https://forms.spaninsight.app/f/123",
    }

    with patch(
        "services.forms_service.request_with_retry", new_callable=AsyncMock
    ) as mock_req:
        mock_req.return_value = mock_response
        res = await create_form("proj_1", "Survey", "Desc", valid_schema)
        assert res is not None
        assert res["id"] == "form_123"
