import asyncio
import json
import logging
from datetime import UTC, datetime

import flet as ft

from components.brand_header import build_brand_header
from components.form_editor import TYPE_ICONS, build_form_editor
from components.refresh_button import build_refresh_button
from core import theme, utils
from services import ai as ai_service
from services import forms_service
from services.audio_service import AudioService
from state import AppStateCtx
from state.controller_ctx import ControllerMethodsCtx
from state.service_ctx import ServiceCtx

logger = logging.getLogger(__name__)


@ft.component
def FormsScreen() -> ft.Control:
    page = ft.context.page
    state = ft.use_context(AppStateCtx)
    ft.use_context(ServiceCtx)
    ft.use_context(ControllerMethodsCtx)

    # Mode to switch between views
    mode, set_mode = ft.use_state("dashboard")  # "dashboard", "editor", "detail"

    # State variables
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

    audio_svc = ft.use_ref(lambda: AudioService(page))

    def _show_error(msg: str):
        page.snack_bar = ft.SnackBar(
            ft.Text(msg, color=ft.Colors.WHITE), bgcolor=theme.ERROR, duration=4000
        )
        page.snack_bar.open = True
        page.update()

    async def load_forms():
        set_is_loading(True)
        try:
            forms = await forms_service.list_forms(state.active_project_id)
            set_user_forms(forms)
            state.forms = forms
        except Exception as e:
            logger.error("Failed to load forms: %s", e)
            _show_error("Could not load forms. Check your connection.")
        finally:
            set_is_loading(False)

    def _on_mount():
        page.run_task(load_forms)
        return lambda: None

    ft.use_effect(_on_mount, [])

    async def on_create_form(e=None):
        prompt = prompt_text.strip()
        if not prompt:
            return
        set_is_creating(True)
        try:
            schema = await ai_service.generate_form_schema(prompt)
            if not schema:
                _show_error("AI could not generate a form. Try again.")
                set_is_creating(False)
                return

            set_draft_schema(schema.get("fields", []))
            set_draft_title(schema.get("title", prompt[:50]))
            set_draft_desc(schema.get("description", ""))
            set_mode("editor")
        except Exception as err:
            _show_error(f"Error: {err}")
            logger.exception("Create form error")
        finally:
            set_is_creating(False)

    async def on_ai_edit(action: str, text: str = ""):
        if action == "__set_text__":
            set_ai_edit_text(text)
            return
        if action == "__submit__":
            prompt = (text or ai_edit_text).strip()
            if not prompt:
                return
            set_is_ai_editing(True)
            try:
                edit_prompt = (
                    f"Current form schema:\n{json.dumps(draft_schema, indent=2)}\n\n"
                    f"Title: {draft_title}\n"
                    f"Description: {draft_desc}\n\n"
                    f"User wants to modify: {prompt}\n\n"
                    f"Return the FULL updated form as a JSON object with title, description, fields."
                )
                schema = await ai_service.generate_form_schema(edit_prompt)
                if schema:
                    set_draft_schema(schema.get("fields", draft_schema))
                    set_draft_title(schema.get("title", draft_title))
                    set_draft_desc(schema.get("description", draft_desc))
                    set_ai_edit_text("")
            except Exception as err:
                _show_error(f"AI edit failed: {err}")
            finally:
                set_is_ai_editing(False)
            return
        await on_ai_edit("__submit__", action)

    async def _update_editor_timer():
        while editor_recording:
            await asyncio.sleep(1)
            if editor_recording:
                set_editor_recording_time(editor_recording_time + 1)

    async def _handle_editor_auto_stop(result):
        set_editor_recording(False)
        if result:
            audio_bytes, mime_type = result
            transcript = await ai_service.transcribe_audio(audio_bytes, mime_type)
            if transcript and not transcript.startswith("["):
                set_ai_edit_text(transcript)

    async def on_editor_voice_toggle(e):
        if editor_recording:
            result = await audio_svc.current.stop_recording()
            set_editor_recording(False)
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
                on_auto_stop=lambda res: page.run_task(_handle_editor_auto_stop, res)
            )
            if started:
                set_editor_recording(True)
                set_editor_recording_time(0)
                page.run_task(_update_editor_timer)

    async def on_publish():
        set_is_publishing(True)
        try:
            result = await forms_service.create_form(
                project_id=state.active_project_id,
                title=draft_title,
                description=draft_desc,
                schema_json=draft_schema,
            )
            if result:
                set_mode("dashboard")
                set_draft_schema([])
                set_prompt_text("")
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
            set_is_publishing(False)

    def on_cancel_editor():
        set_mode("dashboard")
        set_draft_schema([])

    async def _update_timer():
        while is_recording:
            await asyncio.sleep(1)
            if is_recording:
                set_recording_time(recording_time + 1)

    async def _handle_auto_stop(result):
        set_is_recording(False)
        if result:
            audio_bytes, mime_type = result
            transcript = await ai_service.transcribe_audio(audio_bytes, mime_type)
            if transcript and not transcript.startswith("["):
                set_prompt_text(transcript)

    async def on_voice_toggle(e):
        if is_recording:
            result = await audio_svc.current.stop_recording()
            set_is_recording(False)
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
                on_auto_stop=lambda res: page.run_task(_handle_auto_stop, res)
            )
            if started:
                set_is_recording(True)
                set_recording_time(0)
                page.run_task(_update_timer)

    async def on_view_form(form: dict):
        set_active_form(form)
        resp_data = await forms_service.get_responses(
            form["id"], state.active_project_id
        )
        form["_responses"] = resp_data.get("responses", [])
        form["_count"] = resp_data.get("count", 0)
        set_active_form(form)
        set_mode("detail")

    def on_back_to_list(e=None):
        set_active_form(None)
        set_mode("dashboard")

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
            page.close_dialog()

        async def _confirm_delete(e=None):
            _close_dlg()
            set_is_loading(True)
            success = await forms_service.delete_form(form_id, state.active_project_id)
            if success:
                set_active_form(None)
                set_mode("dashboard")
                page.snack_bar = ft.SnackBar(
                    ft.Text("Form permanently deleted from project."), duration=2000
                )
                page.snack_bar.open = True
                await load_forms()
            else:
                set_is_loading(False)
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
        page.open_dialog(confirm_dlg)

    async def on_download_csv(form: dict):
        responses = form.get("_responses", [])
        if not responses:
            _show_error("No responses to download.")
            return
        csv_bytes = forms_service.responses_to_csv_bytes(responses)

        picker = getattr(page, "file_picker", None)
        if not picker:
            picker = ft.FilePicker()
            page.overlay.append(picker)
            page.update()

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
        rows_json = _json.dumps(rows[:200], default=str)
        code = (
            f"import pandas as pd\n"
            f"import json\n\n"
            f"data = json.loads('''{rows_json}''')\n"
            f"df = pd.DataFrame(data)\n"
            f'print(f"Loaded {{len(df)}} responses, {{len(df.columns)}} fields")\n'
            f"df.head()"
        )
        state.add_cell("code", code)
        await page.push_route("/notebook")

    # Layout functions
    def render_form_card(form: dict) -> ft.Container:
        is_expired = False
        try:
            exp = datetime.fromisoformat(form["expires_at"])
            is_expired = exp < datetime.now(UTC)
        except Exception:
            pass
        status_color = theme.ERROR if is_expired else theme.SUCCESS
        status_text = "Expired" if is_expired else "Active"
        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(
                                form["title"],
                                weight="bold",
                                size=14,
                                max_lines=1,
                                overflow="ellipsis",
                            ),
                            ft.Row(
                                [
                                    ft.Container(
                                        content=ft.Text(
                                            status_text,
                                            size=9,
                                            color=status_color,
                                            weight="bold",
                                        ),
                                        padding=ft.Padding(6, 2, 6, 2),
                                        border_radius=4,
                                        bgcolor=ft.Colors.with_opacity(
                                            0.1, status_color
                                        ),
                                    ),
                                    ft.Text(
                                        f"{form.get('response_count', 0)} responses",
                                        size=11,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                ],
                                spacing=8,
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.IconButton(
                        ft.Icons.ARROW_FORWARD_IOS_ROUNDED,
                        icon_size=16,
                        on_click=lambda e, f=form: page.run_task(on_view_form, f),
                    ),
                ]
            ),
            padding=14,
            border_radius=12,
            bgcolor=theme.GLASS_BG,
            border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
            margin=ft.Margin(20, 0, 20, 8),
            on_click=lambda e, f=form: page.run_task(on_view_form, f),
            ink=True,
        )

    def render_dashboard():
        form_list_content = []
        if is_loading:
            form_list_content = [
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
        elif not user_forms:
            form_list_content = [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.DYNAMIC_FORM_ROUNDED,
                                size=48,
                                color=ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE),
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
            form_list_content = [render_form_card(form) for form in user_forms]

        return ft.Column(
            [
                build_brand_header(show_tagline=True, spacing_below=True),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Create a Survey", weight="bold", size=16),
                            ft.Text(
                                "Describe your questionnaire, we will generate it, and you can edit before publishing.",
                                size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Container(height=8),
                            ft.Row(
                                [
                                    ft.TextField(
                                        value=prompt_text,
                                        hint_text="e.g. A questionnaire on employee satisfaction",
                                        expand=True,
                                        border_radius=12,
                                        max_lines=3,
                                        min_lines=1,
                                        on_change=lambda e: set_prompt_text(
                                            e.control.value
                                        ),
                                        on_submit=lambda e: page.run_task(
                                            on_create_form, e
                                        ),
                                        disabled=is_creating or is_recording,
                                    ),
                                    ft.Row(
                                        [
                                            ft.Text(
                                                value=f"00:{recording_time:02d} / 01:00",
                                                size=11,
                                                color=theme.ERROR,
                                                weight="bold",
                                                visible=is_recording,
                                            ),
                                            ft.IconButton(
                                                icon=ft.Icons.STOP_ROUNDED
                                                if is_recording
                                                else ft.Icons.MIC_ROUNDED,
                                                icon_color=theme.ERROR
                                                if is_recording
                                                else theme.ACCENT,
                                                tooltip="Stop"
                                                if is_recording
                                                else "Voice",
                                                on_click=lambda e: page.run_task(
                                                    on_voice_toggle, e
                                                ),
                                                disabled=is_creating,
                                            ),
                                        ],
                                        spacing=2,
                                        vertical_alignment="center",
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.SEND_ROUNDED,
                                        icon_color=theme.PRIMARY,
                                        on_click=lambda e: page.run_task(
                                            on_create_form, e
                                        ),
                                        disabled=is_creating or is_recording,
                                    ),
                                ],
                                spacing=4,
                                vertical_alignment="center",
                            ),
                            ft.ProgressBar(visible=is_creating or is_transcribing),
                            ft.Row(
                                [
                                    ft.ProgressRing(
                                        width=16, height=16, stroke_width=2
                                    ),
                                    ft.Text(
                                        "Transcribing your voice...",
                                        size=12,
                                        color=theme.ACCENT,
                                    ),
                                ],
                                spacing=8,
                                alignment="center",
                                visible=is_transcribing,
                            ),
                        ],
                        spacing=4,
                    ),
                    padding=16,
                    margin=ft.Margin(20, 0, 20, 10),
                    border_radius=16,
                    bgcolor=theme.GLASS_BG,
                    border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "SPONSORED",
                                size=8,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                style=ft.TextStyle(letter_spacing=1),
                            ),
                            utils.get_banner_ad(
                                unit_id="ca-app-pub-5679949845754640/5628404223",
                                width=320,
                                height=50,
                            ),
                        ],
                        horizontal_alignment="center",
                        spacing=4,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=8,
                    border_radius=12,
                    bgcolor=theme.GLASS_BG,
                    border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                    margin=ft.Margin(20, 4, 20, 10),
                )
                if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
                else ft.Container(),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Text("Your Forms", weight="bold", size=16),
                            build_refresh_button(
                                on_click=lambda e: page.run_task(load_forms),
                            ),
                        ],
                        alignment="spaceBetween",
                    ),
                    padding=ft.Padding(20, 16, 20, 4),
                ),
                ft.Column(controls=form_list_content),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "SPONSORED",
                                size=8,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                style=ft.TextStyle(letter_spacing=1),
                            ),
                            utils.get_banner_ad(
                                unit_id="ca-app-pub-5679949845754640/5628404223",
                                width=320,
                                height=50,
                            ),
                        ],
                        horizontal_alignment="center",
                        spacing=4,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=8,
                    border_radius=12,
                    bgcolor=theme.GLASS_BG,
                    border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                    margin=ft.Margin(20, 10, 20, 10),
                )
                if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
                else ft.Container(),
                ft.Container(height=100),
            ]
        )

    def render_editor():
        return ft.Column(
            build_form_editor(
                schema=draft_schema,
                title=draft_title,
                description=draft_desc,
                on_schema_changed=lambda: None,  # State auto re-renders
                on_title_changed=set_draft_title,
                on_desc_changed=set_draft_desc,
                on_publish=lambda: page.run_task(on_publish),
                on_cancel=on_cancel_editor,
                on_ai_edit=lambda action, text="": page.run_task(
                    on_ai_edit, action, text
                ),
                on_voice_toggle=lambda e: page.run_task(on_editor_voice_toggle, e),
                is_publishing=is_publishing,
                is_recording=editor_recording,
                is_transcribing=editor_transcribing,
                is_ai_editing=is_ai_editing,
                recording_time=editor_recording_time,
                ai_prompt_text=ai_edit_text,
                recording_timer_ref=None,
            )
        )

    def render_detail():
        if not active_form:
            return ft.Container()

        form = active_form
        controls = []
        controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.IconButton(
                            ft.Icons.ARROW_BACK_ROUNDED, on_click=on_back_to_list
                        ),
                        ft.Text(form["title"], weight="bold", size=16, expand=True),
                    ]
                ),
                padding=ft.Padding(20, 0, 20, 0),
            )
        )
        resp_count = form.get("_count", form.get("response_count", 0))
        controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.PEOPLE_ROUNDED, size=16, color=theme.ACCENT
                                ),
                                ft.Text(f"{resp_count} responses", weight="w500"),
                            ],
                            spacing=8,
                        ),
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.TIMER_ROUNDED, size=16, color=theme.WARNING
                                ),
                                ft.Text(
                                    f"Expires: {form.get('expires_at', '')[:10]}",
                                    size=12,
                                ),
                            ],
                            spacing=8,
                        ),
                    ],
                    spacing=8,
                ),
                padding=16,
                margin=ft.Margin(20, 8, 20, 8),
                border_radius=12,
                bgcolor=theme.GLASS_BG,
                border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
            )
        )

        schema_json = form.get("schema_json", "")
        fields = []
        if isinstance(schema_json, str) and schema_json:
            try:
                fields = json.loads(schema_json)
            except Exception:
                pass
        elif isinstance(schema_json, list):
            fields = schema_json

        if fields:
            field_controls = []
            for idx, field in enumerate(fields):
                label = field.get("label", field.get("name", f"Field {idx + 1}"))
                ftype = field.get("type", "text")
                required = field.get("required", False)
                options = field.get("options", [])
                field_controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(
                                    TYPE_ICONS.get(ftype, ft.Icons.TEXT_FIELDS),
                                    size=16,
                                    color=theme.ACCENT,
                                ),
                                ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Text(
                                                    label,
                                                    size=13,
                                                    weight="w500",
                                                    expand=True,
                                                ),
                                                ft.Container(
                                                    content=ft.Text(
                                                        ftype.upper(),
                                                        size=9,
                                                        color=theme.PRIMARY,
                                                        weight="bold",
                                                    ),
                                                    padding=ft.Padding(6, 2, 6, 2),
                                                    border_radius=4,
                                                    bgcolor=ft.Colors.with_opacity(
                                                        0.08, theme.PRIMARY
                                                    ),
                                                ),
                                                ft.Text(
                                                    "*",
                                                    size=14,
                                                    color=theme.ERROR,
                                                    weight="bold",
                                                )
                                                if required
                                                else ft.Container(),
                                            ],
                                            spacing=6,
                                        ),
                                        ft.Text(
                                            ", ".join(options[:5]),
                                            size=10,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                            max_lines=1,
                                            overflow="ellipsis",
                                        )
                                        if options
                                        else ft.Container(),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                            ],
                            spacing=10,
                            vertical_alignment="start",
                        ),
                        padding=ft.Padding(12, 8, 12, 8),
                        border_radius=8,
                        bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.ON_SURFACE),
                    )
                )
            controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                f"Form Fields ({len(fields)})", weight="bold", size=13
                            ),
                            ft.Column(field_controls, spacing=4),
                        ],
                        spacing=8,
                    ),
                    padding=ft.Padding(20, 8, 20, 8),
                )
            )

        controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.FilledButton(
                                    "Copy Link",
                                    icon=ft.Icons.LINK_ROUNDED,
                                    style=ft.ButtonStyle(
                                        bgcolor=theme.PRIMARY,
                                        color=ft.Colors.WHITE,
                                        shape=ft.RoundedRectangleBorder(radius=12),
                                        padding=14,
                                    ),
                                    on_click=lambda e: page.run_task(
                                        on_copy_link, form["id"]
                                    ),
                                ),
                                ft.FilledButton(
                                    "Renew +7d",
                                    icon=ft.Icons.UPDATE_ROUNDED,
                                    style=ft.ButtonStyle(
                                        bgcolor=theme.PRIMARY,
                                        color=ft.Colors.WHITE,
                                        shape=ft.RoundedRectangleBorder(radius=12),
                                        padding=14,
                                    ),
                                    on_click=lambda e: page.run_task(
                                        on_renew_form, form["id"]
                                    ),
                                ),
                            ],
                            spacing=8,
                            wrap=True,
                        ),
                        ft.Row(
                            [
                                ft.FilledButton(
                                    "Download CSV",
                                    icon=ft.Icons.DOWNLOAD_ROUNDED,
                                    style=ft.ButtonStyle(
                                        bgcolor=theme.PRIMARY,
                                        color=ft.Colors.WHITE,
                                        shape=ft.RoundedRectangleBorder(radius=12),
                                        padding=14,
                                    ),
                                    on_click=lambda e: page.run_task(
                                        on_download_csv, form
                                    ),
                                ),
                                ft.FilledButton(
                                    "Analyze",
                                    icon=ft.Icons.ANALYTICS_ROUNDED,
                                    style=ft.ButtonStyle(
                                        bgcolor=theme.PRIMARY,
                                        color=ft.Colors.WHITE,
                                        shape=ft.RoundedRectangleBorder(radius=12),
                                        padding=14,
                                    ),
                                    on_click=lambda e: page.run_task(
                                        on_analyze_responses, form
                                    ),
                                ),
                            ],
                            spacing=8,
                            wrap=True,
                        ),
                        ft.TextButton(
                            "Delete Form",
                            icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                            style=ft.ButtonStyle(
                                color=theme.ERROR,
                                shape=ft.RoundedRectangleBorder(radius=12),
                            ),
                            on_click=lambda e: page.run_task(
                                on_delete_form, form["id"]
                            ),
                        ),
                    ],
                    spacing=8,
                ),
                padding=ft.Padding(20, 8, 20, 8),
            )
        )

        responses = form.get("_responses", [])
        if responses:
            rows_data = [r["data"] for r in responses[:50]]
            if rows_data:
                columns = []
                for row in rows_data:
                    for key in row:
                        if key not in columns:
                            columns.append(key)

                controls.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    f"Latest {min(50, len(responses))} Responses",
                                    weight="bold",
                                    size=13,
                                ),
                                ft.DataTable(
                                    columns=[
                                        ft.DataColumn(ft.Text(c, size=11))
                                        for c in columns
                                    ],
                                    rows=[
                                        ft.DataRow(
                                            cells=[
                                                ft.DataCell(
                                                    ft.Text(
                                                        str(row.get(c, "")), size=11
                                                    )
                                                )
                                                for c in columns
                                            ]
                                        )
                                        for row in rows_data
                                    ],
                                    column_spacing=16,
                                    horizontal_lines=ft.BorderSide(
                                        0.5, ft.Colors.OUTLINE_VARIANT
                                    ),
                                ),
                            ],
                            spacing=8,
                        ),
                        padding=ft.Padding(20, 8, 20, 8),
                    )
                )
        if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
            controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "SPONSORED",
                                size=8,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                style=ft.TextStyle(letter_spacing=1),
                            ),
                            utils.get_banner_ad(
                                unit_id="ca-app-pub-5679949845754640/5628404223",
                                width=320,
                                height=50,
                            ),
                        ],
                        horizontal_alignment="center",
                        spacing=4,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=8,
                    border_radius=12,
                    bgcolor=theme.GLASS_BG,
                    border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                    margin=ft.Margin(20, 8, 20, 8),
                )
            )

        controls.append(ft.Container(height=100))
        return ft.Column(controls)

    return ft.Column(
        controls=[
            render_dashboard()
            if mode == "dashboard"
            else (render_editor() if mode == "editor" else render_detail())
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
