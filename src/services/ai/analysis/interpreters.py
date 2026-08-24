"""AI interpretation and statistical summary generators."""

from __future__ import annotations

import json
import logging

from core.constants import TASK_INTERPRET
from services.ai.analysis.code_gen import compress_schema
from services.ai.client import call_gateway, extract_content

logger = logging.getLogger(__name__)


async def describe_dataset(schema_json: dict) -> str:
    """AI reads the schema and produces a concise dataset overview."""
    system_prompt = (
        "You are an expert data science director. Given a comprehensive dataset schema "
        "with structural details and distribution statistics, provide a professional, "
        "highly concise overview of what the data signifies and the macro domains it represents. "
        "Do NOT use any markdown (no bold, no italics, no bullet points, no headers). "
        "Write strictly as clear, plain-text prose, limited to at most 2 to 3 sentences."
    )
    ai_schema = compress_schema(schema_json)
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


async def verify_result(
    question: str,
    schema_description: str,
    res_data: dict,
) -> dict:
    """Verify an executed analysis against the user's literal question.

    The verifier reads ONLY real execution artifacts (stdout, returned value,
    structured result) and must ground every number it reports in them.
    Returns a strict contract::

        {"satisfied": bool,       # does this result answer the question?
         "answer": str,           # grounded 2-4 sentence answer (plain text)
         "gaps": [str],           # what is still missing (empty if satisfied)
         "key_numbers": [str]}    # exact figures lifted from the outputs

    On ANY gateway/parsing failure we return ``verified=False`` with the
    generic narration fallback so the UI degrades gracefully instead of
    blocking on verification.
    """
    system_prompt = (
        "You are a rigorous data-analysis VERIFIER. You are given a user's "
        "question and the REAL artifacts of an executed analysis (code, stdout "
        "logs, returned value). Decide whether the execution genuinely answers "
        "the question.\n\n"
        "Rules:\n"
        "- Ground EVERY number in 'answer'/'key_numbers' strictly in the "
        "provided artifacts. NEVER invent or estimate figures.\n"
        "- If the artifacts do not contain the needed information, set "
        "'satisfied' to false and list exactly what is missing in 'gaps'.\n"
        "- 'answer' is plain text, no markdown, 2 to 4 sentences, directly "
        "answering the question using only artifact-backed facts.\n\n"
        "Return ONLY a valid JSON object with these keys:\n"
        '{"satisfied": boolean, "answer": string, "gaps": string[], '
        '"key_numbers": string[]}'
    )
    user_content = (
        f"User's Question:\n{question}\n\n"
        f"Dataset Context: {schema_description}\n\n"
        f"Executed Code:\n{res_data.get('code', '')}\n\n"
        f"Standard Output Logs:\n{res_data.get('stdout', '')}\n"
        f"Returned Value String:\n{res_data.get('result', '')}\n"
        f"Structured Result JSON:\n{json.dumps(res_data.get('structured_result'), default=str)[:6000]}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    fallback = {
        "satisfied": False,
        "answer": "",
        "gaps": [],
        "key_numbers": [],
        "verified": False,
    }
    try:
        data = await call_gateway(TASK_INTERPRET, messages)
        content = extract_content(data)
        from services.ai.client import extract_block_by_pattern

        cleaned = extract_block_by_pattern(content or "", is_json=True)
        result = json.loads(cleaned, strict=False)
        if not isinstance(result, dict) or "satisfied" not in result:
            return fallback
        return {
            "satisfied": bool(result.get("satisfied")),
            "answer": str(result.get("answer", "")).strip(),
            "gaps": [str(g) for g in (result.get("gaps") or [])][:5],
            "key_numbers": [str(k) for k in (result.get("key_numbers") or [])][:8],
            "verified": True,
        }
    except Exception as e:
        logger.warning("verify_result failed (degrading gracefully): %s", e)
        return fallback
