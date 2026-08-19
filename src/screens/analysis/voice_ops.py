"""Voice recording and speech-to-text transcription handler for Analysis screen."""

from __future__ import annotations

import asyncio
import logging

import flet as ft

from core.utils import show_snack
from services.ai import transcribe_audio

logger = logging.getLogger("Analysis.VoiceOps")


async def toggle_voice_recording(
    page: ft.Page | None,
    audio_service,
    rec_state_ref,
    set_is_recording,
    set_recording_time,
    set_prompt_text,
):
    """Toggle microphone recording and send audio bytes to transcription API."""
    if not audio_service:
        return

    if rec_state_ref.current["is_recording"]:
        rec_state_ref.current["is_recording"] = False
        set_is_recording(False)
        set_recording_time(0)
        try:
            result = await audio_service.stop_recording()
            if result:
                audio_bytes, mime_type = result
                text = await transcribe_audio(audio_bytes, mime_type)
                if text and not text.startswith("["):
                    set_prompt_text(text)
                else:
                    if page:
                        show_snack(
                            page, "Could not transcribe audio. Try again.", error=True
                        )
        except Exception as ex:
            logger.warning("Voice processing error: %s", ex)
            if page:
                show_snack(page, f"Transcription failed: {ex}", error=True)
    else:
        try:
            started = await audio_service.start_recording()
            if started:
                rec_state_ref.current["is_recording"] = True
                rec_state_ref.current["seconds"] = 0
                set_is_recording(True)
                set_recording_time(0)

                async def _timer_loop():
                    while rec_state_ref.current["is_recording"]:
                        await asyncio.sleep(1)
                        if rec_state_ref.current["is_recording"]:
                            rec_state_ref.current["seconds"] += 1
                            set_recording_time(rec_state_ref.current["seconds"])

                if page:
                    page.run_task(_timer_loop)
            else:
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
                show_snack(page, f"Voice recording error: {ex}", error=True)
