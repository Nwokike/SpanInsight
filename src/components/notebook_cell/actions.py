"""Notebook cell action buttons and clipboard helpers."""

import logging
import re

import flet as ft

from core import theme, tokens

logger = logging.getLogger("notebook")


def make_actions_row(
    on_move_up=None, on_move_down=None, on_delete=None, on_copy=None, on_fix=None
):
    """Compact action button row for cell management."""
    controls = []
    if on_fix:
        controls.append(
            ft.IconButton(
                ft.Icons.AUTO_FIX_HIGH_ROUNDED,
                icon_size=tokens.ICON_XS,
                icon_color=theme.WARNING,
                tooltip="Fix with AI",
                style=ft.ButtonStyle(padding=tokens.SPACE_XS),
                on_click=lambda e: on_fix() if on_fix else None,
            )
        )
    if on_copy:
        controls.append(
            ft.IconButton(
                ft.Icons.COPY_ROUNDED,
                icon_size=tokens.ICON_XS,
                tooltip="Copy Code",
                style=ft.ButtonStyle(padding=tokens.SPACE_XS),
                on_click=lambda e: on_copy() if on_copy else None,
            )
        )
    controls.extend(
        [
            ft.IconButton(
                ft.Icons.ARROW_UPWARD_ROUNDED,
                icon_size=tokens.ICON_XS,
                tooltip="Move Up",
                style=ft.ButtonStyle(padding=tokens.SPACE_XS),
                on_click=lambda e: on_move_up() if on_move_up else None,
            ),
            ft.IconButton(
                ft.Icons.ARROW_DOWNWARD_ROUNDED,
                icon_size=tokens.ICON_XS,
                tooltip="Move Down",
                style=ft.ButtonStyle(padding=tokens.SPACE_XS),
                on_click=lambda e: on_move_down() if on_move_down else None,
            ),
            ft.IconButton(
                ft.Icons.DELETE_OUTLINE_ROUNDED,
                icon_size=tokens.ICON_XS,
                icon_color=theme.ERROR,
                tooltip="Delete Cell",
                style=ft.ButtonStyle(padding=tokens.SPACE_XS),
                on_click=lambda e: on_delete() if on_delete else None,
            ),
        ]
    )
    return ft.Row(controls=controls, spacing=tokens.SPACE_NONE)


async def fix_with_ai(page: ft.Page, cell: dict, on_change=None):
    """Generate an AI correction for a failed hand-written cell (Expert mode).

    Writes the corrected code into the editor WITHOUT running it — experts
    stay in control and can review before executing.
    """
    from core.state import state
    from services.ai import analysis as ai_service
    from services.colab.output_utils import extract_error_text

    src = cell.get("source", "")
    error_text = extract_error_text(cell.get("outputs", [])) or "Unknown error"

    if page:
        from core.utils import show_snack

        show_snack(
            page,
            "🩹 Asking AI for a fix…",
            duration=tokens.SNACK_DURATION_SHORT_MS,
        )

    try:
        corrected = await ai_service.generate_corrected_code(
            "Fix the error in this Python data-analysis code",
            src,
            error_text,
            state.active_schema_json or {},
        )
    except Exception as ex:
        logger.warning("Fix-with-AI generation failed: %s", ex)
        corrected = ""

    if not corrected or corrected == src:
        if page:
            from core.utils import show_snack

            show_snack(
                page,
                "AI couldn't improve this code — try rephrasing it.",
                duration=tokens.SNACK_DURATION_NORMAL_MS,
            )
        return

    cell["source"] = corrected
    cell["failed"] = False
    if on_change:
        on_change()
    if page:
        from core.utils import show_snack

        show_snack(
            page,
            "🩹 Code corrected — review & run",
            duration=tokens.SNACK_DURATION_NORMAL_MS,
            success=True,
        )


async def copy_code(page: ft.Page, code: str):
    """Copy cell source code to clipboard."""
    if not code or not code.strip():
        return
    try:
        await page.clipboard.set(code.strip())
        if page:
            from core.utils import show_snack

            show_snack(
                page,
                "📋 Code copied to clipboard!",
                duration=tokens.SNACK_DURATION_SHORT_MS,
            )
    except Exception as ex:
        logger.error("Copy code failed: %s", ex)


async def copy_output(page: ft.Page, outputs: list):
    """Copy notebook output text to clipboard supporting all output types."""
    if not outputs:
        return

    text_to_copy = ""
    for out in outputs:
        if isinstance(out, str):
            text_to_copy += out + "\n"
            continue
        if not isinstance(out, dict):
            continue

        out_type = out.get("type") or out.get("output_type")
        if out_type == "stream":
            txt = out.get("text", "")
            if isinstance(txt, list):
                txt = "".join(txt)
            text_to_copy += str(txt) + "\n"
        elif out_type == "error":
            tb = out.get("traceback", [])
            if isinstance(tb, list):
                tb_str = "\n".join(tb)
            else:
                tb_str = str(tb)
            ename = out.get("ename", "")
            evalue = out.get("evalue", "")
            if ename or evalue:
                text_to_copy += f"{ename}: {evalue}\n"
            text_to_copy += tb_str + "\n"
        elif out_type in ["execute_result", "display_data"]:
            data = out.get("data", {})
            if "text/plain" in data:
                txt = data["text/plain"]
                if isinstance(txt, list):
                    txt = "".join(txt)
                text_to_copy += str(txt) + "\n"
        elif "text" in out:
            txt = out["text"]
            if isinstance(txt, list):
                txt = "".join(txt)
            text_to_copy += str(txt) + "\n"

    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    final_text = ansi_escape.sub("", text_to_copy).strip()

    if final_text:
        try:
            await page.clipboard.set(final_text)
            if page:
                from core.utils import show_snack

                show_snack(
                    page,
                    "📋 Output copied to clipboard!",
                    duration=tokens.SNACK_DURATION_SHORT_MS,
                )
        except Exception as ex:
            logger.error("Copy output failed: %s", ex)
