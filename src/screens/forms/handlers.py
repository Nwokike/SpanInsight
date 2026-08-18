"""Business logic and async handlers for Forms screen."""

from __future__ import annotations

import asyncio
import json
import logging

import flet as ft

from core import theme
from services import ai as ai_service
from services import forms_service

logger = logging.getLogger("FormsHandlers")


async def load_forms_async(
    active_project_id: str, state, set_user_forms, set_is_loading, show_error
):
    """Fetch all forms belonging to active project from backend."""
    set_is_loading(True)
    try:
        forms = await forms_service.list_forms(active_project_id)
        set_user_forms(forms)
        state.forms = forms
    except Exception as e:
        logger.error("Failed to load forms: %s", e)
        show_error("Could not load forms. Check your connection.")
    finally:
        set_is_loading(False)


async def create_form_schema_async(
    prompt_text: str,
    set_is_creating,
    set_draft_schema,
    set_draft_title,
    set_draft_desc,
    set_mode,
    show_error,
):
    """Generate structured form schema with AI from natural language description."""
    prompt = prompt_text.strip()
    if not prompt:
        return
    set_is_creating(True)
    try:
        schema = await ai_service.generate_form_schema(prompt)
        if not schema:
            show_error("AI could not generate a form. Try again.")
            return

        set_draft_schema(schema.get("fields", []))
        set_draft_title(schema.get("title", prompt[:50]))
        set_draft_desc(schema.get("description", ""))
        set_mode("editor")
    except Exception as err:
        show_error(f"Error: {err}")
        logger.exception("Create form error")
    finally:
        set_is_creating(False)


async def ai_edit_schema_async(
    action: str,
    text: str,
    ai_edit_text: str,
    draft_schema: list,
    draft_title: str,
    draft_desc: str,
    set_ai_edit_text,
    set_is_ai_editing,
    set_draft_schema,
    set_draft_title,
    set_draft_desc,
    show_error,
):
    """Modify existing draft schema using AI prompts."""
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
            show_error(f"AI edit failed: {err}")
        finally:
            set_is_ai_editing(False)


async def publish_form_async(
    active_project_id: str,
    draft_title: str,
    draft_desc: str,
    draft_schema: list,
    page: ft.Page,
    set_is_publishing,
    set_mode,
    set_draft_schema,
    set_prompt_text,
    load_forms_fn,
    show_error,
):
    """Publish form schema to the cloud and copy share link to clipboard."""
    set_is_publishing(True)
    try:
        result = await forms_service.create_form(
            project_id=active_project_id,
            title=draft_title,
            description=draft_desc,
            schema_json=draft_schema,
        )
        if result:
            set_mode("dashboard")
            set_draft_schema([])
            set_prompt_text("")
            if page:
                from core.utils import show_snack

                show_snack(
                    page,
                    f"Published! Link: {result['url']}",
                    success=True,
                    duration=5000,
                )
            try:
                await page.set_clipboard_async(result["url"])
            except Exception:
                pass
            await load_forms_fn()
        else:
            show_error("Publish failed. Please check connection or try again.")
    except Exception as err:
        show_error(f"Publish error: {err}")
    finally:
        set_is_publishing(False)


async def delete_form_async(
    form_id: str,
    active_project_id: str,
    page: ft.Page,
    set_is_loading,
    set_active_form,
    set_mode,
    load_forms_fn,
    show_error,
):
    """Shows delete confirmation dialog and removes the form permanently."""

    def _close_dlg(_=None):
        if page:
            page.pop_dialog()

    async def _confirm_delete(_=None):
        _close_dlg()
        set_is_loading(True)
        success = await forms_service.delete_form(form_id, active_project_id)
        if success:
            set_active_form(None)
            set_mode("dashboard")
            if page:
                from core.utils import show_snack

                show_snack(
                    page, "Form permanently deleted from project.", duration=2000
                )
            await load_forms_fn()
        else:
            set_is_loading(False)
            show_error("Failed to delete form from edge database.")

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
                on_click=lambda e: page.run_task(_confirm_delete) if page else None,
            ),
        ],
    )
    if page:
        page.show_dialog(confirm_dlg)


async def download_csv_async(form: dict, page: ft.Page, show_error):
    """Exports all form submission responses to a CSV file in app storage."""
    responses = form.get("_responses", [])
    if not responses:
        show_error("No responses to download.")
        return
    csv_bytes = forms_service.responses_to_csv_bytes(responses)

    import os
    from pathlib import Path

    try:
        storage_data = os.getenv("FLET_APP_STORAGE_DATA")
        export_dir = (
            Path(storage_data) if storage_data else Path(".flet") / "storage" / "data"
        )
        export_dir.mkdir(parents=True, exist_ok=True)
        safe_name = form["title"].replace(" ", "_").replace("/", "-")
        export_path = export_dir / f"{safe_name}_responses.csv"

        def _write():
            export_path.write_bytes(csv_bytes)

        await asyncio.to_thread(_write)
        if page:
            from core.utils import show_snack

            show_snack(
                page,
                f"📄 Responses saved: {export_path.name}",
                success=True,
                duration=3000,
            )
    except Exception as err:
        show_error(f"Save failed: {err}")
