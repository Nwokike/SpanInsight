"""Tests for ReportService CRUD and block manipulation."""

from __future__ import annotations

import pytest

from core.state import state
from services.report_service import ReportService
from services.storage_service import StorageService


@pytest.mark.asyncio
async def test_report_create_and_list(tmp_path):
    state.user_reports = []
    storage = StorageService(data_dir=str(tmp_path))
    report_svc = ReportService(storage=storage)

    blocks = [
        {
            "prompt": "Revenue by Region",
            "description": "Bar chart",
            "figure_png_b64": "",
        },
    ]

    created = await report_svc.create_report(
        title="Q3 Sales Analysis",
        dataset_name="sales.csv",
        blocks=blocks,
        description="Exploratory report on regional revenue",
    )
    assert created["id"] is not None
    assert created["title"] == "Q3 Sales Analysis"
    assert len(created["blocks"]) == 1

    reports = await report_svc.list_reports()
    assert len(reports) == 1
    assert reports[0]["id"] == created["id"]


@pytest.mark.asyncio
async def test_report_update_and_delete(tmp_path):
    state.user_reports = []
    storage = StorageService(data_dir=str(tmp_path))
    report_svc = ReportService(storage=storage)

    created = await report_svc.create_report(
        title="Draft", dataset_name="data.csv", blocks=[]
    )
    rep_id = created["id"]

    ok = await report_svc.update_report(
        rep_id, {"title": "Final Report", "is_arranged": True}
    )
    assert ok is True

    fetched = await report_svc.get_report(rep_id)
    assert fetched["title"] == "Final Report"
    assert fetched["is_arranged"] is True

    await report_svc.delete_report(rep_id)
    reports = await report_svc.list_reports()
    assert len(reports) == 0
