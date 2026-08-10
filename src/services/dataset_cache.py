"""Dataset caching — local file cache for uploaded datasets."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from core.utils import get_temp_dir

logger = logging.getLogger(__name__)

_DATASETS_DIR = get_temp_dir() / "datasets"
_DATASETS_DIR.mkdir(parents=True, exist_ok=True)


def get_cached_path(project_id: str) -> Path | None:
    """Return the cached file path for a project, or None if not cached."""
    if not project_id:
        return None
    for ext in (".csv", ".xlsx", ".json", ".parquet", ".tsv"):
        p = _DATASETS_DIR / f"{project_id}{ext}"
        if p.exists():
            return p
    return None


def cache_file(project_id: str, source_path: str) -> Path:
    """Copy a file into the dataset cache."""
    src = Path(source_path)
    ext = src.suffix or ".csv"
    dest = _DATASETS_DIR / f"{project_id}{ext}"
    shutil.copy2(src, dest)
    logger.info("Cached dataset: %s -> %s", src.name, dest)
    return dest


def delete_cache(project_id: str) -> None:
    """Remove all cached files for a project."""
    if not project_id:
        return
    for p in _DATASETS_DIR.glob(f"{project_id}.*"):
        try:
            p.unlink()
            logger.info("Deleted cache: %s", p.name)
        except Exception as e:
            logger.warning("Failed to delete cache %s: %s", p, e)
