"""AI suggestion generator and autopilot next-step planner."""

from __future__ import annotations

import json
import logging
import re

from core.constants import TASK_SUGGEST
from services.ai.client import (
    call_gateway,
    extract_block_by_pattern,
    extract_content,
)

from .code_gen import COLAB_ENV_CONTEXT, compress_schema

logger = logging.getLogger(__name__)


def salvage_json_objects(text: str) -> list:
    """Extract every complete, well-formed JSON object from corrupt text.

    Scans for balanced ``{...}`` blocks (string/escape aware) and parses each
    individually, so one truncated object never destroys its neighbours.
    """
    items = []
    i = 0
    n = len(text)
    while i < n:
        start = text.find("{", i)
        if start == -1:
            break
        depth = 0
        j = start
        in_str = False
        esc = False
        end = -1
        while j < n:
            ch = text[j]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = j
                    break
            j += 1
        if end == -1:
            break  # truncated object - nothing after it can be complete either
        try:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict):
                items.append(obj)
        except ValueError:
            pass
        i = end + 1
    return items


def fallback_suggestions() -> list[dict]:
    """Safe fallbacks when the AI gateway is offline."""
    return [
        {
            "label": "Summary Statistics",
            "icon": "📊",
            "prompt": "Show descriptive statistics for all numeric columns as a styled table.",
        },
        {
            "label": "Distribution Plot",
            "icon": "📈",
            "prompt": "Plot histograms of all numeric columns in a grid layout.",
        },
        {
            "label": "Missing Values Audit",
            "icon": "🔍",
            "prompt": "Calculate percent of missing values in each column and render as a bar plot.",
        },
    ]


async def suggest(
    schema_json: dict,
    initial_description: str = "",
    analysis_context: str = "",
) -> list[dict]:
    """Fast context-aware suggestions - lean prompt matching describe_result speed."""
    system_prompt = (
        "You are an expert data intelligence consultant. Suggest exactly 3 distinct, "
        "deeply insightful analysis tracks. Do NOT repeat previous steps.\n\n"
        + COLAB_ENV_CONTEXT
        + "\nReturn ONLY a raw JSON array. Each object has EXACTLY these keys:\n"
        '- "label": concise title (max 5 words)\n'
        '- "icon": "emoji" (double-quoted)\n'
        '- "prompt": full analysis instruction for code generation\n'
    )

    ai_schema = dict(schema_json)
    for key in ("head", "tail", "describe", "summary"):
        ai_schema.pop(key, None)
    context_parts = [json.dumps(ai_schema, default=str)]

    if initial_description:
        context_parts.append(f"\nDataset: {initial_description}")

    if analysis_context:
        context_parts.append(f"\nDone (do NOT repeat):\n{analysis_context}")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n".join(context_parts)},
    ]

    data = None
    content = ""
    try:
        data = await call_gateway(TASK_SUGGEST, messages)
        content = extract_content(data)
        cleaned = extract_block_by_pattern(content, is_json=True)
        cleaned = re.sub(r'"icon"\s*:\s*([^"\s,{}]+)', r'"icon": "\1"', cleaned)
        cleaned = re.sub(
            r"\\U([0-9a-fA-F]{8})",
            lambda m: chr(int(m.group(1), 16)),
            cleaned,
        )
        try:
            suggestions = json.loads(cleaned, strict=False)
        except Exception:
            # Reasoning models sometimes emit a broken string mid-array -
            # salvage the complete objects instead of losing every suggestion.
            salvaged = salvage_json_objects(cleaned)
            salvaged = [s for s in salvaged if isinstance(s, dict) and s.get("label")]
            if salvaged:
                logger.info(
                    "Suggest JSON was malformed; salvaged %d complete item(s)",
                    len(salvaged),
                )
                return salvaged
            raise
        if isinstance(suggestions, list):
            return suggestions
        if isinstance(suggestions, dict) and suggestions.get("label"):
            # The extractor trimmed a corrupt array down to one valid object
            return [suggestions]
        return []
    except Exception as e:
        model_used = (
            data.get("_spaninsight_model_used", "unknown") if data else "unknown"
        )
        logger.error(
            "Suggest failed (model=%s): %s | raw_snippet=%s",
            model_used,
            e,
            content[:200] if content else "",
        )
        return fallback_suggestions()


async def plan_next_step(
    schema_json: dict, initial_description: str, analysis_history: list[dict]
) -> dict:
    """Autopilot planner: given all previous analysis results, decide the next step."""
    history_lines = []
    for i, entry in enumerate(analysis_history):
        status = "✓" if entry.get("success") else "✗"
        prompt = entry.get("prompt", "")[:80]
        desc = entry.get("description", "")[:100]
        history_lines.append(f"  {i + 1}. [{status}] {prompt} → {desc}")

    history_summary = "\n".join(history_lines) if history_lines else "No steps yet."

    system_prompt = (
        "You are an autonomous data analysis agent. Decide the NEXT step.\n\n"
        + COLAB_ENV_CONTEXT
        + "\nReturn ONLY a valid JSON object with these keys:\n"
        '- "prompt": the next analysis instruction (empty string if complete)\n'
        '- "is_complete": boolean\n'
        '- "reason": brief explanation\n'
    )

    compressed = compress_schema(schema_json)
    user_content = (
        f"Dataset Schema:\n{json.dumps(compressed, default=str)}\n\n"
        f"Dataset Overview: {initial_description}\n\n"
        f"Completed Steps ({len(analysis_history)} total):\n{history_summary}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        data = await call_gateway(TASK_SUGGEST, messages)
        content = extract_content(data)
        cleaned = extract_block_by_pattern(content, is_json=True)
        result = json.loads(cleaned, strict=False)
        if isinstance(result, dict) and "prompt" in result and "is_complete" in result:
            return result
        return {
            "prompt": "",
            "is_complete": True,
            "reason": "Planner returned invalid format.",
        }
    except Exception as e:
        logger.error("Plan next step failed: %s", e)
        return {"prompt": "", "is_complete": True, "reason": f"Planner error: {e}"}
