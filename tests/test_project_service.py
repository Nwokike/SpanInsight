"""Tests for ProjectService CRUD, .ipynb auto-persistence, and file versioning."""

from __future__ import annotations

import pytest

from services.project_service import ProjectService
from services.storage_service import StorageService


@pytest.mark.asyncio
async def test_project_create_and_list(tmp_path):
    storage = StorageService(data_dir=str(tmp_path))
    project_svc = ProjectService(storage=storage)

    cells = [
        {
            "id": "cell_1",
            "type": "code",
            "source": "import pandas as pd\ndf = pd.read_csv('data.csv')",
            "outputs": [],
        }
    ]
    created = await project_svc.create_project(
        name="Sales Forecast Q4",
        primary_dataset="sales_q4.csv",
        hardware="T4 GPU",
        initial_cells=cells,
    )

    assert created["id"].startswith("proj_")
    assert created["name"] == "Sales Forecast Q4"
    assert created["primary_dataset"] == "sales_q4.csv"
    assert created["hardware"] == "T4 GPU"
    assert len(created["notebook_cells"]) == 1

    projects = await project_svc.list_projects()
    assert len(projects) == 1
    assert projects[0]["id"] == created["id"]
    assert projects[0]["name"] == "Sales Forecast Q4"
    assert projects[0]["cell_count"] == 1


@pytest.mark.asyncio
async def test_project_ipynb_persistence_roundtrip(tmp_path):
    storage = StorageService(data_dir=str(tmp_path))
    project_svc = ProjectService(storage=storage)

    created = await project_svc.create_project(
        name="Churn Analysis", primary_dataset="churn.csv"
    )
    pid = created["id"]

    # Append a markdown summary and code cell
    created["notebook_cells"] = [
        {
            "id": "m1",
            "type": "markdown",
            "source": "# Customer Churn Investigation",
            "outputs": [],
        },
        {
            "id": "c1",
            "type": "code",
            "source": "df['churn'].value_counts()",
            "outputs": [{"output_type": "stream", "text": "0: 800\n1: 200"}],
        },
    ]
    await project_svc.save_project(created)

    # Re-fetch project from storage
    loaded = await project_svc.get_project(pid)
    assert loaded is not None
    assert len(loaded["notebook_cells"]) == 2
    assert loaded["notebook_cells"][0]["type"] == "markdown"
    assert "Customer Churn" in loaded["notebook_cells"][0]["source"]
    assert loaded["notebook_cells"][1]["type"] == "code"


@pytest.mark.asyncio
async def test_project_file_versioning(tmp_path):
    storage = StorageService(data_dir=str(tmp_path))
    project_svc = ProjectService(storage=storage)

    created = await project_svc.create_project(
        name="Cleaned Data Project", primary_dataset="raw.csv"
    )
    pid = created["id"]

    # Add initial version of transformed dataset
    p1 = await project_svc.add_file_version(
        pid, "cleaned.csv", "/content/cleaned.csv", size=1024
    )
    assert len(p1["file_versions"]) == 1
    assert p1["file_versions"][0]["version"] == 1

    # Modify and add next version
    p2 = await project_svc.add_file_version(
        pid, "cleaned.csv", "/content/cleaned.csv", size=2048
    )
    assert len(p2["file_versions"]) == 1
    assert p2["file_versions"][0]["version"] == 2
    assert p2["file_versions"][0]["size"] == 2048


@pytest.mark.asyncio
async def test_project_delete(tmp_path):
    storage = StorageService(data_dir=str(tmp_path))
    project_svc = ProjectService(storage=storage)

    created = await project_svc.create_project(name="Temporary Project")
    pid = created["id"]

    assert len(await project_svc.list_projects()) == 1
    await project_svc.delete_project(pid)

    assert len(await project_svc.list_projects()) == 0
    assert await project_svc.get_project(pid) is None
