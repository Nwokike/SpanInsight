"""Regression tests for the dataset import pipeline.

These pin the REAL colab_cli 0.6.0 output contract: ``exec_code`` returns a
LIST of jupyter-style output dicts (not a ``{"outputs": [...]}`` envelope).
The old code failed silently against this contract — no description, no
suggestions, no overview card — so every shape here is asserted explicitly.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from services.colab.introspection import (
    build_schema_extraction_code,
    parse_schema_from_outputs,
)
from services.colab.output_utils import (
    extract_error_text,
    extract_marker_payload,
    extract_text,
    normalize_outputs,
    parse_marker_json,
)
from services.file_service import suggest_load_code

# ── Output contract (colab_cli returns a list) ────────────────────


def test_normalize_outputs_list_passthrough():
    outputs = [{"output_type": "stream", "text": "hi"}]
    assert normalize_outputs(outputs) == outputs


def test_normalize_outputs_dict_envelope_tolerated():
    outputs = [{"output_type": "stream", "text": "hi"}]
    assert normalize_outputs({"outputs": outputs}) == outputs


def test_normalize_outputs_none_and_tuple():
    assert normalize_outputs(None) == []
    assert normalize_outputs(("a",)) == ["a"]


def test_extract_text_stream_and_result():
    outputs = [
        {"output_type": "stream", "name": "stdout", "text": "Loaded 10 rows"},
        {"output_type": "execute_result", "data": {"text/plain": "DataFrame"}},
    ]
    assert extract_text(outputs) == "Loaded 10 rowsDataFrame"


def test_extract_text_list_shaped_text():
    # jupyter sometimes delivers text as a list of string fragments
    outputs = [{"output_type": "stream", "text": ["a", "b"]}]
    assert extract_text(outputs) == "ab"


def test_extract_error_text():
    outputs = [
        {
            "output_type": "error",
            "ename": "NameError",
            "evalue": "name 'df' is not defined",
            "traceback": [
                "Traceback (most recent call last)",
                "NameError: name 'df' is not defined",
            ],
        }
    ]
    err = extract_error_text(outputs)
    assert err is not None
    assert "NameError" in err and "df" in err


def test_extract_error_text_none_when_clean():
    assert extract_error_text([{"output_type": "stream", "text": "ok"}]) is None


# ── Marker parsing ────────────────────────────────────────────────


def test_extract_marker_payload():
    raw = 'noise\n__SPANINSIGHT_SCHEMA_START__\n{"a": 1}\n__SPANINSIGHT_SCHEMA_END__\nmore'
    assert extract_marker_payload(raw, "SPANINSIGHT_SCHEMA") == '{"a": 1}'


def test_extract_marker_payload_missing():
    assert extract_marker_payload("no markers here", "SPANINSIGHT_SCHEMA") is None


def test_parse_marker_json_valid():
    outputs = [
        {"output_type": "stream", "text": "__SPANINSIGHT_SCHEMA_START__"},
        {"output_type": "stream", "text": json.dumps({"kind": "dataframe"})},
        {"output_type": "stream", "text": "__SPANINSIGHT_SCHEMA_END__"},
    ]
    payload, err = parse_marker_json(outputs, "SPANINSIGHT_SCHEMA")
    assert err is None
    assert payload == {"kind": "dataframe"}


def test_parse_marker_json_malformed():
    outputs = [
        {
            "output_type": "stream",
            "text": "__SPANINSIGHT_SCHEMA_START__not-json__SPANINSIGHT_SCHEMA_END__",
        }
    ]
    payload, err = parse_marker_json(outputs, "SPANINSIGHT_SCHEMA")
    assert payload is None
    assert err and "Malformed" in err


# ── Schema introspection ──────────────────────────────────────────


def test_schema_code_always_prints_markers_and_never_swallows():
    code = build_schema_extraction_code()
    assert "__SPANINSIGHT_SCHEMA_START__" in code
    assert "__SPANINSIGHT_SCHEMA_END__" in code
    # The old killer: a bare remote `except Exception: pass` that hid every failure
    assert "except Exception:\n  pass" not in code.replace("\r", "")
    assert "except Exception:\n    pass" not in code.replace("\r", "")


def test_parse_schema_success():
    schema = {
        "kind": "dataframe",
        "shape": [100, 3],
        "columns": ["a", "b", "c"],
        "dtypes": {"a": "int64"},
        "summary": {"a": {"mean": 1.0}},
        "head": [],
        "nulls": {"a": 0},
    }
    outputs = [
        {"output_type": "stream", "text": "__SPANINSIGHT_SCHEMA_START__"},
        {"output_type": "stream", "text": json.dumps(schema, default=str)},
        {"output_type": "stream", "text": "__SPANINSIGHT_SCHEMA_END__"},
    ]
    parsed, err = parse_schema_from_outputs(outputs)
    assert err is None
    assert parsed == schema


def test_parse_schema_reports_remote_error():
    payload = {"kind": "none", "error": "No tabular dataset (df) found"}
    outputs = [
        {
            "output_type": "stream",
            "text": f"__SPANINSIGHT_SCHEMA_START__{json.dumps(payload)}__SPANINSIGHT_SCHEMA_END__",
        }
    ]
    parsed, err = parse_schema_from_outputs(outputs)
    assert parsed is None
    assert err and "No tabular dataset" in err


def test_parse_schema_kernel_error_surfaces():
    outputs = [
        {
            "output_type": "error",
            "ename": "KernelError",
            "evalue": "boom",
            "traceback": ["KernelError: boom"],
        }
    ]
    parsed, err = parse_schema_from_outputs(outputs)
    assert parsed is None
    assert err and "KernelError" in err


def test_parse_schema_rejects_non_tabular_kind():
    payload = {"kind": "npz", "keys": ["x", "y"], "error": None}
    outputs = [
        {
            "output_type": "stream",
            "text": f"__SPANINSIGHT_SCHEMA_START__{json.dumps(payload)}__SPANINSIGHT_SCHEMA_END__",
        }
    ]
    parsed, err = parse_schema_from_outputs(outputs)
    assert parsed is None
    assert err


# ── THE regression: list-shaped outputs flow through the pipeline ─


class FakeColab:
    """Mimics ColabService.exec_code: returns a LIST of jupyter outputs."""

    def __init__(self, outputs):
        self._outputs = outputs
        self.executed = []

    async def exec_code(self, code, session_name=None, **kwargs):
        self.executed.append(code)
        return self._outputs


def _schema_stream_outputs(schema: dict) -> list[dict]:
    payload = json.dumps(schema, default=str)
    return [
        {"output_type": "stream", "text": "__SPANINSIGHT_SCHEMA_START__\n"},
        {"output_type": "stream", "text": payload},
        {"output_type": "stream", "text": "\n__SPANINSIGHT_SCHEMA_END__"},
    ]


@pytest.mark.asyncio
async def test_load_and_extract_schema_with_list_outputs():
    """Regression for the missing-description bug: real list contract must parse.

    The previous implementation checked `isinstance(res, dict)` and never
    extracted a schema — this exact input produced no description.
    """
    from screens.analysis.dataset_ops import load_and_extract_schema

    schema = {
        "kind": "dataframe",
        "shape": [50, 2],
        "columns": ["x", "y"],
        "dtypes": {"x": "int64", "y": "float64"},
        "summary": {},
        "head": [{"x": 1, "y": 2.5}],
        "nulls": {"x": 0, "y": 1},
    }
    colab = FakeColab(_schema_stream_outputs(schema))
    parsed, err = await load_and_extract_schema(colab, "sess", "import pandas")
    assert err is None
    assert parsed == schema
    assert len(colab.executed) == 2  # load code + schema code


@pytest.mark.asyncio
async def test_load_and_extract_schema_reports_failure_reason():
    from screens.analysis.dataset_ops import load_and_extract_schema

    colab = FakeColab([{"output_type": "stream", "text": "nothing useful"}])
    parsed, err = await load_and_extract_schema(colab, "sess", "load code")
    assert parsed is None
    assert err  # honest error instead of silent empty schema


@pytest.mark.asyncio
async def test_enrich_schema_with_ai_fallbacks():
    from screens.analysis.dataset_ops import enrich_schema_with_ai

    schema = {"kind": "dataframe", "columns": ["a"], "shape": [5, 1]}
    with (
        patch(
            "services.ai.analysis.describe_dataset", new_callable=AsyncMock
        ) as mock_desc,
        patch(
            "services.ai.analysis.suggest",
            new_callable=AsyncMock,
            side_effect=RuntimeError("gateway down"),
        ) as mock_suggest,
    ):
        mock_desc.return_value = "A dataset of things."
        enriched = await enrich_schema_with_ai(schema)

    assert enriched["description"] == "A dataset of things."
    # Gateway failure falls back to built-in chips instead of empty suggestions
    assert enriched["suggestions"], "fallback suggestions must be wired"
    assert mock_suggest.await_count == 1


# ── Load-code generation ──────────────────────────────────────────


def test_csv_load_code_has_encoding_fallback():
    code = suggest_load_code("data.csv")
    assert "utf-8" in code and "latin-1" in code
    assert "UnicodeDecodeError" in code
    assert "df = pd.read_csv" in code


def test_txt_load_code_sniffs_separator():
    code = suggest_load_code("dump.txt")
    assert "sep=None" in code and 'engine="python"' in code


def test_zip_load_code_loads_tabular_member_into_df():
    code = suggest_load_code("archive.zip")
    assert "extractall" in code
    assert "df = " in code  # must produce a DataFrame, not just extract


def test_sqlite_load_code_loads_table_into_df():
    code = suggest_load_code("store.db")
    assert "sqlite3.connect" in code
    assert "df = pd.read_sql_query" in code


def test_npy_load_code_uses_data_variable():
    code = suggest_load_code("weights.npy")
    assert "data = np.load" in code
    assert "df = " not in code  # arrays are NOT DataFrames — don't pretend


def test_generic_fallback_does_not_pretend_csv():
    code = suggest_load_code("unknown.xyz")
    assert "read_csv" not in code


def test_upload_extensions_accept_numpy_and_spss():
    from services.file_service import UPLOAD_EXTENSIONS

    assert {".npy", ".npz", ".sav"} <= UPLOAD_EXTENSIONS


class TestSuggestSalvage:
    """Malformed gateway JSON must not destroy all suggestions (live issue)."""

    def test_salvage_complete_objects_from_broken_array(self):
        from services.ai.analysis import salvage_json_objects

        broken = (
            '[{"label": "LOS Prediction", "icon": "🏥", "prompt": "Load the dataset '
            'and model length of stay"}, {"label": "Second", "icon": "📊", "prompt": "broken '
            "unclosed string"  # truncation mid-string
        )
        items = salvage_json_objects(broken)
        assert len(items) == 1
        assert items[0]["label"] == "LOS Prediction"

    def test_salvage_skips_invalid_objects_keeps_valid(self):
        from services.ai.analysis import salvage_json_objects

        text = '[{"label": "A"}, {not json}, {"label": "B"}]'
        items = salvage_json_objects(text)
        assert [i["label"] for i in items] == ["A", "B"]

    def test_salvage_handles_escaped_quotes(self):
        from services.ai.analysis import salvage_json_objects

        text = '[{"label": "He said \\"hi\\"", "prompt": "x"}]'
        items = salvage_json_objects(text)
        assert items and items[0]["label"] == 'He said "hi"'

    @pytest.mark.asyncio
    async def test_suggest_returns_salvaged_items(self):
        from services.ai import analysis as ai_service

        # Matches the live failure: raw array (no fence), broken mid-string
        broken_content = (
            '[{"label": "Ok One", "icon": "✨", "prompt": "do it"}, {"label": "Trunc'
        )
        with patch(
            "services.ai.analysis.suggestions.call_gateway",
            new_callable=AsyncMock,
        ) as mock_gateway:
            mock_gateway.return_value = {
                "choices": [{"message": {"content": broken_content}}]
            }
            result = await ai_service.suggest({"columns": ["a"]})

        assert any(s.get("label") == "Ok One" for s in result)


class TestAnalysisContextBuilder:
    def test_caps_cells_and_chars(self):
        from core.utils import build_analysis_context

        cells = [{"type": "code", "prompt": f"step {i}"} for i in range(20)] + [
            {"type": "markdown", "source": "ignore me"}
        ]
        ctx = build_analysis_context(cells, max_cells=6, max_chars=100)
        assert "step 19" in ctx
        assert "step 13" not in ctx  # only last 6
        assert len(ctx) <= 102  # 100 + ellipsis marker

    def test_empty(self):
        from core.utils import build_analysis_context

        assert build_analysis_context([]) == ""
