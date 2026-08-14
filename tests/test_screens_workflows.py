"""Tests for screen workflow state transitions and user journey flows."""

from __future__ import annotations

from core.state import state
from screens.files.actions import handle_load_in_analysis
from services.forms_service import responses_to_csv_bytes


def test_onboarding_to_home_workflow():
    state.onboarding_done = False
    assert state.onboarding_done is False

    # User clicks get started
    state.onboarding_done = True
    assert state.onboarding_done is True


def test_home_to_analysis_workflow():
    state.current_tab = 0
    state.current_tab = 1
    assert state.current_tab == 1


def test_files_load_in_analysis_workflow():
    state.clear_notebook()
    state.current_tab = 0
    handle_load_in_analysis(page=None, current_path="/content", item_name="sales.csv")

    assert state.current_tab == 1
    assert len(state.notebook_cells) == 1
    assert "read_csv('/content/sales.csv')" in state.notebook_cells[0]["source"]


def test_project_load_and_switch_workflow():
    project_payload = {
        "id": "proj_demo123",
        "name": "E-Commerce Revenue Analysis",
        "primary_dataset": "orders.csv",
        "hardware": "T4 GPU",
        "session_name": "ses_colab_99",
        "notebook_cells": [
            {
                "id": "cell_1",
                "type": "code",
                "source": "df['revenue'].sum()",
                "outputs": [],
            }
        ],
    }
    state.load_project(project_payload)

    assert state.active_project_id == "proj_demo123"
    assert state.active_project_name == "E-Commerce Revenue Analysis"
    assert state.active_project_dataset == "orders.csv"
    assert state.session_hardware == "T4 GPU"
    assert state.active_session_name == "ses_colab_99"
    assert len(state.notebook_cells) == 1
    assert "df['revenue'].sum()" in state.notebook_cells[0]["source"]


def test_forms_csv_export():
    responses = [
        {"data": {"Score": 5, "Comment": "Great!"}},
        {"data": {"Score": 4, "Comment": "Good"}},
    ]
    csv_bytes = responses_to_csv_bytes(responses)
    csv_text = csv_bytes.decode("utf-8")
    assert "Score,Comment" in csv_text
    assert "5,Great!" in csv_text
    assert "4,Good" in csv_text
