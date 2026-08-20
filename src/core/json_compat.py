"""Fast JSON serialization via orjson with transparent stdlib fallback.

orjson is a Rust-backed JSON library, typically 3-10x faster than stdlib
``json`` for both serialization and deserialization. Flet publishes Android
and iOS wheels for it on ``pypi.flet.dev``, so it works on every platform we
build for (APK, AAB, desktop, web).

This module exposes drop-in helpers for the app's *local* hot paths -
project/notebook persistence, settings/history storage, and Colab schema/result
payload parsing - where payloads can reach multiple megabytes (notebook cells
carry base64 chart images).

Behavioral notes (verified against the installed orjson 3.12 API):
- ``orjson.dumps`` returns ``bytes`` and always emits UTF-8 (equivalent to
  ``ensure_ascii=False``); there is no ``indent=N``, only ``OPT_INDENT_2``.
- orjson converts NaN/Infinity to ``null`` on encode (stdlib emits the invalid
  ``NaN`` literal). ``null`` is valid JSON and matches the app's existing
  ``sanitize_output()`` / Colab ``_si_clean()`` NaN->None behavior.
- orjson is always strict on decode. stdlib ``json`` tolerates ``NaN``
  literals and (with ``strict=False``) control characters. To stay
  backward-compatible with files older stdlib writes may have left behind
  (e.g. ``NaN`` literals), every helper falls back to stdlib ``json`` on an
  orjson decode error.
- ``orjson.JSONDecodeError`` subclasses ``json.JSONDecodeError``, so existing
  ``except json.JSONDecodeError`` handlers still catch it.

Do NOT use these helpers for:
- AI gateway response parsing (those call sites rely on ``strict=False``).
- Code strings executed inside the Colab kernel (the remote kernel only has
  stdlib ``json`` available).
"""

from __future__ import annotations

import json as _stdlib_json

try:
    import orjson as _orjson
except ImportError:  # pragma: no cover - web/Pyodide without the wheel
    _orjson = None


def _stdlib_dumps_bytes(obj, default, indent: bool) -> bytes:
    kwargs: dict = {"ensure_ascii": False}
    if indent:
        kwargs["indent"] = 2
    if default is not None:
        kwargs["default"] = default
    return _stdlib_json.dumps(obj, **kwargs).encode("utf-8")


def fast_dumps_bytes(obj, default=None, indent: bool = False) -> bytes:
    """Serialize ``obj`` to UTF-8 JSON bytes, preferring orjson.

    Use this when writing directly to a file or byte sink to skip the
    str->bytes round trip entirely.
    """
    if _orjson is not None:
        try:
            option = _orjson.OPT_INDENT_2 if indent else None
            return _orjson.dumps(obj, default=default, option=option)
        except Exception:
            # Unsupported type without a `default` handler - fall back to
            # stdlib, which matches historical output for edge cases.
            pass
    return _stdlib_dumps_bytes(obj, default, indent)


def fast_dumps(obj, default=None, indent: bool = False) -> str:
    """Serialize ``obj`` to a JSON string, preferring orjson."""
    return fast_dumps_bytes(obj, default=default, indent=indent).decode("utf-8")


def fast_loads(raw):
    """Deserialize JSON from ``str`` or ``bytes``, preferring orjson.

    Falls back to stdlib ``json`` if orjson rejects the payload (e.g. it
    contains ``NaN``/``Infinity`` literals or control characters), preserving
    compatibility with data written by older stdlib-based code.
    """
    if _orjson is not None:
        try:
            return _orjson.loads(raw)
        except Exception:
            pass
    return _stdlib_json.loads(raw)


__all__ = ["fast_dumps", "fast_dumps_bytes", "fast_loads"]
