"""Platform-resilient key-value storage service.

Uses a split local JSON file approach for desktop/mobile persistence
(separating heavy history from light settings), and falls back to
``page.client_storage`` when running on the web.

v2: Replaced msgspec with stdlib json. Added notebook save/load.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path

import flet as ft

logger = logging.getLogger(__name__)

# Use FLET_APP_STORAGE_DATA when set by Flet at runtime (Android: app private data dir)
# Dev fallback mirrors the .flet/storage/data/ folder Flet creates locally
storage_env = os.getenv("FLET_APP_STORAGE_DATA")
if storage_env:
    _STORAGE_DIR = Path(storage_env)
else:
    _STORAGE_DIR = Path(".flet") / "storage" / "data"

_SETTINGS_FILE = _STORAGE_DIR / "settings.json"
_HISTORY_FILE = _STORAGE_DIR / "history.json"

_WRITE_DEBOUNCE_SEC = 1.0


class StorageService:
    def __init__(self, page: ft.Page | None = None, data_dir: str | Path | None = None):
        self._page = page
        self._settings: dict[str, str] = {}
        self._history: dict[str, str] = {}
        self._lock = asyncio.Lock()

        self._settings_dirty = False
        self._history_dirty = False

        self._last_write: float = 0.0
        self._pending_write_task: asyncio.Task | None = None

        if data_dir:
            self._storage_dir = Path(data_dir)
        else:
            self._storage_dir = _STORAGE_DIR

        self._settings_file = self._storage_dir / "settings.json"
        self._history_file = self._storage_dir / "history.json"

        self._is_web = bool(getattr(page, "session_id", None)) if page else False

        if self._is_web:
            logger.info("StorageService: running on web - using client_storage")
            self._load_web()
        else:
            logger.info("StorageService: running on native - using split local files")
            self._load()

    def _is_history_key(self, key: str) -> bool:
        """Determines if a key contains heavy analytical data vs lightweight settings."""
        return key.startswith(("report_", "history_", "analysis_", "notebook_"))

    # ── Web/Pyodide helpers ──────────────────────────────────────────

    def _load_web(self) -> None:
        try:
            if self._page:
                # Synchronous fallback: split local files if available, otherwise initialized empty
                self._load()
        except Exception as e:
            logger.warning("StorageService._load_web failed: %s", e)
            self._settings, self._history = {}, {}

    def _save_now_web(self) -> None:
        try:
            if self._page:
                prefs = ft.SharedPreferences()
                if self._settings_dirty:
                    self._page.run_task(
                        prefs.set, "spaninsight_settings", json.dumps(self._settings)
                    )
                    self._settings_dirty = False
                if self._history_dirty:
                    self._page.run_task(
                        prefs.set, "spaninsight_history", json.dumps(self._history)
                    )
                    self._history_dirty = False
            self._last_write = time.monotonic()
        except Exception as e:
            logger.warning("StorageService._save_now_web failed: %s", e)

    # ── Native file helpers ──────────────────────────────────────────

    def _load(self) -> None:
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._settings = self._load_file(self._settings_file, "settings")
        self._history = self._load_file(self._history_file, "history")

    @staticmethod
    def _load_file(path: Path, label: str) -> dict:
        """Read and decode a JSON file, recovering from corruption gracefully."""
        if not path.exists():
            return {}
        try:
            raw = path.read_bytes()
            if not raw:
                return {}
            return json.loads(raw)
        except Exception as e:
            logger.warning("Storage %s corrupted (%s) - resetting", label, e)
            try:
                backup = path.with_suffix(f".{label}.corrupted")
                path.rename(backup)
                logger.info("Backed up corrupted %s to %s", label, backup)
            except Exception:
                path.unlink(missing_ok=True)
            return {}

    def _write_files_sync(
        self, settings_copy, history_copy, write_settings, write_history
    ) -> None:
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        if write_settings:
            self._settings_file.write_bytes(
                json.dumps(settings_copy, ensure_ascii=False).encode("utf-8"),
            )
        if write_history:
            self._history_file.write_bytes(
                json.dumps(history_copy, ensure_ascii=False).encode("utf-8"),
            )

    async def _save_now_async(self) -> None:
        if self._is_web:
            self._save_now_web()
            return
        try:
            write_settings = self._settings_dirty
            write_history = self._history_dirty

            if write_settings or write_history:
                settings_copy = dict(self._settings) if write_settings else None
                history_copy = dict(self._history) if write_history else None

                await asyncio.to_thread(
                    self._write_files_sync,
                    settings_copy,
                    history_copy,
                    write_settings,
                    write_history,
                )

                if write_settings:
                    self._settings_dirty = False
                if write_history:
                    self._history_dirty = False

            self._last_write = time.monotonic()
        except Exception as e:
            logger.warning(
                "StorageService._save_now_async failed, falling back to web: %s", e
            )
            self._save_now_web()

    def _save_now(self) -> None:
        try:
            _STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            if self._settings_dirty:
                _SETTINGS_FILE.write_bytes(
                    json.dumps(self._settings, ensure_ascii=False).encode("utf-8"),
                )
                self._settings_dirty = False
            if self._history_dirty:
                _HISTORY_FILE.write_bytes(
                    json.dumps(self._history, ensure_ascii=False).encode("utf-8"),
                )
                self._history_dirty = False
            self._last_write = time.monotonic()
        except Exception as e:
            logger.warning("StorageService._save failed, falling back to web: %s", e)
            self._save_now_web()

    def _schedule_write(self) -> None:
        elapsed = time.monotonic() - self._last_write
        if elapsed >= _WRITE_DEBOUNCE_SEC:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._save_now_async())
            except RuntimeError:
                self._save_now() if not self._is_web else self._save_now_web()
        else:
            if self._pending_write_task is None or self._pending_write_task.done():
                try:
                    loop = asyncio.get_event_loop()
                    self._pending_write_task = loop.create_task(self._deferred_write())
                except RuntimeError:
                    self._save_now() if not self._is_web else self._save_now_web()

    async def _deferred_write(self) -> None:
        await asyncio.sleep(_WRITE_DEBOUNCE_SEC)
        if self._settings_dirty or self._history_dirty:
            await self._save_now_async()

    # ── Public API ───────────────────────────────────────────────────

    async def get(self, key: str) -> str | None:
        async with self._lock:
            if self._is_history_key(key):
                return self._history.get(key)
            return self._settings.get(key)

    async def set(self, key: str, value: str) -> None:
        async with self._lock:
            if self._is_history_key(key):
                self._history[key] = value
                self._history_dirty = True
            else:
                self._settings[key] = value
                self._settings_dirty = True
            self._schedule_write()

    async def delete(self, key: str) -> None:
        async with self._lock:
            if self._is_history_key(key):
                self._history.pop(key, None)
                self._history_dirty = True
            else:
                self._settings.pop(key, None)
                self._settings_dirty = True
            self._schedule_write()

    async def flush(self) -> None:
        async with self._lock:
            if self._settings_dirty or self._history_dirty:
                await (
                    self._save_now_async()
                ) if not self._is_web else self._save_now_web()

    # ── Notebook persistence ─────────────────────────────────────────

    async def save_notebook(self, session_name: str, cells: list[dict]) -> None:
        """Save notebook cells for a given session."""
        key = f"notebook_{session_name}"
        await self.set(key, json.dumps(cells, ensure_ascii=False))

    async def load_notebook(self, session_name: str) -> list[dict]:
        """Load notebook cells for a given session."""
        key = f"notebook_{session_name}"
        raw = await self.get(key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError, TypeError:
                return []
        return []
