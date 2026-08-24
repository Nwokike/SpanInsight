"""App-side result serializer - wraps plain decoded data into typed payloads.

The heavy lifting happens kernel-side (see services/colab/introspection.py);
this module exists for the few app-side paths that hold raw decoded values
(e.g. extra entries alongside an embedded chart spec) and need a ``type`` tag
so ``build_serialized_result_visualizer`` can route them.
"""

from __future__ import annotations


def serialize_data(data) -> dict | None:
    """Convert arbitrary decoded result data into a typed visualizer payload."""
    if isinstance(data, dict):
        return {"type": "dict", "data": data}
    if isinstance(data, (list, tuple)):
        return {"type": "list", "data": list(data), "total_rows": len(data)}
    if data is None:
        return None
    return {"type": "scalar", "data": data}
