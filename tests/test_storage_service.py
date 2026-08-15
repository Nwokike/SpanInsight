"""Tests for StorageService file-backed split storage."""

from __future__ import annotations

import json

import pytest

from services.storage_service import StorageService


@pytest.mark.asyncio
async def test_storage_set_and_get(tmp_path):
    storage = StorageService(data_dir=str(tmp_path))
    await storage.set("test_key", "hello_world")
    val = await storage.get("test_key")
    assert val == "hello_world"


@pytest.mark.asyncio
async def test_storage_json_roundtrip(tmp_path):
    storage = StorageService(data_dir=str(tmp_path))
    payload = {"name": "SpanInsight", "version": 2, "features": ["colab", "surveys"]}
    await storage.set("config", json.dumps(payload))

    raw = await storage.get("config")
    loaded = json.loads(raw)
    assert loaded == payload


@pytest.mark.asyncio
async def test_storage_delete(tmp_path):
    storage = StorageService(data_dir=str(tmp_path))
    await storage.set("temp_key", "data")
    assert await storage.get("temp_key") == "data"

    await storage.delete("temp_key")
    assert await storage.get("temp_key") is None


@pytest.mark.asyncio
async def test_storage_notebook_save_load(tmp_path):
    storage = StorageService(data_dir=str(tmp_path))
    cells = [{"id": "c1", "type": "code", "source": "x = 10"}]
    await storage.save_notebook("session_abc", cells)

    loaded = await storage.load_notebook("session_abc")
    assert loaded == cells


def test_dataset_cache_lifecycle(tmp_path, monkeypatch):
    import services.dataset_cache as dcache

    cache_dir = tmp_path / "datasets"
    monkeypatch.setattr(dcache, "_DATASETS_DIR", cache_dir)

    # Create dummy source file
    src_file = tmp_path / "sales.csv"
    src_file.write_text("a,b,c\n1,2,3")

    # Cache file
    dest = dcache.cache_file("proj_123", str(src_file))
    assert dest is not None
    assert dest.exists()

    # Get cached file
    cached = dcache.get_cached_path("proj_123")
    assert cached == dest

    # Delete cache
    dcache.delete_cache("proj_123")
    assert dcache.get_cached_path("proj_123") is None
