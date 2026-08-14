"""Tests for Core State, Utilities, and Tokens."""

from __future__ import annotations

from unittest.mock import MagicMock

from core.state import AppState
from core.utils import figure_to_png_bytes, parse_version, sanitize_numpy


class TestAppState:
    def test_initial_state(self):
        state = AppState()
        assert state.current_tab == 0
        assert state.colab_connected is False
        assert state.is_online is True
        assert state.notebook_cells == []
        assert state.active_session_name == ""

    def test_cell_management(self):
        state = AppState()
        cell1 = state.add_cell("code", "import pandas as pd")
        assert len(state.notebook_cells) == 1
        assert cell1["type"] == "code"
        assert cell1["source"] == "import pandas as pd"
        assert "id" in cell1

        cell2 = state.add_cell("markdown", "# Title")
        assert len(state.notebook_cells) == 2
        assert cell2["type"] == "markdown"

        state.clear_notebook()
        assert len(state.notebook_cells) == 0

    def test_session_state(self):
        state = AppState()
        state.active_session_name = "test_session_123"
        state.session_hardware = "T4 GPU"
        state.colab_connected = True

        assert state.active_session_name == "test_session_123"
        assert state.session_hardware == "T4 GPU"
        assert state.colab_connected is True


class TestUtils:
    def test_parse_version(self):
        assert parse_version("1.2.3") == (1, 2, 3)
        assert parse_version("2.0.0") > parse_version("1.9.9")
        assert parse_version("invalid") == (0, 0, 0)
        assert parse_version("") == (0, 0, 0)
        assert parse_version(None) == (0, 0, 0)
        assert parse_version("  1.2.3  ") == (1, 2, 3)

    def test_sanitize_numpy(self):
        assert sanitize_numpy(float("nan")) is None
        assert sanitize_numpy(float("inf")) is None
        assert sanitize_numpy(float("-inf")) is None
        assert sanitize_numpy(42) == 42
        assert sanitize_numpy("text") == "text"
        assert sanitize_numpy([1.0, float("nan"), 3.0]) == [1.0, None, 3.0]
        assert sanitize_numpy({"a": float("inf"), "b": 2}) == {"a": None, "b": 2}
        assert sanitize_numpy(None) is None
        assert sanitize_numpy(True) is True

    def test_figure_to_png_bytes(self):
        mock_fig = MagicMock()

        def _mock_savefig(buf, **kwargs):
            buf.write(b"\x89PNG\r\n\x1a\n")

        mock_fig.savefig.side_effect = _mock_savefig
        data = figure_to_png_bytes(mock_fig)
        assert isinstance(data, bytes)
        assert data.startswith(b"\x89PNG")
