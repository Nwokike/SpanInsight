from __future__ import annotations

import asyncio
import json
import logging

import flet as ft

from components.form_editor import build_form_editor
from core import theme
from core.state import state
from services import ai as ai_service
from services import forms_service
from services.audio_service import AudioService

from .dashboard import build_dashboard_layout, build_form_card
from .detail import build_form_detail
from .state import FormsState

logger = logging.getLogger(__name__)


def build_forms_view(page: ft.Page) -> ft.View:
    ui_state = FormsState()
    audio_svc = AudioService(page)

    async def load_forms():
        ui_state.is_loading["value"] = True
        _rebuild()
        try:
            forms = await forms_service.list_forms(state.active_project_id)
            ui_state.user_forms.clear()
            ui_state.user_forms.extend(forms)

            state.forms = forms
        except Exception as e:
            logger.error("Failed to load forms: %s", e)
            _show_error("Could not load forms. Check your connection.")
        finally:
            ui_state.is_loading["value"] = False
            _rebuild()

    async def on_create_form(e):
        if not ui_state.form_prompt_field.current:
            return
        prompt = ui_state.form_prompt_field.current.value.strip()
        if not prompt:
            return
        ui_state.is_creating["value"] = True
        _rebuild()
        try:
            schema = await ai_service.generate_form_schema(prompt)
            if not schema:
                _show_error("AI could not generate a form. Try again.")
                ui_state.is_creating["value"] = False
                _rebuild()
                return

            ui_state.draft_schema.clear()
            ui_state.draft_schema.extend(schema.get("fields", []))
            ui_state.draft_title["value"] = schema.get("title", prompt[:50])
            ui_state.draft_desc["value"] = schema.get("description", "")
            ui_state.editor_active["value"] = True
        except Exception as err:
            _show_error(f"Error: {err}")
            logger.exception("Create form error")
        finally:
            ui_state.is_creating["value"] = False
            _rebuild()

    async def on_ai_edit(action: str, text: str = ""):
        if action == "__set_text__":
            ui_state.ai_edit_text["value"] = text
            return
        if action == "__submit__":
            prompt = (text or ui_state.ai_edit_text["value"]).strip()
            if not prompt:
                return
            ui_state.is_ai_editing["value"] = True
            _rebuild()
            try:
                edit_prompt = (
                    f"Current form schema:\n{json.dumps(ui_state.draft_schema, indent=2)}\n\n"
                    f"Title: {ui_state.draft_title['value']}\n"
                    f"Description: {ui_state.draft_desc['value']}\n\n"
                    f"User wants to modify: {prompt}\n\n"
                    f"Return the FULL updated form as a JSON object with title, description, fields."
                )
                schema = await ai_service.generate_form_schema(edit_prompt)
                if schema:
                    ui_state.draft_schema.clear()
                    ui_state.draft_schema.extend(
                        schema.get("fields", ui_state.draft_schema)
                    )
                    ui_state.draft_title["value"] = schema.get(
                        "title", ui_state.draft_title["value"]
                    )
                    ui_state.draft_desc["value"] = schema.get(
                        "description", ui_state.draft_desc["value"]
                    )
                    ui_state.ai_edit_text["value"] = ""
            except Exception as err:
                _show_error(f"AI edit failed: {err}")
            finally:
                ui_state.is_ai_editing["value"] = False
                _rebuild()
            return
        await on_ai_edit("__submit__", action)

    async def on_editor_voice_toggle(e):
        if ui_state.editor_recording["value"]:
            result = await audio_svc.stop_recording()
            ui_state.editor_recording["value"] = False
            ui_state.editor_transcribing["value"] = True
            _rebuild()
            if result:
                audio_bytes, mime_type = result
                try:
                    transcript = await ai_service.transcribe_audio(
                        audio_bytes, mime_type
                    )
                    if transcript and not transcript.startswith("["):
                        ui_state.ai_edit_text["value"] = transcript
                    else:
                        _show_error("Could not transcribe audio. Try again.")
                except Exception as err:
                    _show_error(f"Transcription failed: {err}")
            else:
                _show_error("No audio recorded.")
            ui_state.editor_transcribing["value"] = False
            _rebuild()
        else:
            started = await audio_svc.start_recording(
                on_auto_stop=lambda res: page.run_task(_handle_editor_auto_stop, res)
            )
            if started:
                ui_state.editor_recording["value"] = True
                ui_state.editor_recording_time["value"] = 0
                _rebuild()
                page.run_task(_update_editor_timer)

    async def _update_editor_timer():
        while ui_state.editor_recording["value"]:
            await asyncio.sleep(1)
            if ui_state.editor_recording["value"]:
                ui_state.editor_recording_time["value"] += 1
                if ui_state.editor_recording_timer.current:
                    ui_state.editor_recording_timer.current.value = (
                        f"00:{ui_state.editor_recording_time['value']:02d} / 01:00"
                    )
                    page.update(ui_state.editor_recording_timer.current)

    async def _handle_editor_auto_stop(result):
        ui_state.editor_recording["value"] = False
        _rebuild()
        if result:
            audio_bytes, mime_type = result
            transcript = await ai_service.transcribe_audio(audio_bytes, mime_type)
            if transcript and not transcript.startswith("["):
                ui_state.ai_edit_text["value"] = transcript
                _rebuild()

    async def on_publish():
        ui_state.is_publishing["value"] = True
        _rebuild()
        try:
            result = await forms_service.create_form(
                project_id=state.active_project_id,
                title=ui_state.draft_title["value"],
                description=ui_state.draft_desc["value"],
                schema_json=ui_state.draft_schema,
            )
            if result:
                ui_state.editor_active["value"] = False
                ui_state.draft_schema.clear()
                ui_state.prompt_text["value"] = ""
                if ui_state.form_prompt_field.current:
                    ui_state.form_prompt_field.current.value = ""
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Published! Link: {result['url']}"), duration=5000
                )
                page.snack_bar.open = True
                try:
                    await ft.Clipboard().set(result["url"])
                except Exception:
                    pass
                await load_forms()
            else:
                _show_error("Publish failed. Check connection.")
        except Exception as err:
            _show_error(f"Error: {err}")
        finally:
            ui_state.is_publishing["value"] = False
            _rebuild()

    def on_cancel_editor():
        ui_state.editor_active["value"] = False
        ui_state.draft_schema.clear()
        _rebuild()

    async def on_voice_toggle(e):
        if ui_state.is_recording["value"]:
            result = await audio_svc.stop_recording()
            ui_state.is_recording["value"] = False
            ui_state.is_transcribing["value"] = True
            _rebuild()
            if result:
                audio_bytes, mime_type = result
                try:
                    transcript = await ai_service.transcribe_audio(
                        audio_bytes, mime_type
                    )
                    if transcript and not transcript.startswith("["):
                        ui_state.prompt_text["value"] = transcript
                        if ui_state.form_prompt_field.current:
                            ui_state.form_prompt_field.current.value = transcript
                    else:
                        _show_error("Could not transcribe audio. Try again.")
                except Exception as err:
                    _show_error(f"Transcription failed: {err}")
            else:
                _show_error("No audio recorded.")
            ui_state.is_transcribing["value"] = False
            _rebuild()
        else:
            started = await audio_svc.start_recording(
                on_auto_stop=lambda res: page.run_task(_handle_auto_stop, res)
            )
            if started:
                ui_state.is_recording["value"] = True
                ui_state.recording_time["value"] = 0
                _rebuild()
                page.run_task(_update_timer)

    async def _update_timer():
        while ui_state.is_recording["value"]:
            await asyncio.sleep(1)
            if ui_state.is_recording["value"]:
                ui_state.recording_time["value"] += 1
                if ui_state.recording_timer.current:
                    ui_state.recording_timer.current.value = (
                        f"00:{ui_state.recording_time['value']:02d} / 01:00"
                    )
                    page.update(ui_state.recording_timer.current)

    async def _handle_auto_stop(result):
        ui_state.is_recording["value"] = False
        _rebuild()
        if result:
            audio_bytes, mime_type = result
            transcript = await ai_service.transcribe_audio(audio_bytes, mime_type)
            if (
                transcript
                and not transcript.startswith("[")
                and ui_state.form_prompt_field.current
            ):
                ui_state.form_prompt_field.current.value = transcript
                page.update()

    async def on_view_form(form: dict):
        ui_state.active_form["data"] = form
        resp_data = await forms_service.get_responses(
            form["id"], state.active_project_id
        )
        ui_state.active_form["data"]["_responses"] = resp_data.get("responses", [])
        ui_state.active_form["data"]["_count"] = resp_data.get("count", 0)
        _rebuild()

    def on_back_to_list(e):
        ui_state.active_form["data"] = None
        _rebuild()

    async def on_copy_link(form_id: str):
        url = f"https://f.spaninsight.com/{form_id}"
        try:
            await ft.Clipboard().set(url)
        except Exception:
            pass
        page.snack_bar = ft.SnackBar(ft.Text("Link copied!"), duration=2000)
        page.snack_bar.open = True
        page.update()

    async def on_renew_form(form_id: str):
        new_exp = await forms_service.renew_form(form_id, state.active_project_id)
        if new_exp:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Extended to {new_exp[:10]}"), duration=3000
            )
            page.snack_bar.open = True
            await load_forms()
        else:
            _show_error("Failed to renew.")

    async def on_delete_form(form_id: str):
        def _close_dlg(e=None):
            page.pop_dialog()

        async def _confirm_delete(e=None):
            _close_dlg()
            ui_state.is_loading["value"] = True
            _rebuild()
            success = await forms_service.delete_form(form_id, state.active_project_id)
            if success:
                ui_state.active_form["data"] = None
                page.snack_bar = ft.SnackBar(
                    ft.Text("Form permanently deleted from project."), duration=2000
                )
                page.snack_bar.open = True
                await load_forms()
            else:
                ui_state.is_loading["value"] = False
                _rebuild()
                _show_error("Failed to delete form from edge database.")

        confirm_dlg = ft.AlertDialog(
            title=ft.Text("Delete Shared Form?"),
            content=ft.Container(
                content=ft.Text(
                    "Anyone with access to this project PIN can edit or delete items. "
                    "Deleting this form will permanently remove it and all collected responses "
                    "from the cloud node for all collaborators. This cannot be undone.",
                    size=13,
                ),
                width=340,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=_close_dlg),
                ft.FilledButton(
                    "Delete",
                    bgcolor=theme.ERROR,
                    color=ft.Colors.WHITE,
                    on_click=lambda e: page.run_task(_confirm_delete),
                ),
            ],
        )
        page.show_dialog(confirm_dlg)

    async def on_download_csv(form: dict):
        responses = form.get("_responses", [])
        if not responses:
            _show_error("No responses to download.")
            return
        csv_bytes = forms_service.responses_to_csv_bytes(responses)
        picker = ft.FilePicker()

        async def _do_save():
            result = await picker.save_file(
                dialog_title="Save Responses CSV",
                file_name=f"{form['title'].replace(' ', '_')}_responses.csv",
                allowed_extensions=["csv"],
            )
            if result:
                try:

                    def _write_csv():
                        with open(result, "wb") as f:
                            f.write(csv_bytes)

                    await asyncio.to_thread(_write_csv)
                    page.snack_bar = ft.SnackBar(ft.Text("Saved!"), duration=3000)
                    page.snack_bar.open = True
                    page.update()
                except Exception as err:
                    _show_error(f"Save failed: {err}")

        page.run_task(_do_save)

    async def on_analyze_responses(form: dict):
        responses = form.get("_responses", [])
        if not responses:
            _show_error("No responses to analyze.")
            return

        import json as _json

        rows = [r["data"] for r in responses]
        # Generate a Python code snippet for Colab to load the data
        rows_json = _json.dumps(rows[:200], default=str)
        code = (
            f"import pandas as pd\n"
            f"import json\n\n"
            f"data = json.loads('''{rows_json}''')\n"
            f"df = pd.DataFrame(data)\n"
            f'print(f"Loaded {{len(df)}} responses, {{len(df.columns)}} fields")\n'
            f"df.head()"
        )
        # Add a notebook cell with this code
        state.add_cell("code", code)
        await page.push_route("/notebook")

    def _show_error(msg: str):
        page.snack_bar = ft.SnackBar(
            ft.Text(msg, color=ft.Colors.WHITE), bgcolor=theme.ERROR, duration=4000
        )
        page.snack_bar.open = True
        page.update()

    def _rebuild():
        try:
            _rebuild_unsafe()
        except Exception as ex:
            logger.debug("Bypassed rebuild during navigation: %s", ex)

    def _rebuild_unsafe():
        if not ui_state.content_column.current:
            return

        show_editor = ui_state.editor_active["value"]
        show_detail = ui_state.active_form["data"] is not None
        show_dashboard = not show_editor and not show_detail

        for ref, vis in [
            (ui_state.dashboard_container_ref, show_dashboard),
            (ui_state.editor_container_ref, show_editor),
            (ui_state.detail_container_ref, show_detail),
        ]:
            if ref.current and ref.current.visible != vis:
                ref.current.visible = vis
                ref.current.update()

        if show_editor:
            if ui_state.editor_container_ref.current:
                ui_state.editor_container_ref.current.content = ft.Column(
                    build_form_editor(
                        schema=ui_state.draft_schema,
                        title=ui_state.draft_title["value"],
                        description=ui_state.draft_desc["value"],
                        on_schema_changed=_rebuild,
                        on_title_changed=lambda v: (
                            ui_state.draft_title.__setitem__("value", v),
                        ),
                        on_desc_changed=lambda v: (
                            ui_state.draft_desc.__setitem__("value", v),
                        ),
                        on_publish=lambda: page.run_task(on_publish),
                        on_cancel=on_cancel_editor,
                        on_ai_edit=lambda action, text="": page.run_task(
                            on_ai_edit, action, text
                        ),
                        on_voice_toggle=lambda e: page.run_task(
                            on_editor_voice_toggle, e
                        ),
                        is_publishing=ui_state.is_publishing["value"],
                        is_recording=ui_state.editor_recording["value"],
                        is_transcribing=ui_state.editor_transcribing["value"],
                        is_ai_editing=ui_state.is_ai_editing["value"],
                        recording_time=ui_state.editor_recording_time["value"],
                        ai_prompt_text=ui_state.ai_edit_text["value"],
                        recording_timer_ref=ui_state.editor_recording_timer,
                    )
                )
                ui_state.editor_container_ref.current.update()

        elif show_detail:
            if ui_state.detail_container_ref.current:
                ui_state.detail_container_ref.current.content = ft.Column(
                    build_form_detail(
                        form=ui_state.active_form["data"],
                        on_back_to_list=on_back_to_list,
                        on_copy_link=on_copy_link,
                        on_renew_form=on_renew_form,
                        on_download_csv=on_download_csv,
                        on_analyze_responses=on_analyze_responses,
                        on_delete_form=on_delete_form,
                        page=page,
                    )
                )
                ui_state.detail_container_ref.current.update()

        else:
            if ui_state.dashboard_container_ref.current:
                if (
                    not ui_state.dashboard_container_ref.current.content
                    or not isinstance(
                        ui_state.dashboard_container_ref.current.content, ft.Column
                    )
                ):
                    ui_state.dashboard_container_ref.current.content = (
                        build_dashboard_layout(
                            ui_state=ui_state,
                            page=page,
                            on_create_form=on_create_form,
                            on_voice_toggle=on_voice_toggle,
                            load_forms=load_forms,
                        )
                    )
                    ui_state.dashboard_container_ref.current.update()

                if ui_state.form_prompt_field.current:
                    ui_state.form_prompt_field.current.disabled = (
                        ui_state.is_creating["value"] or ui_state.is_recording["value"]
                    )
                    ui_state.form_prompt_field.current.update()

                if ui_state.recording_timer.current:
                    ui_state.recording_timer.current.value = (
                        f"00:{ui_state.recording_time['value']:02d} / 01:00"
                    )
                    ui_state.recording_timer.current.visible = ui_state.is_recording[
                        "value"
                    ]
                    ui_state.recording_timer.current.update()

                if ui_state.dashboard_voice_button_ref.current:
                    ui_state.dashboard_voice_button_ref.current.icon = (
                        ft.Icons.STOP_ROUNDED
                        if ui_state.is_recording["value"]
                        else ft.Icons.MIC_ROUNDED
                    )
                    ui_state.dashboard_voice_button_ref.current.icon_color = (
                        theme.ERROR if ui_state.is_recording["value"] else theme.ACCENT
                    )
                    ui_state.dashboard_voice_button_ref.current.tooltip = (
                        "Stop" if ui_state.is_recording["value"] else "Voice"
                    )
                    ui_state.dashboard_voice_button_ref.current.disabled = (
                        ui_state.is_creating["value"]
                    )
                    ui_state.dashboard_voice_button_ref.current.update()

                if ui_state.dashboard_send_button_ref.current:
                    ui_state.dashboard_send_button_ref.current.disabled = (
                        ui_state.is_creating["value"] or ui_state.is_recording["value"]
                    )
                    ui_state.dashboard_send_button_ref.current.update()

                if ui_state.dashboard_progress_bar_ref.current:
                    ui_state.dashboard_progress_bar_ref.current.visible = (
                        ui_state.is_creating["value"]
                        or ui_state.is_transcribing["value"]
                    )
                    ui_state.dashboard_progress_bar_ref.current.update()

                if ui_state.user_forms_column_ref.current:
                    if ui_state.is_loading["value"]:
                        ui_state.user_forms_column_ref.current.controls = [
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.ProgressRing(width=16, height=16),
                                        ft.Text("Loading forms..."),
                                    ],
                                    spacing=10,
                                    alignment="center",
                                ),
                                padding=20,
                            )
                        ]
                    elif not ui_state.user_forms:
                        ui_state.user_forms_column_ref.current.controls = [
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Icon(
                                            ft.Icons.DYNAMIC_FORM_ROUNDED,
                                            size=48,
                                            color=ft.Colors.with_opacity(
                                                0.2, ft.Colors.ON_SURFACE
                                            ),
                                        ),
                                        ft.Text(
                                            "No forms yet",
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                            size=13,
                                        ),
                                        ft.Text(
                                            "Describe a survey topic above to generate your first form.",
                                            size=11,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                            text_align="center",
                                        ),
                                    ],
                                    spacing=8,
                                    horizontal_alignment="center",
                                ),
                                padding=40,
                                alignment=ft.Alignment.CENTER,
                            )
                        ]
                    else:
                        ui_state.user_forms_column_ref.current.controls = [
                            build_form_card(form, on_view_form, page)
                            for form in ui_state.user_forms
                        ]
                    ui_state.user_forms_column_ref.current.update()

    page.run_task(load_forms)

    return ft.View(
        route="/forms",
        appbar=ft.AppBar(
            title=ft.Text("Forms", weight="bold"), bgcolor=ft.Colors.TRANSPARENT
        ),
        controls=[
            ft.Column(
                ref=ui_state.content_column,
                controls=[
                    ft.Container(
                        ref=ui_state.dashboard_container_ref,
                        visible=True,
                        content=build_dashboard_layout(
                            ui_state=ui_state,
                            page=page,
                            on_create_form=on_create_form,
                            on_voice_toggle=on_voice_toggle,
                            load_forms=load_forms,
                        ),
                    ),
                    ft.Container(
                        ref=ui_state.editor_container_ref,
                        visible=False,
                        content=ft.Column([]),
                    ),
                    ft.Container(
                        ref=ui_state.detail_container_ref,
                        visible=False,
                        content=ft.Column([]),
                    ),
                ],
                scroll="auto",
                expand=True,
            )
        ],
        padding=0,
    )
