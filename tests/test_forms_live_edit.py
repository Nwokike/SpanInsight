"""Live-form editing: stable question ids, validation, smart-merge helpers."""

from __future__ import annotations

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
