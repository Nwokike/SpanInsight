"""Voice recording and speech-to-text transcription handler for Analysis screen."""

from __future__ import annotations

import logging

import flet as ft

from core.utils import show_snack
from services.ai import transcribe_audio

logger = logging.getLogger("Analysis.VoiceOps")


async def toggle_voice_recording(
    page: ft.Page | None,
    is_recording: bool,
    set_is_recording,
    set_prompt_text,
):
    """Toggle microphone recording and send audio bytes to transcription API."""
    if is_recording:
        set_is_recording(False)
        try:
            from services.audio_service import AudioService

            audio_svc = AudioService(page)
            result = await audio_svc.stop_recording()
            if result:
                audio_bytes, mime_type = result
                text = await transcribe_audio(audio_bytes, mime_type)
                if text and not text.startswith("["):
                    set_prompt_text(text)
        except Exception as ex:
            logger.warning("Voice processing error: %s", ex)
    else:
        set_is_recording(True)
        try:
            from services.audio_service import start_recording

            ok = await start_recording()
            if not ok:
                set_is_recording(False)
                if page:
                    show_snack(
                        page,
                        "Microphone unavailable on this platform. Please type your query.",
                        error=True,
                    )
        except Exception as ex:
            set_is_recording(False)
            if page:
                show_snack(page, f"Voice recording not supported: {ex}", error=True)
