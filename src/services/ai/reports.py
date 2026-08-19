"""AI report generation and editing."""

from __future__ import annotations

import json
import logging

from core.constants import TASK_SUGGEST

from .client import call_gateway, extract_block_by_pattern, extract_content

logger = logging.getLogger(__name__)


def _parse_resilient_json(text: str) -> dict | None:
    """Robustly extract and parse a JSON object from raw LLM output."""
    from .client import strip_thinking

    # First attempt to extract everything from first { to last } from the raw 'text' string.
    # Since we always expect a JSON object for reports, this completely avoids being tricked
    # by a leading '[' from LLM conversational reasoning (e.g. "[0,1,3,2,4,5,6,7] would follow...").
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last >= first:
        cleaned = text[first : last + 1]
    else:
        cleaned = extract_block_by_pattern(text, is_json=True)

    cleaned = strip_thinking(cleaned)

    try:
        return json.loads(cleaned, strict=False)
    except Exception as e:
        logger.warning(
            "Standard strict=False JSON parsing failed: %s. Attempting custom repairs.",
            e,
        )

        repaired = _repair_json(cleaned)
        try:
            return json.loads(repaired, strict=False)
        except Exception as ex:
            logger.error(
                "All JSON repair attempts failed. Original text length: %d. Error: %s",
                len(text),
                ex,
            )
            logger.error("Raw cleaned text that failed to parse: %s", cleaned)
            raise


def _repair_json(text: str) -> str:
    """Apply progressive repairs to malformed JSON."""
    import re

    repaired = text

    # 1. Strip single-line and multi-line comments
    repaired = re.sub(r"//[^\n]*", "", repaired)
    repaired = re.sub(r"/\*.*?\*/", "", repaired, flags=re.DOTALL)

    # 2. Replace single quotes with double quotes (but not within double-quoted strings)
    repaired = re.sub(r"([{,])\s*'([^']*?)'\s*(?=\s*[:,\}])", r'\1"\2"', repaired)
    repaired = re.sub(r"(:\s*)'([^']*?)'\s*(?=\s*[,}])", r'\1"\2"', repaired)

    # 3. Replace bare NaN, Infinity, -Infinity with null
    repaired = re.sub(r"\bNaN\b", "null", repaired)
    repaired = re.sub(r"\bInfinity\b", "null", repaired)
    repaired = re.sub(r"\b-Infinity\b", "null", repaired)

    # 4. Insert missing commas between objects/arrays
    repaired = re.sub(r"\}\s*\{", "}, {", repaired)
    repaired = re.sub(r"\]\s*\[", "], [", repaired)
    repaired = re.sub(r"\}\s*\[", "}, [", repaired)
    repaired = re.sub(r"\]\s*\{", "], {", repaired)

    # 5. Strip trailing commas before closing brackets/braces
    repaired = re.sub(r",\s*([\]}])", r"\1", repaired)

    # 6. Remove trailing comma before end of string before closing brace
    repaired = re.sub(r",\s*$", "", repaired)

    return repaired


async def arrange_report(blocks: list[dict], dataset_name: str = "") -> dict | None:
    """AI auto-arranges report blocks into optimal order with polished descriptions."""
    system_prompt = (
        "You are an expert report formatter. Given a list of analysis blocks, "
        "format them into a professional, publication-ready report.\n\n"
        "YOUR TASKS:\n"
        "1. Generate a concise, polished report title (focused on business insights).\n"
        "2. Generate a premium, consumer-friendly 1-2 sentence executive summary description of the overall findings.\n"
        "3. Rewrite the title/prompt of each block to be a beautiful, highly professional slide/section header "
        "(e.g., 'Data Ingestion & Loading' instead of 'load dataset', 'Missing Data Imputation' instead of 'clean missing values'). "
        "Make every block title read like a premium executive slide header!\n"
        "4. Keep all block-level descriptions exactly identical to how you received them.\n\n"
        "CRITICAL: Return ONLY valid raw JSON starting with '{' and ending with '}'. "
        "Do NOT write any explanations, reasoning, thoughts, or preamble. Any conversational text will cause a system crash!\n\n"
        "OUTPUT FORMAT:\n"
        '{"title":"...", "description":"...", "blocks":[{"prompt":"Concise Section Header", "description":"(preserved original description)", "original_index": 0}]}'
    )

    blocks_summary = [
        {
            "index": i,
            "prompt": b.get("prompt", ""),
            "description": b.get("description", ""),
        }
        for i, b in enumerate(blocks)
    ]
    user_content = (
        f"Dataset: {dataset_name}\n\nBlocks:\n{json.dumps(blocks_summary, default=str)}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        data = await call_gateway(TASK_SUGGEST, messages)
        content = extract_content(data)
        result = _parse_resilient_json(content)
        if isinstance(result, dict) and "blocks" in result:
            logger.info(
                "AI arranged report: %s (%d blocks)",
                result.get("title", ""),
                len(result["blocks"]),
            )
            return result
        return None
    except Exception as e:
        logger.error("Arrange report failed: %s", e)
        return None


async def edit_report_with_ai(
    current_blocks: list[dict],
    title: str,
    description: str,
    user_instruction: str,
) -> dict | None:
    """AI edits report based on user instruction (reorder, rephrase, etc.)."""
    system_prompt = (
        "You are an expert report editor. Apply the user's edit instruction to the report.\n\n"
        "RULES:\n"
        "- You may reorder blocks, edit report titles, and update the report-level description.\n"
        "- Generate a beautiful, concise report-level description as an executive summary of the findings.\n"
        "- You MUST NOT modify, edit, or touch any block-level descriptions unless the user's edit instruction explicitly requests it. "
        "Otherwise, return all block-level descriptions exactly identical to how you received them.\n"
        "- You MUST NOT delete any blocks - return the same count.\n"
        "- Reformat block titles to be highly professional, concise section headers.\n\n"
        "CRITICAL: Return ONLY valid raw JSON starting with '{' and ending with '}'. "
        "Do NOT write any explanations, reasoning, thoughts, or preamble. Any conversational text will cause a system crash!\n\n"
        "OUTPUT FORMAT:\n"
        '{"title":"...", "description":"...", "blocks":[{"prompt":"...", "description":"...", "original_index": 0}]}'
    )

    blocks_summary = [
        {
            "index": i,
            "prompt": b.get("prompt", ""),
            "description": b.get("description", ""),
        }
        for i, b in enumerate(current_blocks)
    ]
    user_content = (
        f"Report Title: {title}\nDescription: {description}\n\n"
        f"Blocks:\n{json.dumps(blocks_summary, default=str)}\n\n"
        f"Edit Instruction: {user_instruction}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        data = await call_gateway(TASK_SUGGEST, messages)
        content = extract_content(data)
        result = _parse_resilient_json(content)
        if isinstance(result, dict) and "blocks" in result:
            logger.info("AI edited report: %d blocks", len(result["blocks"]))
            return result
        return None
    except Exception as e:
        logger.error("Edit report with AI failed: %s", e)
        return None
