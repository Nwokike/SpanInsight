"""Tests for AI analysis and report generation services."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.ai import analysis as ai_service


@pytest.mark.asyncio
async def test_ai_generate_code():
    schema = {"columns": ["age", "salary"], "shape": [100, 2]}
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": "```python\nimport pandas as pd\ndf['salary'].mean()\n```"
                }
            }
        ]
    }
    with patch(
        "services.ai.analysis.code_gen.call_gateway", new_callable=AsyncMock
    ) as mock_gateway:
        mock_gateway.return_value = mock_response
        code = await ai_service.generate_code("Calculate mean salary", schema)
        assert "mean()" in code


@pytest.mark.asyncio
async def test_ai_error_correction():
    schema = {"columns": ["A", "B"]}
    mock_response = {
        "choices": [{"message": {"content": "```python\ndf['A'].fillna(0)\n```"}}]
    }
    with patch(
        "services.ai.analysis.code_gen.call_gateway", new_callable=AsyncMock
    ) as mock_gateway:
        mock_gateway.return_value = mock_response
        corrected = await ai_service.generate_corrected_code(
            prompt="Clean missing values",
            bad_code="df['A'].invalid_op()",
            error_message="AttributeError: 'Series' object has no attribute 'invalid_op'",
            schema_json=schema,
        )
        assert "fillna(0)" in corrected
