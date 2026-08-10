"""AI forms generation."""

from __future__ import annotations

import json
import logging

from core.constants import TASK_SUGGEST

from .client import call_gateway, extract_block_by_pattern, extract_content

logger = logging.getLogger(__name__)


async def generate_form_schema(prompt: str) -> dict | None:
    """Generate high-fidelity research forms with comprehensive structural depth."""
    system_prompt = (
        "You are an expert research survey designer and form builder AI. "
        "Your job is to generate COMPREHENSIVE, THOROUGH, RESEARCH-GRADE forms. "
        "Do NOT produce minimal or skeleton forms — think deeply about every angle of the topic.\n\n"
        "FIELD GENERATION RULES:\n"
        "- Generate 12 to 25 fields — NEVER fewer than 12\n"
        "- Start with demographics: age range, gender, education, region/location\n"
        "- Cover the topic from multiple angles\n"
        "OUTPUT — return ONLY a raw JSON object, no markdown fences, no explanation:\n"
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
        return json.loads(cleaned)
    except Exception as e:
        logger.error("AI form gen failed: %s", e)
        return None
