"""AI interpretation and statistical summary generators."""

from __future__ import annotations

import json
import logging

from core.constants import TASK_INTERPRET
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
