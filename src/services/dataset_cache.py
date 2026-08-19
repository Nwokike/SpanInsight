"""Local dataset file cache - one cached file per project.

Copies the user's imported file to app-local storage so the dataset
can be reloaded silently on app restart or kernel reconnection without
re-prompting the user.
"""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from core.storage_patch import resolve_storage_dir

logger = logging.getLogger("dataset_cache")

CACHE_MAX_AGE_DAYS = 30
_CACHE_MAX_AGE_SEC = CACHE_MAX_AGE_DAYS * 24 * 60 * 60

_DATASETS_DIR = resolve_storage_dir() / "datasets"


def _ensure_dir() -> None:
    """Create the datasets directory if it doesn't exist."""
    _DATASETS_DIR.mkdir(parents=True, exist_ok=True)


def cache_file(project_id: str, source_path: str) -> Path | None:
    """Copy the original imported file into local project cache preserving original filename.

    Returns the cache destination path, or None on failure.
    """
    if not source_path:
        return None
    key = project_id or "_default"
    try:
        _ensure_dir()
        delete_cache(key)

        proj_dir = _DATASETS_DIR / key
        proj_dir.mkdir(parents=True, exist_ok=True)

        filename = Path(source_path).name
        dest = proj_dir / filename
        shutil.copy(source_path, dest)
        logger.info("Cached dataset for project %s → %s", key, dest.name)
        return dest
    except Exception as e:
        logger.warning("Failed to cache dataset for project %s: %s", key, e)
        return None


def get_cached_path(project_id: str) -> Path | None:
    """Return the cached file path for a project, or None if not cached."""
    key = project_id or "_default"
    try:
        if not _DATASETS_DIR.exists():
            return None
        proj_dir = _DATASETS_DIR / key
        if proj_dir.exists() and proj_dir.is_dir():
            for f in proj_dir.iterdir():
                if f.is_file():
                    f.touch()
                    return f
        # Backward-compatible fallback for flat cache files
        for f in _DATASETS_DIR.iterdir():
            if f.stem == key and f.is_file():
                f.touch()
                return f
    except Exception as e:
        logger.warning("Error checking cache for project %s: %s", key, e)
    return None


def delete_cache(project_id: str) -> None:
    """Delete the cached dataset file for a project."""
    key = project_id or "_default"
    try:
        if not _DATASETS_DIR.exists():
            return
        proj_dir = _DATASETS_DIR / key
        if proj_dir.exists() and proj_dir.is_dir():
            shutil.rmtree(proj_dir, ignore_errors=True)
            logger.info("Deleted cached dataset directory: %s", proj_dir.name)
        for f in _DATASETS_DIR.iterdir():
            if f.stem == key and f.is_file():
                f.unlink(missing_ok=True)
                logger.info("Deleted legacy cached dataset: %s", f.name)
    except Exception as e:
        logger.warning("Failed to delete cache for project %s: %s", key, e)


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
