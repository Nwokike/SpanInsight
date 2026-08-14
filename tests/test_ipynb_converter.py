"""Tests for Jupyter Notebook export converter and File service."""

from __future__ import annotations

import os
import tempfile

import pytest

from services.file_service import (
    FileValidationError,
    suggest_load_code,
    validate_file,
)
from services.ipynb_converter import cells_to_ipynb


class TestIpynbConverter:
    def test_cells_to_ipynb_structure(self):
        cells = [
            {
                "id": "c1",
                "type": "code",
                "source": "import pandas as pd\ndf = pd.DataFrame()",
                "outputs": [],
            },
            {
                "id": "c2",
                "type": "markdown",
                "source": "# Analysis Summary",
                "outputs": [],
            },
        ]
        nb = cells_to_ipynb(cells)

        assert nb["nbformat"] == 4
        assert nb["nbformat_minor"] == 5
        assert len(nb["cells"]) == 2
        assert nb["cells"][0]["cell_type"] == "code"
        assert nb["cells"][1]["cell_type"] == "markdown"
        assert "language_info" in nb["metadata"]


class TestFileService:
    def test_suggest_load_code(self):
        assert "pd.read_csv" in suggest_load_code("data.csv")
        assert "pd.read_excel" in suggest_load_code("sales.xlsx")
        assert "pd.read_json" in suggest_load_code("records.json")
        assert "pd.read_parquet" in suggest_load_code("dataset.parquet")

    def test_validate_file_invalid_ext(self):
        with tempfile.NamedTemporaryFile(suffix=".unknown_ext", delete=False) as f:
            f.write(b"content")
            path = f.name
        try:
            with pytest.raises(FileValidationError):
                validate_file(path)
        finally:
            os.remove(path)

    def test_validate_file_valid_csv(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            f.write(b"col1,col2\n1,2")
            path = f.name
        try:
            validate_file(path)  # Should not raise
        finally:
            os.remove(path)
