"""AI Gateway client and utility functions."""

from __future__ import annotations

import logging
import re

from core.constants import API_CHAT_ENDPOINT, API_HEALTH_ENDPOINT, USER_AGENT
from services.api_client import get_client, request_with_retry

logger = logging.getLogger(__name__)

# Pre-compiled regular expressions for robust extraction
_THINK_RE = re.compile(
    r"<(?:think|thought|reasoning)>.*?(?:</(?:think|thought|reasoning)>|$)",
    re.DOTALL | re.IGNORECASE,
)
_PYTHON_BLOCK_RE = re.compile(r"```python\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_JSON_BLOCK_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_GENERIC_BLOCK_RE = re.compile(r"```\s*(.*?)\s*```", re.DOTALL)

# Timeouts per task type, calibrated against real gateway latencies:
# reasoning models routinely take 30-90s on `suggest` and up to ~140s on
# `code` (observed live) - 60s timeouts caused double-spends via retries.
TIMEOUTS = {
    "suggest": 90.0,
    "code": 150.0,
    "interpret": 90.0,
    "vision": 60.0,
    "audio": 90.0,
}


async def check_health() -> bool:
    """Ping the gateway health endpoint. Returns True if online."""
    try:
        client = get_client()
        resp = await client.get(
            API_HEALTH_ENDPOINT,
            headers={"User-Agent": USER_AGENT},
            timeout=5.0,
        )
        return resp.status_code == 200
    except Exception as e:
        logger.warning("Gateway health check failed: %s", e)
        return False


async def call_gateway(task_type: str, messages: list[dict]) -> dict:
    """Make a non-streaming POST to the gateway with retry and expanded processing thresholds."""
    import time

    start_time = time.perf_counter()

    prompt_chars = sum(len(m.get("content", "")) for m in messages)
    logger.info(
        "[AI Gateway] Request starting | Task: %s | Messages: %d | Prompt size: ~%d chars",
        task_type,
        len(messages),
        prompt_chars,
    )

    payload = {
        "task_type": task_type,
        "stream": False,
        "messages": messages,
    }
    timeout = TIMEOUTS.get(task_type, 20.0)

    try:
        resp = await request_with_retry(
            "POST",
            API_CHAT_ENDPOINT,
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        duration = time.perf_counter() - start_time
        model_name = data.get("model", "unknown-gateway-model")
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        logger.info(
            "[AI Gateway] Request completed | Model: %s | Duration: %.2fs | "
            "Tokens: In=%d, Out=%d | Status: %d",
            model_name,
            duration,
            prompt_tokens,
            completion_tokens,
            resp.status_code,
        )

        if (
            "groq" in model_name.lower()
            or "llama" in model_name.lower()
            or "mixtral" in model_name.lower()
        ) and (prompt_chars > 15000 or prompt_tokens > 4000):
            logger.warning(
                "[AI Gateway WARNING] Large context (%d chars / %d tokens) detected on model %s. "
                "Groq models have strict limits and should ideally be kept under ~5K context for optimal stability.",
                prompt_chars,
                prompt_tokens,
                model_name,
            )
        return data
    except Exception as err:
        duration = time.perf_counter() - start_time
        logger.error(
            "[AI Gateway ERROR] Request failed after %.2fs | Task: %s | Error: %s",
            duration,
            task_type,
            err,
        )
        raise


async def call_gateway_raw(payload: dict, timeout: float = 15.0) -> dict:
    """Make a raw POST to the gateway with active connection parameters."""
    import time

    start_time = time.perf_counter()

    messages = payload.get("messages", [])
    prompt_chars = sum(len(m.get("content", "")) for m in messages)
    task_type = payload.get("task_type", "raw")
    logger.info(
        "[AI Gateway] Raw request starting | Task: %s | Messages: %d | Prompt size: ~%d chars",
        task_type,
        len(messages),
        prompt_chars,
    )

    try:
        resp = await request_with_retry(
            "POST",
            API_CHAT_ENDPOINT,
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        duration = time.perf_counter() - start_time
        model_name = data.get("model", "unknown-gateway-model")
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        logger.info(
            "[AI Gateway] Raw request completed | Model: %s | Duration: %.2fs | "
            "Tokens: In=%d, Out=%d | Status: %d",
            model_name,
            duration,
            prompt_tokens,
            completion_tokens,
            resp.status_code,
        )

        if (
            "groq" in model_name.lower()
            or "llama" in model_name.lower()
            or "mixtral" in model_name.lower()
        ) and (prompt_chars > 15000 or prompt_tokens > 4000):
            logger.warning(
                "[AI Gateway WARNING] Large context (%d chars / %d tokens) detected on model %s. "
                "Groq models have strict limits and should ideally be kept under ~5K context for optimal stability.",
                prompt_chars,
                prompt_tokens,
                model_name,
            )
        return data
    except Exception as err:
        duration = time.perf_counter() - start_time
        logger.error(
            "[AI Gateway ERROR] Raw request failed after %.2fs | Task: %s | Error: %s",
            duration,
            task_type,
            err,
        )
        raise


def extract_content(data: dict) -> str:
    """Extract assistant payload content while handling thinking steps safely."""
    try:
        choices = data.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "") or ""
            content = strip_thinking(content)
            return content.strip()
    except (IndexError, KeyError, TypeError):
        pass
    return ""


def extract_reasoning(data: dict) -> str:
    """Extract reasoning/thinking process from message reasoning_content, reasoning, or thinking tags."""
    try:
        choices = data.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            reasoning = (
                message.get("reasoning_content")
                or message.get("reasoning")
                or message.get("thought")
                or data.get("reasoning")
            )
            if reasoning and str(reasoning).strip():
                return str(reasoning).strip()
            content = message.get("content", "") or ""
            match = re.search(
                r"<(?:think|thought|reasoning)>(.*?)(?:</(?:think|thought|reasoning)>|$)",
                content,
                re.DOTALL | re.IGNORECASE,
            )
            if match:
                return match.group(1).strip()
    except Exception:
        pass
    return ""


def strip_thinking(text: str) -> str:
    """Remove <think>...</think> reasoning blocks using efficient pre-compiled matching."""
    return _THINK_RE.sub("", text).strip()


def extract_block_by_pattern(text: str, is_json: bool = False) -> str:
    """Uses advanced Regex pattern matching to pull code arrays safely."""
    cleaned = strip_thinking(text)

    if is_json:
        # Check which bracket comes first to determine the outermost structure (object or array)
        first_brace = cleaned.find("{")
        first_bracket = cleaned.find("[")

        if first_bracket != -1 and (first_brace == -1 or first_bracket < first_brace):
            # Outer-most is an array
            end_bracket = cleaned.rfind("]")
            if end_bracket != -1 and end_bracket > first_bracket:
                return cleaned[first_bracket : end_bracket + 1].strip()

        if first_brace != -1:
            # Outer-most is an object
            end_brace = cleaned.rfind("}")
            if end_brace != -1 and end_brace > first_brace:
                return cleaned[first_brace : end_brace + 1].strip()

        match = _JSON_BLOCK_RE.search(cleaned)
        if match:
            return match.group(1).strip()
    else:
        match = _PYTHON_BLOCK_RE.search(cleaned)
        if match:
            return match.group(1).strip()

    generic_match = _GENERIC_BLOCK_RE.search(cleaned)
    if generic_match:
        return generic_match.group(1).strip()

    for trim_target in ["```python", "```json", "```"]:
        if cleaned.lower().startswith(trim_target):
            cleaned = cleaned[len(trim_target) :]
    cleaned = cleaned.removesuffix("```")

    return cleaned.strip()
