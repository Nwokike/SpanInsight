"""Project management service v2 — local-only, no gateway sync.

In v2, execution runs on Google Colab. Projects are local organizational
containers for reports and forms. No cloud sync, no Delta Sync, no blocks.
"""

from __future__ import annotations

import json
import logging
import uuid

import flet as ft

from core.state import state

logger = logging.getLogger(__name__)

STORAGE_PROJECTS = "spaninsight_projects"
STORAGE_ACTIVE_PROJECT_ID = "spaninsight_active_project_id"


class ProjectService:
    def __init__(self, page: ft.Page, storage):
        self._page = page
        self._storage = storage

    async def initialize_projects(self) -> str:
        """Load projects from storage or create a default one. Returns active_project_id."""
        try:
            active_id = await self._storage.get(STORAGE_ACTIVE_PROJECT_ID)

            raw_projects = await self._storage.get(STORAGE_PROJECTS)
            try:
                projects = json.loads(raw_projects) if raw_projects else {}
                if not isinstance(projects, dict):
                    raise TypeError("Projects data is not a dict")
            except (json.JSONDecodeError, ValueError, TypeError) as parse_err:
                logger.error("Corrupt projects JSON, resetting: %s", parse_err)
                projects = {}

            state.user_projects = projects

            if not projects:
                logger.info("No projects found. Generating default workspace...")
                default_proj = await self.create_project("My Workspace")
                active_id = default_proj["id"]

            if not active_id or active_id not in state.user_projects:
                active_id = next(iter(state.user_projects.keys()))

            state.active_project_id = active_id
            await self._storage.set(STORAGE_ACTIVE_PROJECT_ID, active_id)
            return active_id

        except Exception as e:
            logger.error("Failed to initialize projects: %s", e)
            return ""

    async def create_project(self, title: str, description: str = "") -> dict:
        """Create a new local project."""
        proj_id = "proj_" + uuid.uuid4().hex[:8]

        project = {
            "id": proj_id,
            "title": title,
            "description": description,
            "user_reports": [],
            "forms": [],
        }

        state.user_projects[proj_id] = project
        await self._persist_local_projects()
        logger.info("Created project %s: %s", proj_id, title)
        return project

    async def rename_project(self, project_id: str, new_title: str) -> bool:
        """Rename a project."""
        proj = state.user_projects.get(project_id)
        if not proj:
            return False
        proj["title"] = new_title
        await self._persist_local_projects()
        return True

    async def delete_project(self, project_id: str) -> bool:
        """Remove a project locally."""
        state.user_projects.pop(project_id, None)
        await self._persist_local_projects()

        if state.active_project_id == project_id:
            if state.user_projects:
                state.active_project_id = next(iter(state.user_projects.keys()))
            else:
                await self.create_project("My Workspace")
                state.active_project_id = next(iter(state.user_projects.keys()))
            await self._storage.set(STORAGE_ACTIVE_PROJECT_ID, state.active_project_id)

        return True

    # ── Helpers ──────────────────────────────────────────────────────

    async def _persist_local_projects(self):
        """Write current user_projects cache to local device storage."""
        safe_copy = {}
        for pid, p in state.user_projects.items():
            safe_copy[pid] = self._serialize_local_project(p)
        await self._storage.set(STORAGE_PROJECTS, json.dumps(safe_copy))

    @staticmethod
    def _serialize_local_project(proj: dict) -> dict:
        """Prepare project data dict for local JSON serialization."""
        # Deep copy via JSON round-trip, skip non-serializable objects
        try:
            return json.loads(json.dumps(proj, default=str))
        except Exception:
            return {"id": proj.get("id", ""), "title": proj.get("title", "")}
