"""Project management service — local project entity persistence and .ipynb synchronization.

A Project encapsulates:
- id, name, created_at, updated_at
- session_name (associated Colab session)
- hardware (CPU, T4 GPU, TPU v2)
- primary_dataset (e.g. sales.csv)
- schema_json (compressed dataset metadata & statistics)
- notebook_cells (live cells with code, markdown, outputs, and figures)
- file_versions (tracked dataset files & modified outputs)
"""

from __future__ import annotations

import json
import logging
import time
import uuid

from services.ipynb_converter import cells_to_ipynb, ipynb_to_cells

logger = logging.getLogger("ProjectService")

STORAGE_PROJECTS_INDEX = "spaninsight_projects_index"


class ProjectService:
    def __init__(self, storage):
        self._storage = storage

    async def list_projects(self) -> list[dict]:
        """Fetch all projects, sorted by updated_at descending."""
        raw = await self._storage.get(STORAGE_PROJECTS_INDEX)
        if not raw:
            return []
        try:
            projects = json.loads(raw)
            if isinstance(projects, list):
                projects.sort(key=lambda p: p.get("updated_at", 0), reverse=True)
                return projects
            return []
        except Exception as e:
            logger.warning("Failed to parse projects index: %s", e)
            return []

    async def get_project(self, project_id: str) -> dict | None:
        """Fetch project details including full notebook cells."""
        raw = await self._storage.get(f"project_{project_id}")
        if not raw:
            return None
        try:
            project = json.loads(raw)
            # Only reconstruct from notebook.ipynb if project record has no notebook_cells
            if not project.get("notebook_cells"):
                nb_raw = await self._storage.get(f"notebook_{project_id}")
                if nb_raw:
                    try:
                        nb_dict = json.loads(nb_raw)
                        project["notebook_cells"] = ipynb_to_cells(nb_dict)
                    except Exception:
                        pass
            return project
        except Exception as e:
            logger.error("Failed to load project %s: %s", project_id, e)
            return None

    async def create_project(
        self,
        name: str,
        primary_dataset: str = "",
        hardware: str = "CPU",
        initial_cells: list[dict] | None = None,
        schema_json: dict | None = None,
    ) -> dict:
        """Create a new project entity, initialize its .ipynb notebook, and update the index."""
        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        now = time.time()

        project = {
            "id": project_id,
            "name": name.strip() or f"Project {project_id[-4:]}",
            "primary_dataset": primary_dataset,
            "hardware": hardware,
            "created_at": now,
            "updated_at": now,
            "session_name": "",
            "schema_json": schema_json or {},
            "notebook_cells": initial_cells or [],
            "file_versions": [],
        }

        # Save project metadata, notebook .ipynb, and index entry
        await self.save_project(project)
        return project

    async def save_project(self, project: dict) -> None:
        """Save project state, convert notebook cells to .ipynb JSON format, and update index timestamp."""
        project_id = project["id"]
        project["updated_at"] = time.time()

        # Save notebook as standard Jupyter .ipynb format
        cells = project.get("notebook_cells", [])
        ipynb_doc = cells_to_ipynb(cells)
        await self._storage.set(
            f"notebook_{project_id}", json.dumps(ipynb_doc, indent=2)
        )

        # Save full project json (excluding massive duplicated cells to save memory)
        project_meta = dict(project)
        project_meta["notebook_cells"] = cells  # Kept in project record for fast load
        await self._storage.set(
            f"project_{project_id}", json.dumps(project_meta, default=str)
        )

        # Update summary in index
        projects = await self.list_projects()
        updated_index = []
        found = False
        for p in projects:
            if p["id"] == project_id:
                p["name"] = project["name"]
                p["primary_dataset"] = project.get("primary_dataset", "")
                p["hardware"] = project.get("hardware", "CPU")
                p["updated_at"] = project["updated_at"]
                p["session_name"] = project.get("session_name", "")
                p["cell_count"] = len(cells)
                found = True
            updated_index.append(p)
        if not found:
            updated_index.insert(
                0,
                {
                    "id": project["id"],
                    "name": project["name"],
                    "primary_dataset": project.get("primary_dataset", ""),
                    "hardware": project.get("hardware", "CPU"),
                    "created_at": project.get("created_at", time.time()),
                    "updated_at": project["updated_at"],
                    "session_name": project.get("session_name", ""),
                    "cell_count": len(cells),
                },
            )
        await self._storage.set(
            STORAGE_PROJECTS_INDEX, json.dumps(updated_index, default=str)
        )

    async def delete_project(self, project_id: str) -> None:
        """Permanently remove a project and its notebook."""
        await self._storage.delete(f"project_{project_id}")
        await self._storage.delete(f"notebook_{project_id}")

        try:
            from services.dataset_cache import delete_cache

            delete_cache(project_id)
        except Exception:
            pass

        projects = await self.list_projects()
        projects = [p for p in projects if p["id"] != project_id]
        await self._storage.set(
            STORAGE_PROJECTS_INDEX, json.dumps(projects, default=str)
        )

    async def add_file_version(
        self, project_id: str, file_name: str, remote_path: str, size: int | None = None
    ) -> dict:
        """Record or update a file version under the project."""
        project = await self.get_project(project_id)
        if not project:
            return {}
        versions = project.get("file_versions", [])

        # Check existing version
        existing = next((f for f in versions if f["name"] == file_name), None)
        if existing:
            existing["version"] = existing.get("version", 1) + 1
            existing["updated_at"] = time.time()
            existing["size"] = size or existing.get("size")
        else:
            versions.append(
                {
                    "name": file_name,
                    "remote_path": remote_path,
                    "version": 1,
                    "size": size,
                    "created_at": time.time(),
                    "updated_at": time.time(),
                }
            )
        project["file_versions"] = versions
        await self.save_project(project)
        return project
