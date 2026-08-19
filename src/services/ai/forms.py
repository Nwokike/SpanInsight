"""AI forms generation."""

from __future__ import annotations

import json
import logging

from core.constants import TASK_SUGGEST

from .client import call_gateway, extract_block_by_pattern, extract_content

logger = logging.getLogger(__name__)


import re


def _parse_form_json(cleaned: str) -> dict | None:
    """Robustly parse JSON for form schemas handling LLM formatting quirks."""
    if not cleaned:
        return None

    # Attempt 1: Standard load with strict=False (allows unescaped control chars/newlines)
    try:
        return json.loads(cleaned, strict=False)
    except Exception:
        pass

    # Attempt 2: Strip any trailing commas or markdown fences
    text = cleaned.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    # Find outermost braces
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    # Remove trailing commas: e.g. {"a": 1,} -> {"a": 1}
    text = re.sub(r",\s*([\]}])", r"\1", text)

    try:
        return json.loads(text, strict=False)
    except Exception:
        pass

    # Attempt 3: Escape raw unescaped newlines/tabs inside string literals
    try:
        sanitized = re.sub(
            r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]",
            "",
            text,
        )
        return json.loads(sanitized, strict=False)
    except Exception as e:
        logger.error("All JSON parse attempts failed: %s | Text: %s", e, text[:200])
        return None


async def generate_form_schema(prompt: str) -> dict | None:
    """Generate high-fidelity research forms with comprehensive structural depth."""
    system_prompt = (
        "You are an expert research survey designer and form builder AI. "
        "Your job is to generate COMPREHENSIVE, THOROUGH, RESEARCH-GRADE forms. "
        "Do NOT produce minimal or skeleton forms - think deeply about every angle of the topic.\n\n"
        "FIELD GENERATION RULES:\n"
        "- Generate 12 to 25 fields - NEVER fewer than 12\n"
        "- Start with demographics: age range, gender, education, region/location\n"
        "- Cover the topic from multiple angles\n"
        "OUTPUT - return ONLY a raw JSON object, no markdown fences, no explanation:\n"
        '{"title":"...","description":"...","fields":[{"name":"snake_case","label":"Display label",'
        '"type":"text|textarea|number|email|select|radio|checkbox|date|phone|url|rating",'
        '"required":true,"options":["A","B"]}]}'
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    try:
        data = await call_gateway(TASK_SUGGEST, messages)
        content = extract_content(data)
        cleaned = extract_block_by_pattern(content, is_json=True)
        return _parse_form_json(cleaned)
    except Exception as e:
        logger.error("AI form gen failed: %s", e)
        return None
