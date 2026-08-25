"""Forms across projects + autopilot pin/rebuild regressions.

- load_all_forms_async must gather forms from EVERY project (plus the
  account fallback), annotate owners, dedupe, sort newest-first — the Forms
  tab no longer depends on the active project.
- run_autopilot_async must pin every executed cell AND invoke
  on_cell_change afterwards; without that bump the pin icon never renders
  (manual pin bumps, which is why only manual pinning used to show).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import screens.forms.handlers as forms_handlers
from core.state import state
from screens.analysis.autopilot_ops import (
    run_autopilot_async,
    submit_prompt_async,
)
from screens.forms.handlers import load_all_forms_async

# ── load_all_forms_async ─────────────────────────────────────────


class _FakeProjects:
    def __init__(self, projects):
        self._projects = projects

    async def list_projects(self):
        return self._projects


class _FakeState:
    user_uuid = "usr_owner"

    def __init__(self):
        self.forms = []


@pytest.mark.asyncio
async def test_load_all_forms_merges_across_projects_and_annotates(monkeypatch):
    per_scope = {
        "proj_a": [
            {"id": "f_old", "created_at": "2026-01-01T00:00:00Z"},
            {"id": "f_new", "created_at": "2026-03-01T00:00:00Z"},
        ],
        "proj_b": [{"id": "f_b", "created_at": "2026-02-01T00:00:00Z"}],
        "usr_owner": [{"id": "f_legacy", "created_at": "2025-12-01T00:00:00Z"}],
    }

    async def fake_list_forms(project_id):
        return list(per_scope[project_id])

    monkeypatch.setattr(forms_handlers.forms_service, "list_forms", fake_list_forms)

    seen = []
    st = _FakeState()
    await load_all_forms_async(
        _FakeProjects(
            [{"id": "proj_a", "name": "Alpha"}, {"id": "proj_b", "name": ""}]
        ),
        st,
        set_user_forms=lambda fl: seen.append(fl),
        set_is_loading=lambda v: None,
        show_error=lambda m: pytest.fail(f"unexpected error: {m}"),
    )

    merged = seen[0]
    assert [f["id"] for f in merged] == ["f_new", "f_b", "f_old", "f_legacy"]
    owners = {f["id"]: f["_project_id"] for f in merged}
    assert owners == {
        "f_new": "proj_a",
        "f_old": "proj_a",
        "f_b": "proj_b",
        "f_legacy": "usr_owner",
    }
    names = {f["id"]: f["_project_name"] for f in merged}
    assert names["f_new"] == "Alpha" and names["f_b"] == ""
    assert st.forms is merged


@pytest.mark.asyncio
async def test_load_all_forms_dedupes_by_id_and_survives_scope_failure(monkeypatch):
    async def fake_list_forms(project_id):
        if project_id == "proj_bad":
            raise RuntimeError("network down")
        return [
            {"id": "f_dup", "created_at": "2026-05-01T00:00:00Z"},
            {"id": "f_dup", "created_at": "1999-01-01T00:00:00Z"},
        ]

    monkeypatch.setattr(forms_handlers.forms_service, "list_forms", fake_list_forms)

    seen = []
    st = _FakeState()
    await load_all_forms_async(
        _FakeProjects(
            [
                {"id": "proj_ok", "name": "OK"},
                {"id": "proj_bad", "name": "Bad"},
            ]
        ),
        st,
        set_user_forms=lambda fl: seen.append(fl),
        set_is_loading=lambda v: None,
        show_error=lambda m: pytest.fail(f"unexpected error: {m}"),
    )

    assert [f["id"] for f in seen[0]] == ["f_dup"]
    assert seen[0][0]["_project_id"] == "proj_ok"


# ── Autopilot pin + explicit rebuild ─────────────────────────────


@pytest.fixture()
def clean_state():
    saved = {
        k: getattr(state, k)
        for k in (
            "notebook_cells",
            "autopilot_running",
            "autopilot_cancelled",
            "autopilot_progress",
            "autopilot_steps",
            "active_session_name",
        )
    }
    yield state
    for k, v in saved.items():
        setattr(state, k, v)


def _run_cell_writer(outputs):
    async def _write(cell_id):
        cell = next(c for c in state.notebook_cells if c["id"] == cell_id)
        cell["outputs"] = outputs

    return _write


@pytest.mark.asyncio
async def test_autopilot_pins_every_step_and_bumps_ui(clean_state):
    state.active_session_name = "sess_x"
    state.notebook_cells = []

    plans = [
        {"is_complete": False, "prompt": "step one"},
        {"is_complete": True, "reason": "done"},
    ]
    bump = MagicMock()
    with (
        patch(
            "services.ai.analysis.plan_next_step",
            AsyncMock(side_effect=plans),
        ),
        patch(
            "services.ai.analysis.generate_code_meta",
            AsyncMock(return_value={"code": "print(1)"}),
        ),
        patch(
            "services.ai.analysis.describe_result",
            AsyncMock(return_value="found insight"),
        ),
    ):
        await run_autopilot_async(
            "sess_x",
            {"columns": []},
            type("C", (), {"spend": AsyncMock(return_value=(True, 0))})(),
            None,  # page: every use is guarded by `if page`
            lambda t, s="": state.add_cell(t, s),
            _run_cell_writer(
                [{"output_type": "stream", "name": "stdout", "text": "ok"}]
            ),
            bump,
        )

    assert len(state.notebook_cells) == 1
    cell = state.notebook_cells[0]
    assert cell["pinned"] is True
    assert cell["narration"] == "found insight"
    assert bump.called, "pin must trigger a UI version bump or it never renders"


@pytest.mark.asyncio
async def test_autopilot_pins_failed_cell_with_caption_and_continues(clean_state):
    state.active_session_name = "sess_x"
    state.notebook_cells = []

    plans = [
        {"is_complete": False, "prompt": "doomed step"},
        {"is_complete": True, "reason": "done"},
    ]

    def failing_writer(outputs):
        async def _write(cell_id):
            cell = next(c for c in state.notebook_cells if c["id"] == cell_id)
            cell["outputs"] = outputs

        return _write

    bump = MagicMock()
    with (
        patch(
            "services.ai.analysis.plan_next_step",
            AsyncMock(side_effect=plans),
        ),
        patch(
            "services.ai.analysis.generate_code_meta",
            AsyncMock(
                side_effect=[
                    {"code": "raise boom"},
                    {"code": "print('recovered')"},
                ]
            ),
        ),
        patch(
            "services.ai.analysis.describe_result",
            AsyncMock(return_value="should not be used"),
        ),
    ):
        await run_autopilot_async(
            "sess_x",
            {"columns": []},
            type("C", (), {"spend": AsyncMock(return_value=(True, 0))})(),
            None,
            lambda t, s="": state.add_cell(t, s),
            failing_writer([{"output_type": "error", "ename": "E", "evalue": "x"}]),
            bump,
        )

    assert len(state.notebook_cells) == 1
    cell = state.notebook_cells[0]
    # Failed steps are still pinned (legacy parity) with a visible caption;
    # report compilation filters them out via the failed flag.
    assert cell["pinned"] is True
    assert cell.get("failed") is True
    assert "failed even after self-healing" in (cell.get("narration") or "")
    assert bump.called


def test_agent_signatures_accept_rebuild_callback():
    import inspect

    assert "on_cell_change" in inspect.signature(run_autopilot_async).parameters
    assert "on_cell_change" in inspect.signature(submit_prompt_async).parameters
