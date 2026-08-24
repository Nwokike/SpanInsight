"""Business logic and async handlers for Forms screen."""

from __future__ import annotations

import asyncio
import json
import logging

import flet as ft

from core import theme, tokens
from services import ai as ai_service
from services import forms_service

logger = logging.getLogger("FormsHandlers")


def normalize_field_names(
    fields: list[dict], preserve: set[str] | None = None
) -> list[dict]:
    """Ensure every field has a non-empty, unique, stable ``name``.

    ``name`` is the storage key collected responses are filed under, so it is
    assigned once and never re-derived from the label afterwards. Names already
    present in ``preserve`` (a published form's existing identities) are kept
    untouched; empty/duplicated names get fresh generated ids. Returns copies.
    """
    import uuid

    preserve_set = {p for p in (preserve or set()) if p}
    seen: set[str] = set(preserve_set)
    out: list[dict] = []
    for raw in fields or []:
        field = dict(raw)
        name = str(field.get("name") or "").strip()
        # Empty names always get generated ids; a duplicate is regenerated
        # UNLESS it is itself one of the preserved identities.
        if not name or (name in seen and name not in preserve_set):
            name = "q_" + uuid.uuid4().hex[:10]
            while name in seen:
                name = "q_" + uuid.uuid4().hex[:10]
        seen.add(name)
        field["name"] = name
        out.append(field)
    return out


def _form_schema_fields(form: dict) -> list[dict]:
    """Parse a loaded form's ``schema_json`` (gateway returns a JSON string)."""
    raw = form.get("schema_json", "")
    if isinstance(raw, str) and raw:
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    if isinstance(raw, list):
        return raw
    return []


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

        set_draft_schema(normalize_field_names(schema.get("fields", [])))
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
                "IMPORTANT: keep each existing field's exact `name` value "
                "unchanged - it is a stable identifier tied to already-collected "
                "responses. Only brand-new fields may use new unique names.\n\n"
                f"Return the FULL updated form as a JSON object with title, description, fields."
            )
            schema = await ai_service.generate_form_schema(edit_prompt)
            if schema:
                old_names = {str(f.get("name") or "") for f in (draft_schema or [])}
                set_draft_schema(
                    normalize_field_names(
                        schema.get("fields", draft_schema),
                        preserve=old_names,
                    )
                )
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
                from core.utils import set_clipboard, show_snack

                show_snack(
                    page,
                    f"Published! Link: {result['url']}",
                    success=True,
                    duration=tokens.SNACK_DURATION_EXTENDED_MS,
                )
                await set_clipboard(page, result["url"])
            await load_forms_fn()
            # Interstitial after publishing (mobile; cooldown-guarded).
            if page:
                try:
                    from services.ad_service import get_ad_service

                    page.run_task(get_ad_service(page).show_interstitial)
                except Exception:
                    pass
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
                    page,
                    "Form permanently deleted from project.",
                    duration=tokens.SNACK_DURATION_SHORT_MS,
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
                size=tokens.FONT_BODY,
            ),
            width=tokens.DIALOG_WIDTH_SM,
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
    """Exports all form submission responses to a user-accessible CSV file."""
    responses = form.get("_responses", [])
    if not responses:
        show_error("No responses to download.")
        return
    schema_fields = _form_schema_fields(form)
    csv_bytes = forms_service.responses_to_csv_bytes(responses, schema_fields)

    import os
    from pathlib import Path

    from core.utils import resolve_save_path, show_snack

    try:
        safe_name = form.get("title", "form").replace(" ", "_").replace("/", "-")
        default_name = f"{safe_name}_responses.csv"

        save_path = await resolve_save_path(page, default_name)
        if not save_path:
            return  # User canceled the save dialog

        def _write():
            Path(save_path).write_bytes(csv_bytes)

        await asyncio.to_thread(_write)
        if page:
            show_snack(
                page,
                f"📄 Responses saved: {os.path.basename(save_path)}",
                success=True,
                duration=tokens.SNACK_DURATION_MD_MS,
            )
    except Exception as err:
        show_error(f"Save failed: {err}")


async def request_update_live_form_async(
    form: dict,
    draft_title: str,
    draft_desc: str,
    draft_schema: list,
    active_project_id: str,
    page: ft.Page | None,
    set_is_publishing,
    set_mode,
    set_draft_schema,
    set_prompt_text,
    set_editing_form_id,
    set_active_form,
    load_forms_fn,
    show_error,
):
    """Show the smart-merge diff confirmation, then update the LIVE form in place.

    Kept questions preserve every collected answer; removed questions have their
    stored answers permanently purged server-side (zero ghosts). The share link
    never changes.
    """
    if not form or not page:
        return

    error = forms_service._validate_schema(draft_schema)
    if error:
        show_error(f"Cannot save: {error}")
        return

    # Compute the diff from SERVER TRUTH, not from a possibly-stale snapshot:
    # re-fetch the live definition and the current response count at the
    # moment the user asks to update, so every line in the dialog is current.
    fresh = await forms_service.get_form(form["id"])
    resp_data = await forms_service.get_responses(form["id"], active_project_id)
    if fresh:
        form = {**form, "schema_json": fresh.get("schema_json", [])}
    total_responses = resp_data.get("count", len(resp_data.get("responses", [])))

    old_fields = _form_schema_fields(form)
    old_names = [str(f.get("name")) for f in old_fields if f.get("name")]
    new_names = {str(f.get("name")) for f in draft_schema if f.get("name")}
    kept_count = len({n for n in old_names if n in new_names})
    removed = [f for f in old_fields if str(f.get("name")) not in new_names]
    added = [f for f in draft_schema if str(f.get("name")) not in set(old_names)]

    lines = [
        f"• Questions you keep ({kept_count}) keep all their collected answers.",
    ]
    if removed:
        shown = ", ".join(
            "'" + str(f.get("label") or f.get("name")) + "'" for f in removed[:5]
        ) + ("…" if len(removed) > 5 else "")
        lines.append(
            f"• Removed ({len(removed)}): {shown} - EVERY stored answer for "
            "these questions is permanently deleted from the database."
        )
    if added:
        lines.append(f"• New ({len(added)}): older submissions show blank for these.")
    lines.append(
        f"This form has {total_responses} response(s) right now. "
        "The share link stays the same."
    )

    def _close(_=None):
        page.pop_dialog()

    async def _confirm_apply(_=None):
        _close()
        set_is_publishing(True)
        try:
            ok = await forms_service.update_form(
                form_id=form["id"],
                project_id=active_project_id,
                title=draft_title,
                description=draft_desc,
                schema_json=draft_schema,
            )
            if ok:
                resp_data = await forms_service.get_responses(
                    form["id"], active_project_id
                )
                updated = dict(form)
                updated["title"] = draft_title
                updated["description"] = draft_desc
                updated["schema_json"] = json.dumps(draft_schema)
                updated["_responses"] = resp_data.get("responses", [])
                updated["_count"] = resp_data.get("count", 0)
                set_active_form(updated)
                set_mode("detail")
                set_editing_form_id("")
                set_draft_schema([])
                set_prompt_text("")
                await load_forms_fn()
                from core.utils import show_snack

                show_snack(
                    page,
                    "✅ Live form updated - link unchanged",
                    success=True,
                    duration=tokens.SNACK_DURATION_MD_MS,
                )
                # Interstitial after the update completes (mobile; cooldown-
                # guarded so it can never feel spammy).
                try:
                    from services.ad_service import get_ad_service

                    page.run_task(get_ad_service(page).show_interstitial)
                except Exception:
                    pass
            else:
                show_error("Update failed. Please check connection and try again.")
        except Exception as err:
            show_error(f"Update error: {err}")
        finally:
            set_is_publishing(False)

    has_removals = bool(removed)
    confirm_dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Icon(
                    ft.Icons.PUBLISH_ROUNDED,
                    color=theme.ERROR if has_removals else theme.PRIMARY,
                ),
                ft.Text("Update Live Form?"),
            ],
            spacing=tokens.SPACE_SM,
        ),
        content=ft.Container(
            content=ft.Column(
                [ft.Text(ln, size=tokens.FONT_BODY) for ln in lines],
                spacing=tokens.SPACE_XS,
                tight=True,
            ),
            width=tokens.DIALOG_WIDTH_SM,
        ),
        actions=[
            ft.TextButton("Cancel", on_click=_close),
            ft.FilledButton(
                "Update Live Form",
                bgcolor=theme.ERROR if has_removals else theme.PRIMARY,
                color=ft.Colors.WHITE,
                on_click=lambda e: page.run_task(_confirm_apply) if page else None,
            ),
        ],
    )
    page.show_dialog(confirm_dlg)
