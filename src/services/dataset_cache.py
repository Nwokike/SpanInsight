"""Local dataset file cache — one cached file per project.

Copies the user's imported file to app-local storage so the dataset
can be reloaded silently on app restart or kernel reconnection without
re-prompting the user.
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from pathlib import Path

logger = logging.getLogger("dataset_cache")

CACHE_MAX_AGE_DAYS = 30
_CACHE_MAX_AGE_SEC = CACHE_MAX_AGE_DAYS * 24 * 60 * 60

_storage_env = os.getenv("FLET_APP_STORAGE_DATA")
if _storage_env:
    _DATASETS_DIR = Path(_storage_env) / "datasets"
else:
    # Dev fallback — mirrors what Flet sets as FLET_APP_STORAGE_DATA at runtime
    _DATASETS_DIR = Path(".flet") / "storage" / "data" / "datasets"


def _ensure_dir() -> None:
    """Create the datasets directory if it doesn't exist."""
    _DATASETS_DIR.mkdir(parents=True, exist_ok=True)


def cache_file(project_id: str, source_path: str) -> Path | None:
    """Copy the original imported file into local project cache.

    Returns the cache destination path, or None on failure.
    """
    if not project_id or not source_path:
        return None
    try:
        _ensure_dir()
        delete_cache(project_id)

        ext = Path(source_path).suffix.lower() or ".csv"
        dest = _DATASETS_DIR / f"{project_id}{ext}"
        shutil.copy(source_path, dest)
        logger.info("Cached dataset for project %s → %s", project_id, dest.name)
        return dest
    except Exception as e:
        logger.warning("Failed to cache dataset for project %s: %s", project_id, e)
        return None


def get_cached_path(project_id: str) -> Path | None:
    """Return the cached file path for a project, or None if not cached."""
    if not project_id:
        return None
    try:
        if not _DATASETS_DIR.exists():
            return None
        for f in _DATASETS_DIR.iterdir():
            if f.stem == project_id and f.is_file():
                f.touch()
                return f
    except Exception as e:
        logger.warning("Error checking cache for project %s: %s", project_id, e)
    return None


def delete_cache(project_id: str) -> None:
    """Delete the cached dataset file for a project (any extension)."""
    if not project_id:
        return
    try:
        if not _DATASETS_DIR.exists():
            return
        for f in _DATASETS_DIR.iterdir():
            if f.stem == project_id and f.is_file():
                f.unlink(missing_ok=True)
                logger.info("Deleted cached dataset: %s", f.name)
    except Exception as e:
        logger.warning("Failed to delete cache for project %s: %s", project_id, e)


def cleanup_stale() -> None:
    """Remove cached files that haven't been accessed in CACHE_MAX_AGE_DAYS."""
    try:
        if not _DATASETS_DIR.exists():
            return
        now = time.time()
        removed = 0
        for f in _DATASETS_DIR.iterdir():
            if not f.is_file():
                continue
            try:
                age = now - f.stat().st_mtime
                if age > _CACHE_MAX_AGE_SEC:
                    f.unlink(missing_ok=True)
                    removed += 1
            except Exception:
                pass
        if removed:
            logger.info("Stale cache cleanup: removed %d file(s)", removed)
    except Exception as e:
        logger.warning("Stale cache cleanup failed: %s", e)
