"""FormsScreen - Modular survey builder, publisher, and responses dashboard."""

from __future__ import annotations

import asyncio
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
    load_all_forms_async,
    publish_form_async,
    request_update_live_form_async,
)
from services import ai as ai_service
from services import forms_service
from services.audio_service import AudioService
from state import AppStateCtx
from state.controller_ctx import ControllerMethodsCtx
from state.service_ctx import ServiceCtx

logger = logging.getLogger("FormsScreen")


@ft.component
def FormsScreen() -> ft.Control:
    """Forms & survey builder screen with dashboard, editor, and responses view."""
    page = ft.context.page
    state = ft.use_context(AppStateCtx)
    services = ft.use_context(ServiceCtx)
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
        # Project-independent: every form the account owns, annotated with
        # its owning project, so silent project switches never blank the tab.
        await load_all_forms_async(
            services.projects, state, set_user_forms, set_is_loading, _show_error
        )

    def _form_project_scope(form_or: dict | str) -> str:
        """Owning project id for a form (auth scope for its endpoints).

        The active project may be unrelated to the form, so per-form actions
        must always authenticate with the project the form was filed under.
        """
        if isinstance(form_or, dict):
            pid = str(form_or.get("_project_id") or "").strip()
            if pid:
                return pid
            form_or = form_or.get("id")
        for f in state.forms or []:
            if f.get("id") == form_or and f.get("_project_id"):
                return f["_project_id"]
        return state.active_project_id

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
            form["id"], _form_project_scope(form)
        )
        form["_responses"] = resp_data.get("responses", [])
        form["_count"] = resp_data.get("count", 0)
        # The list route omits schema_json - hydrate the full definition so
        # the field preview is populated.
        if not _form_schema_fields(form):
            full = await forms_service.get_form(form["id"])
            if full:
                form["schema_json"] = full.get("schema_json", [])
                form.setdefault("expires_at", full.get("expires_at", ""))
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

    async def on_edit_form_async(edit_target: dict):
        """Hydrate the form's questions first, then open the editor.

        The list route omits schema_json, so editing straight from the
        dashboard must fetch the full definition before rendering.
        """
        if not _form_schema_fields(edit_target):
            full = await forms_service.get_form(edit_target.get("id", ""))
            if not full:
                _show_error(
                    "Could not load this form's questions. Check connection "
                    "or try again."
                )
                return
            edit_target = {
                **edit_target,
                **{
                    k: full[k]
                    for k in ("schema_json", "expires_at", "is_active")
                    if k in full
                },
            }
            set_active_form(edit_target)
        on_edit_form(edit_target)

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
        new_exp = await forms_service.renew_form(form_id, _form_project_scope(form_id))
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

    async def on_analyze_form_async(form_data: dict):
        """Export responses as a labeled CSV dataset via the standard pipeline.

        Replaces the old inline-JSON cell dump: upload → pd.read_csv → parquet
        snapshot, so the survey becomes a first-class dataset. Provenance is
        recorded so returning to this project re-syncs new submissions.
        """
        from screens.forms.dataset_sync import (
            build_form_file_name,
            export_responses_to_csv,
            record_form_dataset,
            write_csv_temp,
        )

        rows = await forms_service.fetch_all_responses(
            form_data.get("id", ""), _form_project_scope(form_data)
        )
        if not rows:
            _show_error("No responses to analyze yet.")
            return

        file_name = build_form_file_name(
            form_data.get("title", "Survey"), form_data.get("id", "")
        )
        csv_bytes = export_responses_to_csv(form_data, rows)
        local_path = await write_csv_temp(file_name, csv_bytes)

        # Provenance powers the return-to-project auto-refresh.
        await record_form_dataset(
            services.projects,
            state.active_project_id,
            form_data.get("id", ""),
            file_name,
            len(rows),
        )

        # Auto-connect Colab BEFORE handing off — the Analysis handoff waits
        # for a live session, and a cold app would otherwise park the import
        # silently until the user connects manually.
        if not state.active_session_name or not state.colab_connected:
            if page:
                show_snack(
                    page,
                    "🔄 Connecting Colab to load your survey…",
                    duration=3000,
                )
            from screens.analysis.colab_connection import connect_colab_async

            await connect_colab_async(services.colab, page, lambda _v: None)
        if not state.active_session_name:
            _show_error(
                "Could not connect to Colab. Connect in Analysis, then tap "
                "Analyze again — your export is ready."
            )
            return

        logger.info(
            "Survey export ready: %s (%d rows) -> page-scope handoff",
            file_name,
            len(rows),
        )
        if page:
            show_snack(
                page,
                f"📊 Exported {len(rows)} responses - loading as a dataset…",
                duration=3000,
            )
        # Navigate first, then run the import AT PAGE SCOPE: the old pending-
        # effect handoff lived inside the Analysis component, so leaving that
        # screen silently killed the import. A page.run_task keeps running no
        # matter which tab is mounted, and results land in AppState.
        state.current_tab = 1
        if page:

            async def _run_handoff():
                from screens.analysis.dataset_ops import (
                    run_form_dataset_handoff_async,
                )

                await run_form_dataset_handoff_async(
                    page, services.colab, local_path, file_name
                )

            page.run_task(_run_handoff)

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
                            _form_project_scope(active_form),
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
            on_edit=lambda f: page.run_task(on_edit_form_async, f) if page else None,
            on_renew=on_renew_clicked,
            on_download_csv=lambda f: (
                page.run_task(download_csv_async, f, page, _show_error)
                if page
                else None
            ),
            on_analyze=lambda f: (
                page.run_task(on_analyze_form_async, f) if page else None
            ),
            on_delete=lambda fid: (
                page.run_task(
                    delete_form_async,
                    fid,
                    _form_project_scope(fid),
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
