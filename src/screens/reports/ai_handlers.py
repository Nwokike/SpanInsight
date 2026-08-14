"""AI arrangement, editing, and voice transcription handlers for Reports view."""

from __future__ import annotations

import asyncio
import logging

import flet as ft

from services import ai as ai_service

logger = logging.getLogger("ReportsAIHandlers")


async def on_ai_edit(page: ft.Page, ui_state, action: str, text: str):
    """Run natural language editing prompt against current report blocks."""
    if action == "__set_text__":
        ui_state.ai_prompt_text["value"] = text
        return

    if action == "__submit__":
        prompt = text.strip()
        if not prompt:
            return

        ui_state.is_ai_editing["value"] = True
        ui_state.rebuild()
        try:
            result = await ai_service.edit_report_with_ai(
                current_blocks=ui_state.editor_blocks,
                title=ui_state.draft_title["value"],
                description=ui_state.draft_desc["value"],
                user_instruction=prompt,
            )
            if result and "blocks" in result:
                new_blocks = []
                for ai_block in result["blocks"]:
                    orig_idx = ai_block.get("original_index", 0)
                    if 0 <= orig_idx < len(ui_state.editor_blocks):
                        b = ui_state.editor_blocks[orig_idx].copy()
                        b["prompt"] = ai_block.get("prompt", b.get("prompt", ""))
                        b["description"] = ai_block.get(
                            "description", b.get("description", "")
                        )
                        new_blocks.append(b)
                if len(new_blocks) == len(ui_state.editor_blocks):
                    ui_state.editor_blocks.clear()
                    ui_state.editor_blocks.extend(new_blocks)
                if result.get("title"):
                    ui_state.draft_title["value"] = result["title"]
                if result.get("description"):
                    ui_state.draft_desc["value"] = result["description"]
                ui_state.ai_prompt_text["value"] = ""
        except Exception as e:
            logger.error("AI edit failed: %s", e)
            if page:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"AI edit failed: {e}"), duration=3000
                )
                page.snack_bar.open = True
                page.update()
        ui_state.is_ai_editing["value"] = False
        ui_state.rebuild()


async def _handle_voice_auto_stop(page: ft.Page, ui_state, result):
    ui_state.is_recording["value"] = False
    if result:
        ui_state.is_transcribing["value"] = True
        ui_state.rebuild()
        audio_bytes, mime = result
        try:
            transcript = await ai_service.transcribe_audio(audio_bytes, mime)
            if transcript and not transcript.startswith("["):
                ui_state.ai_prompt_text["value"] = transcript
        except Exception as ex:
            logger.error("Voice transcription failed: %s", ex)
        ui_state.is_transcribing["value"] = False
    ui_state.rebuild()


async def _update_timer(page: ft.Page, ui_state):
    while ui_state.is_recording["value"]:
        await asyncio.sleep(1)
        if ui_state.is_recording["value"]:
            ui_state.recording_time["value"] += 1
            if ui_state.recording_timer_ref.current:
                ui_state.recording_timer_ref.current.value = (
                    f"00:{ui_state.recording_time['value']:02d} / 01:00"
                )
                if page:
                    page.update(ui_state.recording_timer_ref.current)


async def on_voice_toggle(page: ft.Page, ui_state):
    """Toggle voice audio recording and auto-transcribe."""
    if ui_state.is_recording["value"]:
        result = await ui_state.audio_svc.stop_recording()
        ui_state.is_recording["value"] = False
        if result:
            ui_state.is_transcribing["value"] = True
            ui_state.rebuild()
            audio_bytes, mime = result
            try:
                transcript = await ai_service.transcribe_audio(audio_bytes, mime)
                if transcript and not transcript.startswith("["):
                    ui_state.ai_prompt_text["value"] = transcript
            except Exception as ex:
                logger.error("Voice transcription failed: %s", ex)
            ui_state.is_transcribing["value"] = False
        ui_state.rebuild()
    else:
        started = await ui_state.audio_svc.start_recording(
            on_auto_stop=lambda res: (
                page.run_task(_handle_voice_auto_stop, page, ui_state, res)
                if page
                else None
            )
        )
        if started:
            ui_state.is_recording["value"] = True
            ui_state.recording_time["value"] = 0
            ui_state.rebuild()
            if page:
                page.run_task(_update_timer, page, ui_state)
