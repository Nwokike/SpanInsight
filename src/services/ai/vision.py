"""Vision models handling for images."""

from __future__ import annotations

import base64
import logging

from core.constants import TASK_VISION

from .client import call_gateway_raw, extract_content

logger = logging.getLogger(__name__)


async def analyze_image(image_bytes: bytes, mime_type: str) -> str:
    """Send an image to the vision model for detailed description."""
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You are Spaninsight Eye. Describe this image in extreme detail. "
                            "If it contains a chart, table, or data visualization, extract all "
                            "visible numbers, labels, axes, and trends. If it contains text, "
                            "transcribe every word. Be thorough and precise."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64_image}"},
                    },
                ],
            }
        ],
        "task_type": TASK_VISION,
        "temperature": 0.2,
        "max_tokens": 4096,
    }

    try:
        data = await call_gateway_raw(payload, timeout=40.0)
        content = extract_content(data)
        if content:
            logger.info(
                "Spaninsight Eye: described %d bytes image → %d chars",
                len(image_bytes),
                len(content),
            )
            return content
        return "[Image analysis failed - no description returned]"
    except Exception as e:
        logger.error("Spaninsight Eye failed: %s", e)
        return f"[Image analysis failed: {e}]"
