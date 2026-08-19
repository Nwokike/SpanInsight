"""AI code generation for Colab execution environment."""

from __future__ import annotations

import json
import logging
import time

import httpx

from core.constants import TASK_CODE
from services.ai.client import (
    call_gateway,
    extract_block_by_pattern,
    extract_content,
    extract_reasoning,
)
from services.ai.vision import analyze_image

logger = logging.getLogger(__name__)

COLAB_ENV_CONTEXT = (
    "EXECUTION ENVIRONMENT: Google Colab (Python 3.10+, Ubuntu).\n"
    "PRE-INSTALLED: pandas, numpy, matplotlib, seaborn, scikit-learn, scipy,\n"
    "  statsmodels, plotly, tensorflow, torch, transformers, PIL/Pillow,\n"
    "  and all Python stdlib modules.\n"
    "You can install additional packages with !pip install <package>.\n"
    "The user's data files are in /content/. Use pandas to load them.\n"
)

EXEC_RULES = (
    "EXECUTION RULES:\n"
    "- If a DataFrame `df` exists in the session, use it. Otherwise load data from /content/.\n"
    "- Always .dropna() or .fillna() before algebraic/statistical operations.\n"
    "- Plotting: always create figures with plt.figure() or plt.subplots(). Do NOT call plt.savefig().\n"
    "- Assign key results to a variable named `result`.\n"
    "- For simple visual summaries (bar/line/pie), PREFER assigning a chart spec to `result` "
    'as a dict: {"chart": {"type": "bar" or "line" or "pie", "title": str, '
    '"x": [labels], "series": [{"name": str, "y": [numbers]}]}} - '
    "the app renders it as a NATIVE interactive chart.\n"
    "- For complex visuals, use matplotlib figures; the app displays the rendered image.\n"
    "- Do NOT print human-readable text summaries. Only output raw tables, statistics, or plots.\n"
    "- Keep code efficient and focused on the user's request.\n"
    "- Return only executable Python code, no remarks.\n"
)


def compress_schema(schema_json: dict, max_columns: int = 40) -> dict:
    """Optimize LLM context usage while maintaining high code quality.

    For wide datasets (e.g. MNIST with 785 columns or genomic data), samples
    the most representative columns to keep prompt size under ~4KB instead of 150KB.
    """
    if not schema_json:
        return {}
    compressed = dict(schema_json)
    if "head" in compressed and isinstance(compressed["head"], list):
        compressed["head"] = compressed["head"][:2]
    compressed.pop("tail", None)

    cols = compressed.get("columns", [])
    if isinstance(cols, list) and len(cols) > max_columns:
        # Keep first 30 and last 10 columns
        sample_cols = cols[:30] + cols[-10:]
        compressed["columns"] = sample_cols
        compressed["total_columns"] = len(cols)
        compressed["columns_note"] = (
            f"Showing {len(sample_cols)} sampled columns out of {len(cols)} total"
        )

        for key in ("dtypes", "nulls", "summary"):
            val = compressed.get(key)
            if isinstance(val, dict):
                compressed[key] = {c: val[c] for c in sample_cols if c in val}

    return compressed


async def generate_code_meta(
    prompt: str, schema_json: dict, analysis_context: str = ""
) -> dict:
    """Generate executable Python code for the user's analysis request with reasoning metadata."""
    start_time = time.perf_counter()
    context_section = ""
    if analysis_context:
        context_section = (
            f"\n\nPrevious Analysis Context (do NOT repeat):\n{analysis_context}\n"
        )

    compressed = compress_schema(schema_json)
    system_prompt = (
        "You are an expert Python data engineer. Generate optimal, safe code to analyze `df`.\n\n"
        + COLAB_ENV_CONTEXT
        + EXEC_RULES
        + f"\nComplete Dataset Schema:\n{json.dumps(compressed, default=str)}"
        f"{context_section}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    try:
        data = await call_gateway(TASK_CODE, messages)
        duration = time.perf_counter() - start_time
        content = extract_content(data)
        thought = extract_reasoning(data)
        code = extract_block_by_pattern(content, is_json=False)
        model = data.get("model") or data.get("_spaninsight_model_used", "unknown")
        return {
            "code": code,
            "thought": thought,
            "duration": duration,
            "model": model,
        }
    except httpx.HTTPError as e:
        logger.error("Network error during code generation: %s", e)
        raise
    except Exception as e:
        logger.error("Code generation failed: %s", e)
        return {"code": "", "thought": "", "duration": 0.0, "model": "error"}


async def generate_code(
    prompt: str, schema_json: dict, analysis_context: str = ""
) -> str:
    """Generate executable Python code for the user's analysis request."""
    res = await generate_code_meta(prompt, schema_json, analysis_context)
    return res.get("code", "")


async def generate_corrected_code(
    prompt: str,
    bad_code: str,
    error_message: str,
    schema_json: dict,
) -> str:
    """Debug and correct failing Python code."""
    compressed = compress_schema(schema_json)
    system_prompt = (
        "You are an expert Python data debugging engineer. Correct the failing code.\n\n"
        + COLAB_ENV_CONTEXT
        + EXEC_RULES
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
