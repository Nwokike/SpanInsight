"""FormsScreen - Modular survey builder, publisher, and responses dashboard."""

from __future__ import annotations

import asyncio
import json
import logging

import flet as ft

from components.form_editor import build_form_editor
from core import theme, tokens
from core.utils import show_snack
from screens.forms.dashboard_view import build_forms_dashboard
from screens.forms.detail_view import build_form_detail_view
from screens.forms.handlers import (
    _form_schema_fields,
    ai_edit_schema_async,
    create_form_schema_async,
    delete_form_async,
    download_csv_async,
    load_forms_async,
    publish_form_async,
    request_update_live_form_async,
)
from services import ai as ai_service
from services import forms_service
from services.audio_service import AudioService
from state import AppStateCtx
from state.controller_ctx import ControllerMethodsCtx

logger = logging.getLogger("FormsScreen")


@ft.component
def FormsScreen() -> ft.Control:
    """Forms & survey builder screen with dashboard, editor, and responses view."""
    page = ft.context.page
    state = ft.use_context(AppStateCtx)
    ft.use_context(ControllerMethodsCtx)

    # Mode: "dashboard", "editor", "detail"
    mode, set_mode = ft.use_state("dashboard")

    user_forms, set_user_forms = ft.use_state([])
    is_loading, set_is_loading = ft.use_state(False)
    is_creating, set_is_creating = ft.use_state(False)
    is_publishing, set_is_publishing = ft.use_state(False)

    is_recording, set_is_recording = ft.use_state(False)
    recording_time, set_recording_time = ft.use_state(0)

    active_form, set_active_form = ft.use_state(None)

    draft_schema, set_draft_schema = ft.use_state([])
    draft_title, set_draft_title = ft.use_state("")
    draft_desc, set_draft_desc = ft.use_state("")

    is_transcribing, set_is_transcribing = ft.use_state(False)
    prompt_text, set_prompt_text = ft.use_state("")

    is_ai_editing, set_is_ai_editing = ft.use_state(False)
    editor_recording, set_editor_recording = ft.use_state(False)
    editor_transcribing, set_editor_transcribing = ft.use_state(False)
    editor_recording_time, set_editor_recording_time = ft.use_state(0)
    ai_edit_text, set_ai_edit_text = ft.use_state("")

    # Set while the editor holds a LIVE published form (edit-in-place flow).
    editing_form_id, set_editing_form_id = ft.use_state("")

    audio_svc = ft.use_ref(lambda: AudioService(page))

    rec_state_ref = ft.use_ref({"is_recording": False, "seconds": 0})
    editor_rec_state_ref = ft.use_ref({"is_recording": False, "seconds": 0})

    def _show_error(msg: str):
        if page:
            from core.utils import show_snack

            show_snack(
                page,
                msg,
                error=True,
                duration=tokens.SNACK_DURATION_EXTENDED_MS,
            )

    async def _load_forms():
        await load_forms_async(
            state.active_project_id, state, set_user_forms, set_is_loading, _show_error
        )

    # ── Mount ────────────────────────────────────────────────────
    async def _on_mount():
        await _load_forms()

    ft.use_effect(_on_mount, [])

    # ── Voice helpers ────────────────────────────────────────────
    async def _update_timer():
        while rec_state_ref.current["is_recording"]:
            await asyncio.sleep(1)
            if rec_state_ref.current["is_recording"]:
                rec_state_ref.current["seconds"] += 1
                set_recording_time(rec_state_ref.current["seconds"])

    async def _handle_auto_stop(result):
        rec_state_ref.current["is_recording"] = False
        set_is_recording(False)
        set_recording_time(0)
        if result:
            audio_bytes, mime_type = result
            transcript = await ai_service.transcribe_audio(audio_bytes, mime_type)
            if transcript and not transcript.startswith("["):
                set_prompt_text(transcript)

    async def on_voice_toggle(e=None):
        if rec_state_ref.current["is_recording"]:
            rec_state_ref.current["is_recording"] = False
            result = await audio_svc.current.stop_recording()
            set_is_recording(False)
            set_recording_time(0)
            set_is_transcribing(True)
            if result:
                audio_bytes, mime_type = result
                try:
                    transcript = await ai_service.transcribe_audio(
                        audio_bytes, mime_type
                    )
                    if transcript and not transcript.startswith("["):
                        set_prompt_text(transcript)
                    else:
                        _show_error("Could not transcribe audio. Try again.")
                except Exception as err:
                    _show_error(f"Transcription failed: {err}")
            else:
                _show_error("No audio recorded.")
            set_is_transcribing(False)
        else:
            started = await audio_svc.current.start_recording(
                on_auto_stop=lambda res: (
                    page.run_task(_handle_auto_stop, res) if page else None
                )
            )
            if started:
                rec_state_ref.current["is_recording"] = True
                rec_state_ref.current["seconds"] = 0
                set_is_recording(True)
                set_recording_time(0)
                if page:
                    page.run_task(_update_timer)

    async def _update_editor_timer():
        while editor_rec_state_ref.current["is_recording"]:
            await asyncio.sleep(1)
            if editor_rec_state_ref.current["is_recording"]:
                editor_rec_state_ref.current["seconds"] += 1
                set_editor_recording_time(editor_rec_state_ref.current["seconds"])

    async def _handle_editor_auto_stop(result):
        editor_rec_state_ref.current["is_recording"] = False
        set_editor_recording(False)
        set_editor_recording_time(0)
        if result:
            audio_bytes, mime_type = result
            transcript = await ai_service.transcribe_audio(audio_bytes, mime_type)
            if transcript and not transcript.startswith("["):
                set_ai_edit_text(transcript)

    async def on_editor_voice_toggle(e=None):
        if editor_rec_state_ref.current["is_recording"]:
            editor_rec_state_ref.current["is_recording"] = False
            result = await audio_svc.current.stop_recording()
            set_editor_recording(False)
            set_editor_recording_time(0)
            set_editor_transcribing(True)
            if result:
                audio_bytes, mime_type = result
                try:
                    transcript = await ai_service.transcribe_audio(
                        audio_bytes, mime_type
                    )
                    if transcript and not transcript.startswith("["):
                        set_ai_edit_text(transcript)
                    else:
                        _show_error("Could not transcribe audio. Try again.")
                except Exception as err:
                    _show_error(f"Transcription failed: {err}")
            else:
                _show_error("No audio recorded.")
            set_editor_transcribing(False)
        else:
            started = await audio_svc.current.start_recording(
                on_auto_stop=lambda res: (
                    page.run_task(_handle_editor_auto_stop, res) if page else None
                )
            )
            if started:
                editor_rec_state_ref.current["is_recording"] = True
                editor_rec_state_ref.current["seconds"] = 0
                set_editor_recording(True)
                set_editor_recording_time(0)
                if page:
                    page.run_task(_update_editor_timer)

    # ── Detail view navigation ───────────────────────────────────
    async def on_view_form(form: dict):
        set_active_form(form)
        resp_data = await forms_service.get_responses(
            form["id"], state.active_project_id
        )
        form["_responses"] = resp_data.get("responses", [])
        form["_count"] = resp_data.get("count", 0)
        set_active_form(form)
        set_mode("detail")

    def on_edit_form(edit_target: dict):
        """Open a LIVE published form in the editor for in-place smart-merge editing."""
        set_active_form(edit_target)
        set_draft_title(edit_target.get("title", ""))
        set_draft_desc(edit_target.get("description", ""))
        set_draft_schema(_form_schema_fields(edit_target))
        set_editing_form_id(str(edit_target.get("id", "")))
        set_mode("editor")

    async def on_copy_link(form_id: str):
        from core.constants import FORMS_PUBLIC_BASE_URL
        from core.utils import set_clipboard, show_snack

        url = f"{FORMS_PUBLIC_BASE_URL}/{form_id}"
        await set_clipboard(page, url)
        if page:
            show_snack(
                page,
                "Link copied!",
                success=True,
                duration=tokens.SNACK_DURATION_SHORT_MS,
            )

    async def on_renew_form(form_id: str):
        new_exp = await forms_service.renew_form(form_id, state.active_project_id)
        if new_exp:
            if page:
                from core.utils import show_snack

                show_snack(
                    page,
                    f"Extended to {new_exp[:10]}",
                    success=True,
                    duration=tokens.SNACK_DURATION_SHORT_MS,
                )
            form = active_form.copy()
            form["expires_at"] = new_exp
            set_active_form(dict(form))
            await _load_forms()
        else:
            _show_error("Failed to renew.")

    def on_renew_clicked(form_id: str):
        """Confirmation modal before extending a live form (+7 days)."""
        if not page:
            return

        def _close(_=None):
            page.pop_dialog()

        def _confirm(_=None):
            _close()
            if page:
                page.run_task(on_renew_form, form_id)

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Extend Form (+7 Days)?"),
                content=ft.Container(
                    content=ft.Text(
                        "The share link stays the same and anyone with it can "
                        "keep submitting for 7 more days. Collected responses "
                        "are untouched.",
                        size=tokens.FONT_BODY,
                    ),
                    width=tokens.DIALOG_WIDTH_SM,
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=_close),
                    ft.FilledButton(
                        "Extend",
                        on_click=_confirm,
                    ),
                ],
            )
        )

    def on_editor_cancel(_=None):
        """Discard-changes confirmation when leaving the editor."""
        if not page:
            set_mode("dashboard")
            set_draft_schema([])
            set_editing_form_id("")
            return

        def _close(_=None):
            page.pop_dialog()

        def _discard(_=None):
            _close()
            set_mode("dashboard")
            set_draft_schema([])
            set_editing_form_id("")
            set_draft_title("")
            set_draft_desc("")

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "Discard changes?" if editing_form_id else "Discard this draft?"
                ),
                content=ft.Container(
                    content=ft.Text(
                        "Everything you edited in this session will be lost. "
                        "The published form keeps its current version.",
                        size=tokens.FONT_BODY,
                    ),
                    width=tokens.DIALOG_WIDTH_SM,
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=_close),
                    ft.FilledButton(
                        "Discard",
                        bgcolor=theme.ERROR,
                        color=ft.Colors.WHITE,
                        on_click=_discard,
                    ),
                ],
            )
        )

    def on_analyze_responses(form_data: dict):
        responses = form_data.get("_responses", [])
        if not responses:
            _show_error("No responses to analyze yet.")
            return

        form_title = form_data.get("title", "Survey")
        rows = [r.get("data", r) for r in responses]

        # DataFrame columns use the questions' human-readable LABELS (raw
        # storage key as fallback for unknown/legacy ids, and on collisions).
        from screens.forms.handlers import _form_schema_fields

        labels = {
            str(f.get("name")): str(f.get("label") or f.get("name"))
            for f in _form_schema_fields(form_data)
            if f.get("name")
        }
        ordered_keys = []
        for row in rows:
            for k in row:
                if k not in ordered_keys:
                    ordered_keys.append(k)
        col_map = {}
        used = set()
        for k in ordered_keys:
            label = labels.get(k, k)
            if label in used:
                label = k
            used.add(label)
            col_map[k] = label
        aliased_rows = [{col_map[k]: v for k, v in row.items()} for row in rows]

        code = (
            f"# Survey Dataset: {form_title}\n"
            f"# Total Collected Responses: {len(aliased_rows)}\n"
            f"import pandas as pd\n\n"
            f"responses_data = {json.dumps(aliased_rows, indent=2)}\n"
            f"df = pd.DataFrame(responses_data)\n\n"
            f"print(f\"Loaded survey '{form_title}': {{len(df)}} responses, {{len(df.columns)}} columns\")\n"
            f"df.head()"
        )

        dataset_name = f"{form_title.replace(' ', '_')}_responses.csv"
        # Hand off to the Analysis screen, which owns cell insertion and
        # persistence (direct state writes are lost when its mount handler
        # reloads the active project).
        state.pending_forms_import = {
            "name": dataset_name,
            "code": code,
        }
        state.current_tab = 1
        if page:
            show_snack(
                page,
                f"📊 Loaded {len(rows)} responses into Notebook!",
                success=True,
            )

    # ── View Router ──────────────────────────────────────────────
    if mode == "editor":
        view_controls = build_form_editor(
            schema=draft_schema,
            title=draft_title,
            description=draft_desc,
            on_schema_changed=set_draft_schema,
            on_title_changed=set_draft_title,
            on_desc_changed=set_draft_desc,
            on_ai_edit=lambda action, val: (
                page.run_task(
                    ai_edit_schema_async,
                    action,
                    val,
                    ai_edit_text,
                    draft_schema,
                    draft_title,
                    draft_desc,
                    set_ai_edit_text,
                    set_is_ai_editing,
                    set_draft_schema,
                    set_draft_title,
                    set_draft_desc,
                    _show_error,
                )
                if page
                else None
            ),
            on_voice_toggle=lambda e: (
                page.run_task(on_editor_voice_toggle, e) if page else None
            ),
            on_publish=(
                lambda: (
                    (
                        page.run_task(
                            request_update_live_form_async,
                            active_form,
                            draft_title,
                            draft_desc,
                            draft_schema,
                            state.active_project_id,
                            page,
                            set_is_publishing,
                            set_mode,
                            set_draft_schema,
                            set_prompt_text,
                            set_editing_form_id,
                            set_active_form,
                            _load_forms,
                            _show_error,
                        )
                        if page
                        else None
                    )
                    if editing_form_id
                    else (
                        page.run_task(
                            publish_form_async,
                            state.active_project_id,
                            draft_title,
                            draft_desc,
                            draft_schema,
                            page,
                            set_is_publishing,
                            set_mode,
                            set_draft_schema,
                            set_prompt_text,
                            _load_forms,
                            _show_error,
                        )
                        if page
                        else None
                    )
                )
            ),
            on_cancel=on_editor_cancel,
            is_publishing=is_publishing,
            is_recording=editor_recording,
            is_transcribing=editor_transcribing,
            is_ai_editing=is_ai_editing,
            recording_time=editor_recording_time,
            ai_prompt_text=ai_edit_text,
            recording_timer_ref=None,
            publish_label="Update Form" if editing_form_id else "Publish",
        )
    elif mode == "detail":
        view_controls = build_form_detail_view(
            page=page,
            form=active_form,
            on_back=lambda _: (set_active_form(None), set_mode("dashboard")),
            on_copy_link=lambda fid: page.run_task(on_copy_link, fid) if page else None,
            on_edit=on_edit_form,
            on_renew=on_renew_clicked,
            on_download_csv=lambda f: (
                page.run_task(download_csv_async, f, page, _show_error)
                if page
                else None
            ),
            on_analyze=on_analyze_responses,
            on_delete=lambda fid: (
                page.run_task(
                    delete_form_async,
                    fid,
                    state.active_project_id,
                    page,
                    set_is_loading,
                    set_active_form,
                    set_mode,
                    _load_forms,
                    _show_error,
                )
                if page
                else None
            ),
        )
    else:
        view_controls = build_forms_dashboard(
            page=page,
            user_forms=user_forms,
            is_loading=is_loading,
            is_creating=is_creating,
            is_recording=is_recording,
            is_transcribing=is_transcribing,
            recording_time=recording_time,
            prompt_text=prompt_text,
            set_prompt_text=set_prompt_text,
            on_create_form=lambda e: (
                (
                    set_editing_form_id(""),
                    page.run_task(
                        create_form_schema_async,
                        prompt_text,
                        set_is_creating,
                        set_draft_schema,
                        set_draft_title,
                        set_draft_desc,
                        set_mode,
                        _show_error,
                    ),
                )
                if page
                else None
            ),
            on_voice_toggle=lambda e: (
                page.run_task(on_voice_toggle, e) if page else None
            ),
            on_view_form=lambda f: page.run_task(on_view_form, f) if page else None,
            on_refresh=lambda e: page.run_task(_load_forms) if page else None,
        )

    return ft.Column(
        controls=view_controls,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
