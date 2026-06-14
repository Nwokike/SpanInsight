"""Project management service — collaboration, creation, join, and sync.

Groups all analyses, forms, and reports under project scopes.
Synchronizes project state with D1/R2 gateway via Delta Sync.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import pendulum
import uuid


import flet as ft

from core.constants import API_BASE_URL
from core.state import state
from services.api_client import get_client, request_with_retry
from services.bip39_words import BIP39_WORDS

logger = logging.getLogger(__name__)

# Key under which all local projects dict is stored in StorageService
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
                    raise ValueError("Projects data is not a dict")
            except (json.JSONDecodeError, ValueError) as parse_err:
                logger.error("Corrupt projects JSON, resetting: %s", parse_err)
                projects = {}

            state.user_projects = projects

            if not projects:
                logger.info("No projects found. Generating default workspace...")
                default_proj = await self.create_local_project("My Workspace")
                active_id = default_proj["id"]

                import asyncio

                asyncio.create_task(self.sync_project(active_id))

            if not active_id or active_id not in state.user_projects:
                active_id = next(iter(state.user_projects.keys()))

            state.active_project_id = active_id
            await self._storage.set(STORAGE_ACTIVE_PROJECT_ID, active_id)
            return active_id

        except Exception as e:
            logger.error("Failed to initialize projects: %s", e)
            return ""

    async def create_local_project(self, title: str, description: str = "") -> dict:
        """Create a new offline-ready project locally with a recovery phrase."""
        proj_uuid = str(uuid.uuid4())
        phrase = self.uuid_to_phrase(proj_uuid)
        phrase_hash = self.phrase_to_hash(phrase)

        # Temp local ID until registered/synced with server
        temp_id = "loc_" + proj_uuid[:8]

        project = {
            "id": temp_id,
            "title": title,
            "description": description,
            "phrase": phrase,
            "phrase_hash": phrase_hash,
            "dataset_fingerprint": "",  # Set during file import
            "current_df_name": "",
            "current_file_path": "",
            "analysis_blocks": [],
            "user_reports": [],
            "forms": [],
            "synced_at": 0,
        }

        state.user_projects[temp_id] = project
        await self._persist_local_projects()
        return project

    async def create_project(self, title: str, description: str = "") -> dict:
        """Register a new project on the Cloudflare gateway."""
        # 1. Setup local project state
        proj = await self.create_local_project(title, description)
        temp_id = proj["id"]

        payload = {
            "phrase_hash": proj["phrase_hash"],
            "title": proj["title"],
            "description": proj["description"],
            "dataset_fingerprint": proj.get("dataset_fingerprint", ""),
            "settings_json": {},
        }

        try:
            resp = await request_with_retry(
                "POST",
                f"{API_BASE_URL}/projects",
                json=payload,
                timeout=10.0,
            )
            if resp.status_code == 201:
                data = resp.json()
                server_id = data["id"]

                # Replace local temporary ID with server generated Secure ID
                state.user_projects.pop(temp_id, None)
                proj["id"] = server_id
                proj["synced_at"] = pendulum.now().timestamp()
                state.user_projects[server_id] = proj

                state.active_project_id = server_id
                await self._storage.set(STORAGE_ACTIVE_PROJECT_ID, server_id)
                await self._persist_local_projects()
                logger.info("Project registered in gateway. ID: %s", server_id)
                return proj
        except Exception as e:
            logger.warning(
                "Could not register project in gateway: %s. Keeping local.", e
            )

        # Fallback: Set active locally
        state.active_project_id = temp_id
        await self._storage.set(STORAGE_ACTIVE_PROJECT_ID, temp_id)
        return proj

    async def sync_project(self, project_id: str) -> bool:
        """Delta Sync: Upload ONLY new, unsynced analysis blocks to the gateway."""
        proj = state.user_projects.get(project_id)
        if not proj:
            return False

        # If project is still local, attempt to register it first
        if project_id.startswith("loc_"):
            logger.info("Attempting to register local project '%s'...", proj["title"])
            payload = {
                "phrase_hash": proj["phrase_hash"],
                "title": proj["title"],
                "description": proj["description"],
                "dataset_fingerprint": proj.get("dataset_fingerprint", ""),
                "settings_json": {},
            }
            try:
                resp = await request_with_retry(
                    "POST",
                    f"{API_BASE_URL}/projects",
                    json=payload,
                    timeout=10.0,
                )
                if resp.status_code == 201:
                    data = resp.json()
                    server_id = data["id"]

                    state.user_projects.pop(project_id, None)
                    proj["id"] = server_id
                    proj["synced_at"] = pendulum.now().timestamp()
                    state.user_projects[server_id] = proj

                    if state.active_project_id == project_id:
                        state.active_project_id = server_id
                        await self._storage.set(STORAGE_ACTIVE_PROJECT_ID, server_id)
                    project_id = server_id
                    logger.info(
                        "Local project successfully registered. ID: %s", server_id
                    )
                else:
                    return False
            except Exception as e:
                logger.warning("Could not register local project in gateway: %s", e)
                return False

        # Push unsynced blocks
        success_count = 0
        for block in proj.get("analysis_blocks", []):
            if block.get("type") == "initial" or block.get("failed"):
                continue

            if not block.get("is_synced", False):
                payload = {
                    "id": block.get("id"),
                    "prompt": block.get("prompt", ""),
                    "code": block.get("code", ""),
                    "description": block.get("description", ""),
                }
                try:
                    resp = await request_with_retry(
                        "POST",
                        f"{API_BASE_URL}/projects/{project_id}/blocks",
                        json=payload,
                        timeout=10.0,
                    )
                    if resp.status_code in (201, 200):
                        block["is_synced"] = True
                        success_count += 1
                except Exception as e:
                    logger.warning("Failed to sync block %s: %s", block.get("id"), e)

        if success_count > 0:
            proj["synced_at"] = pendulum.now().timestamp()
            await self._persist_local_projects()
            logger.info("Delta Sync: Pushed %d new blocks.", success_count)
            return True
        return True

    async def join_project_by_phrase(self, phrase: str) -> dict | None:
        """Join a collaborative project using its 12-word seed phrase."""
        phrase = phrase.strip().lower()
        phrase_hash = self.phrase_to_hash(phrase)

        try:
            client = get_client()
            resp = await client.get(
                f"{API_BASE_URL}/projects/restore",
                params={"phrase_hash": phrase_hash},
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                proj_data = {
                    "id": data["id"],
                    "title": data["title"],
                    "description": data["description"],
                    "phrase": phrase,
                    "phrase_hash": phrase_hash,
                    "dataset_fingerprint": data.get("dataset_fingerprint", ""),
                    "current_df_name": "",
                    "current_file_path": "",
                    "analysis_blocks": [],
                    "user_reports": [],
                    "forms": [],
                    "synced_at": 0,  # 0 forces a full pull of all blocks
                }

                state.user_projects[data["id"]] = proj_data
                state.active_project_id = data["id"]
                await self._storage.set(STORAGE_ACTIVE_PROJECT_ID, data["id"])

                # Immediately pull all historical blocks for this newly joined project
                await self.pull_project(data["id"])

                logger.info("Successfully joined project '%s' by phrase", data["title"])
                return state.user_projects[data["id"]]
            else:
                logger.warning(
                    "Join project by phrase failed: HTTP %d", resp.status_code
                )
        except Exception as e:
            logger.error("Failed to restore project by phrase: %s", e)
        return None

    async def pull_project(self, project_id: str) -> bool | str:
        """Delta Pull: Fetch remote project blocks missing from the local UI.

        Returns:
            "local"   - project is offline-only
            "deleted" - project has been deleted from gateway
            True      - successfully pulled new blocks
            False     - offline or no new updates
        """
        if project_id.startswith("loc_"):
            return "local"

        proj = state.user_projects.get(project_id)
        if not proj:
            return False

        try:
            client = get_client()

            # Format last synced time to ISO 8601 for the query
            last_sync = proj.get("synced_at", 0)
            since_iso = (
                pendulum.from_timestamp(last_sync).strftime("%Y-%m-%dT%H:%M:%SZ")
                if last_sync > 0
                else "1970-01-01T00:00:00Z"
            )

            resp = await client.get(
                f"{API_BASE_URL}/projects/{project_id}/blocks",
                params={"since": since_iso},
                timeout=8.0,
            )

            if resp.status_code == 200:
                data = resp.json()
                new_blocks = data.get("blocks", [])

                if not new_blocks:
                    return False

                existing_ids = {b.get("id") for b in proj.get("analysis_blocks", [])}
                added = False

                for nb in new_blocks:
                    if nb["id"] not in existing_ids:
                        # Reconstruct the block for the UI
                        new_block = {
                            "id": nb["id"],
                            "type": "analysis",
                            "prompt": nb["prompt"],
                            "code": nb["code"],
                            "description": nb["description"],
                            "figure_png": None,  # Regenerated locally later
                            "result": "",  # Regenerated locally later
                            "stdout": "",  # Regenerated locally later
                            "suggestions": [],
                            "pinned": False,
                            "failed": False,
                            "is_synced": True,  # Already on server
                            "needs_execution": True,  # CRITICAL: Flags UI to run Python code
                        }
                        proj["analysis_blocks"].append(new_block)
                        added = True

                if added:
                    proj["synced_at"] = pendulum.now().timestamp()
                    await self._persist_local_projects()
                    logger.info(
                        "Delta Pull: Appended %d remote blocks.", len(new_blocks)
                    )
                    return True
                return False

            elif resp.status_code == 404:
                logger.warning("Project %s not found on server (deleted).", project_id)
                return "deleted"
        except Exception as e:
            logger.warning("Failed to pull project blocks %s: %s", project_id, e)
        return False

    async def rename_project(self, project_id: str, new_title: str) -> bool:
        """Rename active project locally.
        (Note: In V2 Delta Sync, project metadata updates are decoupled to save bandwidth.
        Title is strictly local until a re-register.)
        """
        proj = state.user_projects.get(project_id)
        if not proj:
            return False
        proj["title"] = new_title
        await self._persist_local_projects()
        return True

    async def delete_project(self, project_id: str) -> bool:
        """Remove a project locally and trigger gateway cascade delete."""
        from services import dataset_cache

        dataset_cache.delete_cache(project_id)
        state.user_projects.pop(project_id, None)
        await self._persist_local_projects()

        if not project_id.startswith("loc_"):
            try:
                client = get_client()
                await client.delete(
                    f"{API_BASE_URL}/projects/{project_id}",
                    timeout=10.0,
                )
            except Exception as e:
                logger.warning("Delete project from gateway failed: %s", e)

        # Update active project reference if deleted project was active
        if state.active_project_id == project_id:
            if state.user_projects:
                state.active_project_id = next(iter(state.user_projects.keys()))
            else:
                await self.create_local_project("My Workspace")
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

    def _serialize_local_project(self, proj: dict) -> dict:
        """Prepare project data dict for local JSON serialization (encoding Base64).
        Note: This is strictly for local device saving to prevent image loss on restart.
        """
        import pandas as pd

        copied = json.loads(
            json.dumps(
                proj,
                default=lambda x: (
                    x.to_dict() if isinstance(x, pd.DataFrame) else str(x)
                ),
            )
        )

        for b in copied.get("analysis_blocks", []):
            orig_block = next(
                (
                    ob
                    for ob in proj.get("analysis_blocks", [])
                    if ob.get("id") == b.get("id")
                    or ob.get("prompt") == b.get("prompt")
                ),
                None,
            )
            if orig_block and orig_block.get("figure_png"):
                b["figure_png_b64"] = base64.b64encode(orig_block["figure_png"]).decode(
                    "utf-8"
                )
            b.pop("figure_png", None)
            b.pop("figure", None)

        return copied

    def uuid_to_phrase(self, user_uuid: str) -> str:
        """Convert a 128-bit UUID integer to a 12-word recovery mnemonic."""
        u_int = uuid.UUID(user_uuid).int
        words = []
        temp_val = u_int
        for _ in range(12):
            idx = temp_val % 2048
            words.append(BIP39_WORDS[idx])
            temp_val //= 2048
        return " ".join(words)

    @staticmethod
    def phrase_to_hash(phrase: str) -> str:
        """SHA-256 hash of the recovery phrase."""
        return hashlib.sha256(phrase.strip().lower().encode()).hexdigest()[:32]
