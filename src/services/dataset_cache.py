"""Local dataset file cache — one cached file per project.

Copies the user's imported file to app-local storage so the DataFrame
can be reloaded silently on app restart without re-prompting the user.

Stale caches (not accessed for CACHE_MAX_AGE_DAYS) are purged on startup
to prevent storage bloat on mobile devices.
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Cached datasets older than this are auto-deleted on startup
CACHE_MAX_AGE_DAYS = 7
_CACHE_MAX_AGE_SEC = CACHE_MAX_AGE_DAYS * 24 * 60 * 60

# Resolve storage root (same logic as storage_service.py)
_storage_env = os.getenv("FLET_APP_STORAGE_DATA")
if _storage_env:
    _DATASETS_DIR = Path(_storage_env) / "datasets"
else:
    _DATASETS_DIR = Path.home() / ".spaninsight" / "datasets"


def _ensure_dir() -> None:
    """Create the datasets directory if it doesn't exist."""
    _DATASETS_DIR.mkdir(parents=True, exist_ok=True)


def cache_file(project_id: str, source_path: str) -> Path | None:
    """Copy the original imported file into the local cache.

    Any existing cache for this project is deleted first so
    there is always at most one cached file per project.

    Returns the cache destination path, or None on failure.
    """
    try:
        _ensure_dir()
        # Delete any previous cache for this project
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
    """Return the cached file path for a project, or None if not cached.

    Searches for any file matching ``{project_id}.*`` since we preserve
    the original extension.  Also touches the file's access time so the
    stale-cache cleanup knows it was recently used.
    """
    try:
        if not _DATASETS_DIR.exists():
            return None
        for f in _DATASETS_DIR.iterdir():
            if f.stem == project_id and f.is_file():
                # Touch access time to prevent stale cleanup
                f.touch()
                return f
    except Exception as e:
        logger.warning("Error checking cache for project %s: %s", project_id, e)
    return None


def delete_cache(project_id: str) -> None:
    """Delete the cached dataset file for a project (any extension)."""
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
    """Remove cached files that haven't been accessed in CACHE_MAX_AGE_DAYS.

    Called once on app startup to prevent storage bloat.
    """
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
                    logger.info(
                        "Purged stale cache: %s (%.0f days old)", f.name, age / 86400
                    )
            except Exception:
                pass
        if removed:
            logger.info("Stale cache cleanup: removed %d file(s)", removed)
    except Exception as e:
        logger.warning("Stale cache cleanup failed: %s", e)
