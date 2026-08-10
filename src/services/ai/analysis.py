"""Core AI data analysis, generation, and orchestration."""

from __future__ import annotations

import json
import logging
import re

import httpx

from core.constants import TASK_CODE, TASK_INTERPRET, TASK_SUGGEST

from .client import call_gateway, extract_block_by_pattern, extract_content
from .vision import analyze_image

logger = logging.getLogger(__name__)

_COLAB_ENV_CONTEXT = (
    "EXECUTION ENVIRONMENT: Google Colab (Python 3.10+, Ubuntu).\\n"
    "PRE-INSTALLED: pandas, numpy, matplotlib, seaborn, scikit-learn, scipy,\\n"
    "  statsmodels, plotly, tensorflow, torch, transformers, PIL/Pillow,\\n"
    "  and all Python stdlib modules.\\n"
    "You can install additional packages with !pip install <package>.\\n"
    "The user's data files are in /content/. Use pandas to load them.\\n"
)

_EXEC_RULES = (
    "EXECUTION RULES:\\n"
    "- If a DataFrame `df` exists in the session, use it. Otherwise load data from /content/.\\n"
    "- Always .dropna() or .fillna() before algebraic/statistical operations.\\n"
    "- Plotting: always create figures with plt.figure() or plt.subplots(). Do NOT call plt.savefig().\\n"
    "- Assign key results to a variable named `result`.\\n"
    "- Do NOT print human-readable text summaries. Only output raw tables, statistics, or plots.\\n"
    "- Keep code efficient and focused on the user's request.\\n"
    "- Return only executable Python code, no remarks.\\n"
)


async def describe_dataset(schema_json: dict) -> str:
    """AI reads the schema and produces a concise dataset overview."""
    system_prompt = (
        "You are an expert data science director. Given a comprehensive dataset schema "
        "with structural details and distribution statistics, provide a professional, "
        "highly concise overview of what the data signifies and the macro domains it represents. "
        "Do NOT use any markdown (no bold, no italics, no bullet points, no headers). "
        "Write strictly as clear, plain-text prose, limited to at most 2 to 3 sentences."
    )
    ai_schema = dict(schema_json)
    ai_schema.pop("head", None)
    ai_schema.pop("tail", None)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(ai_schema, default=str)},
    ]
    try:
        data = await call_gateway(TASK_INTERPRET, messages)
        desc = extract_content(data)
        if desc:
            logger.info("Block 0 describe: %s", desc[:80])
            return desc
        return "Dataset loaded successfully."
    except Exception as e:
        logger.error("Describe dataset failed: %s", e)
        return "Dataset loaded. AI description unavailable."


async def describe_result(initial_description: str, latest_result: dict) -> str:
    """AI describes what a specific analysis result shows."""
    system_prompt = (
        "You are an expert data analyst. Describe what this specific data analysis "
        "execution result establishes. Interpret anomalies, specific distributions, exact "
        "numerical indices, and structural trends. "
        "Do NOT use any markdown (no bold, no italics, no bullet points, no headers). "
        "Write strictly as clear, plain-text analytical findings, limited to at most 2 to 3 sentences."
    )
    result_text = (
        f"Dataset: {initial_description}\n\n"
        f"Analysis Prompt: {latest_result.get('prompt', '')}\n"
        f"Executed Code:\n{latest_result.get('code', '')}\n\n"
        f"Standard Output Logs:\n{latest_result.get('stdout', '')}\n"
        f"Returned Value String:\n{latest_result.get('result', '')}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": result_text},
    ]
    try:
        data = await call_gateway(TASK_INTERPRET, messages)
        content = extract_content(data)
        if content:
            logger.info("Block N describe: %s", content[:80])
            return content.strip()
        return "Analysis completed."
    except Exception as e:
        logger.error("Describe result failed: %s", e)
        return "Analysis completed."


async def suggest(
    schema_json: dict,
    initial_description: str = "",
    analysis_context: str = "",
) -> list[dict]:
    """Fast context-aware suggestions — lean prompt matching describe_result speed."""
    system_prompt = (
        "You are an expert data intelligence consultant. Suggest exactly 3 distinct, "
        "deeply insightful analysis tracks. Do NOT repeat previous steps.\n\n"
        + _COLAB_ENV_CONTEXT
        + "\nReturn ONLY a raw JSON array. Each object has EXACTLY these keys:\n"
        '- "label": concise title (max 5 words)\n'
        '- "icon": "emoji" (double-quoted)\n'
        '- "prompt": full analysis instruction for code generation\n'
    )

    ai_schema = dict(schema_json)
    for key in ("head", "tail", "describe"):
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
        suggestions = json.loads(cleaned)
        if isinstance(suggestions, list):
            return suggestions
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


def _compress_schema(schema_json: dict) -> dict:
    """Optimize LLM context usage while maintaining high code quality.

    Pares down the massive head (from 20 rows to 2 rows) and removes the tail completely.
    This preserves the exact value formatting context needed for excellent code quality,
    but saves thousands of tokens.
    """
    compressed = dict(schema_json)
    if "head" in compressed and isinstance(compressed["head"], list):
        compressed["head"] = compressed["head"][:2]
    compressed.pop("tail", None)
    return compressed


async def generate_code(
    prompt: str, schema_json: dict, analysis_context: str = ""
) -> str:
    """Generate executable Python code for the user's analysis request."""
    context_section = ""
    if analysis_context:
        context_section = (
            f"\n\nPrevious Analysis Context (do NOT repeat):\n{analysis_context}\n"
        )

    compressed = _compress_schema(schema_json)
    system_prompt = (
        "You are an expert Python data engineer. Generate optimal, safe code to analyze `df`.\n\n"
        + _COLAB_ENV_CONTEXT
        + _EXEC_RULES
        + f"\nComplete Dataset Schema:\n{json.dumps(compressed, default=str)}"
        f"{context_section}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    try:
        data = await call_gateway(TASK_CODE, messages)
        content = extract_content(data)
        code = extract_block_by_pattern(content, is_json=False)
        return code
    except httpx.HTTPError as e:
        logger.error("Network error during code generation: %s", e)
        raise
    except Exception as e:
        logger.error("Code generation failed: %s", e)
        return ""


async def generate_corrected_code(
    prompt: str,
    bad_code: str,
    error_message: str,
    schema_json: dict,
) -> str:
    """Debug and correct failing Python code."""
    compressed = _compress_schema(schema_json)
    system_prompt = (
        "You are an expert Python data debugging engineer. Correct the failing code.\n\n"
        + _COLAB_ENV_CONTEXT
        + _EXEC_RULES
        + f"\nDataset Schema:\n{json.dumps(compressed, default=str)}"
    )

    user_content = (
        f"Original Request: {prompt}\n\n"
        f"Failing Code:\n```python\n{bad_code}\n```\n\n"
        f"Error:\n{error_message}\n\n"
        "Return ONLY the corrected executable Python code."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        data = await call_gateway(TASK_CODE, messages)
        content = extract_content(data)
        return extract_block_by_pattern(content, is_json=False)
    except httpx.HTTPError as e:
        logger.error("Network error during corrected code generation: %s", e)
        raise
    except Exception as e:
        logger.error("Corrected code generation failed: %s", e)
        return ""


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
        + _COLAB_ENV_CONTEXT
        + "\nReturn ONLY a valid JSON object with these keys:\n"
        '- "prompt": the next analysis instruction (empty string if complete)\n'
        '- "is_complete": boolean\n'
        '- "reason": brief explanation\n'
    )

    compressed = _compress_schema(schema_json)
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
        data = await call_gateway(TASK_CODE, messages)
        content = extract_content(data)
        cleaned = extract_block_by_pattern(content, is_json=True)
        result = json.loads(cleaned)
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


async def interpret(result_data: dict) -> str:
    """Send execution metrics to interpret route to fetch clean insight text."""
    system_prompt = (
        "You are a stellar data presentation assistant. Write a direct interpretation of the stats. "
        "Write strictly as plain text, limited to at most 2 to 3 sentences."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(result_data, default=str)},
    ]
    try:
        data = await call_gateway(TASK_INTERPRET, messages)
        return extract_content(data)
    except Exception as e:
        logger.error("Interpret failed: %s", e)
        return "Analysis complete. Review workspace metrics."


async def analyze_image_for_data(
    image_bytes: bytes, mime_type: str, schema_json: dict
) -> str:
    """Eye + Code combo: extract metadata details from graphic and pipe straight to generator."""
    description = await analyze_image(image_bytes, mime_type)
    prompt = (
        f"The user uploaded an image attachment. Context extracted via vision system:\n\n"
        f"{description}\n\n"
        f"Correlate this visibility context against the loaded dataset variables and compile analytical code."
    )
    return await generate_code(prompt, schema_json)


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
