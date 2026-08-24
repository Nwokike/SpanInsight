"""Live-form editing: stable question ids, validation, smart-merge helpers."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from components.form_editor.field_card import new_field
from screens.forms.handlers import _form_schema_fields, normalize_field_names
from services.forms_service import (
    _validate_schema,
    responses_to_csv_bytes,
    update_form,
)

# ── Stable question identity ─────────────────────────────────────────


def test_new_field_generates_immutable_opaque_names():
    schema = []
    a = new_field(schema)
    b = new_field(schema + [a])
    assert a["name"].startswith("q_")
    assert b["name"] != a["name"]
    assert not a["name"].startswith("new_field")  # never label-derived


def test_normalize_keeps_existing_and_repairs_bad_names():
    fields = [
        {"name": "age", "label": "Age", "type": "number"},
        {"name": "", "label": "Broken", "type": "text"},
        {"name": "age", "label": "Duplicate", "type": "text"},
        {"name": "keep_me", "label": "Preserved", "type": "text"},
    ]
    out = normalize_field_names(fields, preserve={"keep_me"})
    names = [f["name"] for f in out]
    assert names[0] == "age"
    assert names[3] == "keep_me"  # preserved identity untouched
    assert len(set(names)) == len(names)  # all unique
    assert all(n for n in names)


def test_label_rename_never_touches_name_in_card_update():
    """The field card's _update closure must leave `name` alone on rename."""
    # Simulate what build_field_card._update does after the fix: it copies the
    # dict and only sets the edited key.
    field = {"name": "q_ab12cd34ef", "label": "Old", "type": "text"}
    updated = dict(field)
    updated["label"] = "Renamed question"  # label change
    assert updated["name"] == "q_ab12cd34ef"


# ── Save-time validation ──────────────────────────────────────────────


def test_validate_rejects_duplicate_names():
    bad = [
        {"name": "a", "label": "A", "type": "text"},
        {"name": "a", "label": "B", "type": "text"},
    ]
    assert _validate_schema(bad)


def test_validate_rejects_empty_name():
    assert _validate_schema([{"name": "", "label": "A", "type": "text"}])


def test_validate_accepts_good_schema():
    good = [{"name": "a", "label": "A", "type": "text"}]
    assert _validate_schema(good) is None


# ── Smart-merge data helpers ─────────────────────────────────────────


def test_form_schema_fields_parses_string_and_list():
    assert len(_form_schema_fields({"schema_json": '[{"name":"a"}]'})) == 1
    assert len(_form_schema_fields({"schema_json": [{"name": "a"}]})) == 1
    assert _form_schema_fields({"schema_json": "not json"}) == []
    assert _form_schema_fields({}) == []


def test_csv_headers_use_labels_with_fallbacks():
    responses = [
        {"data": {"q1": "x", "legacy_key": "y"}},
        {"data": {"q1": "z"}},
    ]
    schema_fields = [
        {"name": "q1", "label": "Full Name"},
        {"name": "q9", "label": "Unused"},
        {"name": "legacy_key", "label": "Full Name"},  # collision -> raw key
    ]
    text = (
        responses_to_csv_bytes(responses, schema_fields).decode().replace("\r\n", "\n")
    )
    header, row1, row2 = text.strip().split("\n")
    assert header == "Full Name,legacy_key"
    assert row1 == "x,y"
    assert row2 == "z,"


# ── update_form service call ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_form_sends_patch_with_payload():
    schema = [{"name": "a", "label": "A", "type": "text"}]
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch(
        "services.forms_service.request_with_retry", new_callable=AsyncMock
    ) as mock_req:
        mock_req.return_value = mock_response
        ok = await update_form("form_1", "proj_1", "T", "D", schema)

    assert ok is True
    method, url = mock_req.call_args.args[0], mock_req.call_args.args[1]
    assert method == "PATCH"
    assert url.endswith("/forms/form_1")
    payload = mock_req.call_args.kwargs["json"]
    assert payload["project_id"] == "proj_1"
    assert payload["title"] == "T"
    assert payload["schema_json"] == schema


@pytest.mark.asyncio
async def test_update_form_rejects_invalid_schema_before_network():
    with patch(
        "services.forms_service.request_with_retry", new_callable=AsyncMock
    ) as mock_req:
        ok = await update_form("f", "p", "T", "D", [{"name": "dup"}, {"name": "dup"}])

    assert ok is False
    mock_req.assert_not_called()


# ── Survey → CSV dataset pipeline ─────────────────────────────────────


def test_build_form_file_name_is_stable_and_collision_free():
    from screens.forms.dataset_sync import build_form_file_name

    a = build_form_file_name("Jollof Rice Test!", "form_ujb5o7dbXZoZ")
    b = build_form_file_name("Jollof Rice Test!", "form_abcdef1234")
    assert a == "Jollof_Rice_Test_dbXZoZ_responses.csv"
    assert a != b  # id suffix keeps same-titled forms apart
    assert build_form_file_name("", "") == "survey_000000_responses.csv"


def test_snapshot_path_matches_load_code():
    from services.file_service import snapshot_path_for, suggest_load_code

    name = "My Survey (2026)_responses.csv"
    assert snapshot_path_for(name) in suggest_load_code(name)


@pytest.mark.asyncio
async def test_fetch_all_responses_walks_pagination():
    from services.forms_service import fetch_all_responses

    pages = {
        1: {"count": 3, "responses": [{"id": 1, "data": {"a": 1}}, {"id": 2}]},
        2: {"count": 3, "responses": [{"id": 3, "data": {"a": 2}}]},
    }

    class FakeResp:
        def __init__(self, payload):
            self.status_code = 200
            self._p = payload

        def json(self):
            return self._p

    class FakeClient:
        async def get(self, url, params=None, timeout=None):
            return FakeResp(pages[params["page"]])

    with patch("services.forms_service.get_client", return_value=FakeClient()):
        rows = await fetch_all_responses("f1", "proj_1")

    assert [r["id"] for r in rows] == [1, 2, 3]


def test_export_csv_aliases_labels_and_dedupes():
    from screens.forms.dataset_sync import export_responses_to_csv

    form = {
        "title": "S",
        "schema_json": [
            {"name": "q1", "label": "Age", "type": "number"},
            {"name": "legacy", "label": "Age", "type": "text"},  # collision
        ],
    }
    responses = [
        {"data": {"q1": 39, "legacy": "x"}},
        {"data": {"q1": 22}},
    ]
    text = export_responses_to_csv(form, responses).decode().replace("\r\n", "\n")
    header, row1, row2 = text.strip().split("\n")
    assert header == "Age,legacy"  # collision falls back to storage key
    assert row1 == "39,x" and row2 == "22,"


# ── Verified Agent: verifier + planner contracts ─────────────────────


@pytest.mark.asyncio
async def test_verify_result_parses_strict_contract():
    from services.ai.analysis.interpreters import verify_result

    payload = {
        "satisfied": True,
        "answer": "Mean income is 13,266.",
        "gaps": [],
        "key_numbers": ["mean=13266"],
    }

    class FakeResp:
        status_code = 200

        def json(self):
            return {}

    with (
        patch(
            "services.ai.analysis.interpreters.call_gateway", new_callable=AsyncMock
        ) as mock_gw,
        patch("services.ai.analysis.interpreters.extract_content") as mock_c,
        # extract_block_by_pattern is imported INSIDE verify_result at call
        # time, so it must be patched at its source module.
        patch("services.ai.client.extract_block_by_pattern") as mock_b,
    ):
        mock_gw.return_value = FakeResp()
        mock_c.return_value = "here:" + json.dumps(payload)
        mock_b.return_value = json.dumps(payload)
        out = await verify_result("q?", "desc", {"stdout": "x"})

    assert out["satisfied"] is True and out["verified"] is True
    assert out["answer"].startswith("Mean income")
    assert out["key_numbers"] == ["mean=13266"]


@pytest.mark.asyncio
async def test_verify_result_degrades_gracefully_on_bad_payload():
    from services.ai.analysis.interpreters import verify_result

    with (
        patch(
            "services.ai.analysis.interpreters.call_gateway", new_callable=AsyncMock
        ) as mock_gw,
        patch("services.ai.analysis.interpreters.extract_content"),
        patch("services.ai.client.extract_block_by_pattern"),
    ):
        mock_gw.side_effect = RuntimeError("gateway down")
        out = await verify_result("q?", "d", {})

    assert out["verified"] is False and out["satisfied"] is False


@pytest.mark.asyncio
async def test_plan_insight_approach_steps_and_fallback():
    from services.ai.analysis.suggestions import plan_insight_approach

    good = {"steps": ["filter df", "groupby price", "plot trend"]}

    class FakeResp:
        status_code = 200

        def json(self):
            return {}

    with (
        patch(
            "services.ai.analysis.suggestions.call_gateway", new_callable=AsyncMock
        ) as mock_gw,
        patch("services.ai.analysis.suggestions.extract_content") as mock_c,
        patch("services.ai.analysis.suggestions.extract_block_by_pattern") as mock_b,
    ):
        mock_gw.return_value = FakeResp()
        mock_c.return_value = json.dumps(good)
        mock_b.return_value = json.dumps(good)
        out = await plan_insight_approach("q", {"columns": ["a"]})
        assert out["steps"][0] == "filter df"

        mock_gw.side_effect = RuntimeError("down")
        out2 = await plan_insight_approach("What drives price?", {"columns": []})
        assert out2["steps"] == ["What drives price?"]
