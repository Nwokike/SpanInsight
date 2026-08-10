"""Tests for AI reports parsing and repair services."""

from services.ai.reports import _parse_resilient_json, _repair_json


def test_repair_json_single_quotes():
    raw_json = "{'title': 'My Report', 'blocks': [{'prompt': 'Clean data', 'original_index': 0}]}"
    repaired = _repair_json(raw_json)
    # Quotes should be converted to double quotes
    assert '"title"' in repaired
    assert '"My Report"' in repaired
    assert '"blocks"' in repaired


def test_repair_json_missing_commas():
    raw_json = '{"title": "Report"} {"description": "Summary"}'
    repaired = _repair_json(raw_json)
    # Comma should be inserted between objects
    assert "}, {" in repaired


def test_repair_json_trailing_commas():
    raw_json = '{"a": 1, "b": 2,}'
    repaired = _repair_json(raw_json)
    assert ',"' not in repaired
    assert repaired.strip().endswith("}")


def test_parse_resilient_json_success():
    text = 'Here is the response: {"title": "Correct title"} which is complete.'
    parsed = _parse_resilient_json(text)
    assert isinstance(parsed, dict)
    assert parsed["title"] == "Correct title"
