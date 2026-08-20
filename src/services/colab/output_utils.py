"""Parsing helpers for Colab kernel execution outputs.

The real contract (colab_cli 0.6.0, ``ColabRuntime.execute_code``) returns a
LIST of jupyter-nbformat-style output dicts:

    [{"output_type": "stream", "name": "stdout", "text": "..."},
     {"output_type": "execute_result", "data": {"text/plain": "...", "image/png": "<b64>"}},
     {"output_type": "display_data", "data": {...}},
     {"output_type": "error", "ename": "...", "evalue": "...", "traceback": [...]}]

Historically some call sites assumed a ``{"outputs": [...]}`` dict envelope -
that shape never comes back from the runtime. Every helper here normalizes
both shapes so no call site ever guesses again.
"""

from __future__ import annotations

import logging

from core.json_compat import fast_loads

logger = logging.getLogger("ColabOutputUtils")


def normalize_outputs(outputs) -> list[dict]:
    """Return a list of output dicts from any historical shape."""
    if not outputs:
        return []
    if isinstance(outputs, dict):
        return list(outputs.get("outputs", []))
    if isinstance(outputs, (list, tuple)):
        return list(outputs)
    return [outputs]


def extract_text(outputs) -> str:
    """Concatenate all textual content (stream + execute_result/display_data text/plain)."""
    parts: list[str] = []
    for out in normalize_outputs(outputs):
        otype = out.get("output_type") or out.get("type", "")
        if otype == "stream":
            text = out.get("text", "")
            parts.append(text if isinstance(text, str) else "".join(text))
        elif otype in ("execute_result", "display_data"):
            data = out.get("data", {}) or {}
            plain = data.get("text/plain", "")
            parts.append(plain if isinstance(plain, str) else "".join(plain))
    return "".join(parts)


def extract_error_text(outputs) -> str | None:
    """Return a human-readable description of the first error output, if any."""
    for out in normalize_outputs(outputs):
        otype = out.get("output_type") or out.get("type", "")
        if otype == "error":
            trace = out.get("traceback", [])
            trace_text = "\n".join(
                t if isinstance(t, str) else "".join(t) for t in trace
            )
            return f"{out.get('ename', 'Error')}: {out.get('evalue', '')}" + (
                f"\n{trace_text}" if trace_text else ""
            )
        if otype == "stream":
            text = str(out.get("text", ""))
            if "Traceback (most recent call last)" in text or any(
                err in text
                for err in (
                    "NameError:",
                    "SyntaxError:",
                    "TypeError:",
                    "ValueError:",
                    "AttributeError:",
                    "ModuleNotFoundError:",
                    "ImportError:",
                    "KeyError:",
                    "IndexError:",
                    "ZeroDivisionError:",
                    "FileNotFoundError:",
                )
            ):
                return text.strip()
    return None


def extract_marker_payload(raw_text: str, marker: str) -> str | None:
    """Extract the payload printed between __<marker>_START__ / __<marker>_END__ fences."""
    start_fence = f"__{marker}_START__"
    end_fence = f"__{marker}_END__"
    if start_fence not in raw_text:
        return None
    payload = raw_text.split(start_fence, 1)[1]
    if end_fence in payload:
        payload = payload.split(end_fence, 1)[0]
    return payload.strip()


def parse_marker_json(outputs, marker: str) -> tuple[dict | None, str | None]:
    """Parse a JSON payload fenced by the given marker from execution outputs.

    Returns ``(payload_dict, error_message)`` - exactly one is non-None on
    success/failure; both None when the marker was never printed.
    """
    raw_text = extract_text(outputs)
    payload = extract_marker_payload(raw_text, marker)
    if payload is None:
        return None, None
    try:
        parsed = fast_loads(payload)
    except ValueError as ex:
        return None, f"Malformed {marker} payload: {ex}"
    if isinstance(parsed, dict):
        return parsed, None
    return None, f"Unexpected {marker} payload type: {type(parsed).__name__}"
