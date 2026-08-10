import pytest

from core.state import state
from services.project_service import ProjectService
from services.report_service import ReportService


class MockStorage:
    def __init__(self):
        self.data = {}

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def set(self, key: str, value: str) -> None:
        self.data[key] = value

    async def delete(self, key: str) -> None:
        self.data.pop(key, None)

    async def flush(self) -> None:
        pass


class MockPage:
    def __init__(self):
        self.dialog = None

    def update(self):
        pass


@pytest.mark.asyncio
async def test_project_lifecycle():
    # Setup mock page and storage
    page = MockPage()
    storage = MockStorage()

    # Reset singleton state
    state.active_project_id = ""
    state.user_projects = {}

    project_svc = ProjectService(page, storage)

    # 1. Initialize (creates default "My Workspace")
    from unittest.mock import patch

    import httpx

    with patch("services.project_service.request_with_retry") as mock_req:
        mock_req.side_effect = httpx.RequestError("offline")
        active_id = await project_svc.initialize_projects()
    assert active_id != ""
    assert active_id in state.user_projects
    assert state.user_projects[active_id]["title"] == "My Workspace"
    assert len(state.user_projects[active_id]["phrase"].split()) == 12

    # 2. Create another local project
    proj2 = await project_svc.create_local_project("Q2 Sales Audit", "Audit of Q2 data")
    pid2 = proj2["id"]
    assert pid2 in state.user_projects
    assert state.user_projects[pid2]["title"] == "Q2 Sales Audit"

    # 3. Rename project (mocked offline to keep local ID)
    from unittest.mock import patch

    with patch("services.project_service.request_with_retry") as mock_req:
        import httpx

        mock_req.side_effect = httpx.RequestError("offline")
        await project_svc.rename_project(pid2, "Q2 Sales Finalized")
    assert state.user_projects[pid2]["title"] == "Q2 Sales Finalized"

    # 4. Switch project and verify state dynamic properties change
    state.active_project_id = active_id
    assert state.current_df_name == ""

    # Modify dynamic property of active project
    state.current_df_name = "sales.csv"
    assert state.user_projects[active_id]["current_df_name"] == "sales.csv"

    # Switch to project 2 and verify it is empty/different
    state.active_project_id = pid2
    assert state.current_df_name == ""

    # 5. Delete project
    # Delete non-active project first
    await project_svc.delete_project(active_id)
    assert active_id not in state.user_projects
    assert (
        state.active_project_id == pid2
    )  # Active project switched since previous active was deleted

    # Delete final remaining project (creates "My Workspace" fallback automatically)
    await project_svc.delete_project(pid2)
    assert pid2 not in state.user_projects
    assert state.active_project_id != ""
    assert state.user_projects[state.active_project_id]["title"] == "My Workspace"


@pytest.mark.asyncio
async def test_report_service_project_context():
    # Setup mock page and storage
    page = MockPage()
    storage = MockStorage()

    state.active_project_id = ""
    state.user_projects = {}

    project_svc = ProjectService(page, storage)
    from unittest.mock import patch

    import httpx

    with patch("services.project_service.request_with_retry") as mock_req:
        mock_req.side_effect = httpx.RequestError("offline")
        await project_svc.initialize_projects()
    active_id1 = state.active_project_id

    # Create Q2 project and make it active
    proj2 = await project_svc.create_local_project("Audit Workspace")
    state.active_project_id = proj2["id"]

    report_svc = ReportService(storage)

    # Verify reports are empty initially for active project 2
    reports = await report_svc.list_reports()
    assert len(reports) == 0

    # Create a report under active project 2
    rpt = await report_svc.create_report(
        "Q2 Summary",
        "q2_dataset.csv",
        [{"prompt": "Show counts", "block_type": "text"}],
    )
    assert rpt["id"] != ""
    assert rpt["title"] == "Q2 Summary"

    # Listing reports should return the created report
    reports2 = await report_svc.list_reports()
    assert len(reports2) == 1
    assert reports2[0]["id"] == rpt["id"]

    # Switch back to default project 1
    state.active_project_id = active_id1

    # Listing reports for project 1 should be completely empty!
    reports1 = await report_svc.list_reports()
    assert len(reports1) == 0


@pytest.mark.asyncio
async def test_pull_project_behaviors():
    # Setup mock page and storage
    page = MockPage()
    storage = MockStorage()

    state.active_project_id = ""
    state.user_projects = {}

    project_svc = ProjectService(page, storage)

    # 1. Local-only project pull -> returns "local"
    proj_local = await project_svc.create_local_project("Local Workspace")
    status = await project_svc.pull_project(proj_local["id"])
    assert status == "local"

    # Register project locally
    proj_server = {
        "id": "123456",
        "title": "Cloud Workspace",
        "description": "desc",
        "phrase": "phrase",
        "phrase_hash": "hash",
        "current_df_name": "local_file.csv",
        "current_file_path": "/path/to/local_file.csv",
        "analysis_blocks": [],
        "user_reports": [],
        "forms": [],
        "synced_at": 100.0,  # Synced timestamp
    }
    state.user_projects["123456"] = proj_server

    # 2. Remote deleted (404) -> returns "deleted"
    from unittest.mock import AsyncMock, MagicMock, patch

    with patch("services.project_service.get_client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client.return_value.get = AsyncMock(return_value=mock_resp)

        status = await project_svc.pull_project("123456")
        assert status == "deleted"

    # 3. Successful merge (200 with new blocks) -> returns True
    with patch("services.project_service.get_client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "blocks": [
                {
                    "id": "new_block_id_1",
                    "prompt": "Step 1",
                    "code": "print('Step 1')",
                    "description": "First block description",
                }
            ]
        }
        mock_client.return_value.get = AsyncMock(return_value=mock_resp)

        status = await project_svc.pull_project("123456")
        assert status is True

        # Verify local blocks are updated
        updated_proj = state.user_projects["123456"]
        assert len(updated_proj["analysis_blocks"]) == 1
        assert updated_proj["analysis_blocks"][0]["id"] == "new_block_id_1"
        assert updated_proj["analysis_blocks"][0]["needs_execution"] is True

        # Verify device-specific dataset path is retained!
        assert updated_proj["current_df_name"] == "local_file.csv"
        assert updated_proj["current_file_path"] == "/path/to/local_file.csv"

    # 4. No-op (200 with no new blocks) -> returns False
    with patch("services.project_service.get_client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"blocks": []}
        mock_client.return_value.get = AsyncMock(return_value=mock_resp)

        status = await project_svc.pull_project("123456")
        assert status is False
        assert (
            state.user_projects["123456"]["title"] == "Cloud Workspace"
        )  # Retains current title (no merge)


@pytest.mark.asyncio
async def test_block_pinning_unpinning_multi_report():
    # Setup mock page and storage
    page = MockPage()
    storage = MockStorage()

    state.active_project_id = ""
    state.user_projects = {}

    project_svc = ProjectService(page, storage)
    from unittest.mock import patch

    import httpx

    with patch("services.project_service.request_with_retry") as mock_req:
        mock_req.side_effect = httpx.RequestError("offline")
        await project_svc.initialize_projects()

    report_svc = ReportService(storage)

    # 1. Create a dummy analysis block in active project
    import uuid

    block_id = "blk_" + str(uuid.uuid4())[:8]
    analysis_block = {
        "id": block_id,
        "type": "analysis",
        "prompt": "Test Prompt",
        "code": "print('hello')",
        "description": "Test Block Insight",
        "figure_png": b"fake_png",
        "failed": False,
    }
    state.analysis_blocks.append(analysis_block)

    # Calculate dynamic pinning - initially should be False
    is_pinned_init = any(
        any(b.get("source_block_id") == block_id for b in r.get("blocks", []))
        for r in state.user_reports
    )
    assert is_pinned_init is False

    # 2. Pin to a new report
    report1 = await report_svc.create_report("Report 1", "test.csv", [])
    report2 = await report_svc.create_report("Report 2", "test.csv", [])

    # Verify both reports loaded
    reports = await report_svc.list_reports()
    assert len(reports) == 2

    # Add block to Report 1
    report_block = {
        "source_block_id": block_id,
        "prompt": "Test Prompt",
        "description": "Test Block Insight",
        "figure_png_b64": "ZmFrZV9wbmc=",
        "block_type": "chart",
    }
    await report_svc.add_block_to_report(report1["id"], report_block)

    # Calculate dynamic pinning - should now be True
    is_pinned_after_1 = any(
        any(b.get("source_block_id") == block_id for b in r.get("blocks", []))
        for r in state.user_reports
    )
    assert is_pinned_after_1 is True

    # Check that Report 1 has 1 block, Report 2 has 0 blocks
    r1_updated = await report_svc.get_report(report1["id"])
    r2_updated = await report_svc.get_report(report2["id"])
    assert len(r1_updated["blocks"]) == 1
    assert len(r2_updated["blocks"]) == 0
    assert r1_updated["blocks"][0]["source_block_id"] == block_id

    # 3. Pin to Report 2 as well (multi-report pinning)
    await report_svc.add_block_to_report(report2["id"], report_block)
    r2_updated = await report_svc.get_report(report2["id"])
    assert len(r2_updated["blocks"]) == 1
    assert r2_updated["blocks"][0]["source_block_id"] == block_id

    # Dynamic pinning still True
    is_pinned_after_2 = any(
        any(b.get("source_block_id") == block_id for b in r.get("blocks", []))
        for r in state.user_reports
    )
    assert is_pinned_after_2 is True

    # 4. Remove block from Report 1 (unpinning)
    r1_blocks = [
        b for b in r1_updated.get("blocks", []) if b.get("source_block_id") != block_id
    ]
    await report_svc.update_report(report1["id"], {"blocks": r1_blocks})

    # Verify Report 1 has 0 blocks, Report 2 still has 1 block
    r1_final = await report_svc.get_report(report1["id"])
    r2_final = await report_svc.get_report(report2["id"])
    assert len(r1_final["blocks"]) == 0
    assert len(r2_final["blocks"]) == 1

    # Dynamic pinning still True because it is in Report 2
    is_pinned_still = any(
        any(b.get("source_block_id") == block_id for b in r.get("blocks", []))
        for r in state.user_reports
    )
    assert is_pinned_still is True

    # 5. Remove block from Report 2
    r2_blocks = [
        b for b in r2_updated.get("blocks", []) if b.get("source_block_id") != block_id
    ]
    await report_svc.update_report(report2["id"], {"blocks": r2_blocks})

    # Dynamic pinning should now be False!
    is_pinned_final = any(
        any(b.get("source_block_id") == block_id for b in r.get("blocks", []))
        for r in state.user_reports
    )
    assert is_pinned_final is False
