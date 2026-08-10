"""Audio transcription handling via Whisper."""

from __future__ import annotations

import logging

from core.constants import API_CHAT_ENDPOINT, TASK_AUDIO
from services.api_client import COMMON_HEADERS, get_client

from .client import extract_content

logger = logging.getLogger(__name__)


async def transcribe_audio(audio_bytes: bytes, mime_type: str) -> str:
    """Send audio to Whisper for transcription."""
    try:
        client = get_client()
        files = {"file": ("audio.wav", audio_bytes, mime_type)}
        form_data = {"task_type": TASK_AUDIO}

        resp = await client.post(
            API_CHAT_ENDPOINT,
            headers=COMMON_HEADERS,
            files=files,
            data=form_data,
            timeout=30.0,
        )

        if resp.status_code != 200:
            logger.error("Whisper HTTP %d: %s", resp.status_code, resp.text[:200])
            return "[Transcription failed — server error]"

        data = resp.json()
        transcript = data.get("text", "")
        if not transcript:
            transcript = extract_content(data)

        if transcript:
            logger.info(
                "Spaninsight Voice: transcribed %d bytes audio → '%s'",
                len(audio_bytes),
                transcript[:80],
            )
            return transcript
        return "[Transcription returned empty result]"

    except Exception as e:
        logger.error("Spaninsight Voice failed: %s", e)
        return f"[Transcription failed: {e}]"
