"""Notebook view layout — evolved from v1 analysis view.

Keeps: prompt/code input toggle, voice input, block cards,
       autopilot overlay, suggestion chips, ad placements.
Changes: Colab execution replaces local sandbox,
         file upload goes to Colab instead of local pandas,
         no more dataset-first gating — notebook is always available.
"""

import logging

import flet as ft

from components.brand_header import build_brand_header
from components.suggestion_chips import build_suggestion_chips
from core import theme, tokens, utils
from core.state import state
from views.notebook.state import NotebookState
from views.notebook.ui_components import (
    build_block_card,
    build_skeleton_loader,
    build_terminal,
)

logger = logging.getLogger(__name__)


def build_notebook_view(
    page: ft.Page, colab_service, credit_service, storage
) -> ft.View:
    """Build the notebook view — the core analysis workspace."""
    view_state = NotebookState(page, colab_service, credit_service, storage)

    # ── Stateful DOM containers ─────────────────────────────────
    top_section = ft.Container()
    blocks_list = ft.Column(spacing=8)
    loading_section = ft.Container()
    input_section = ft.Container()

    main_column = ft.Column(
        controls=[top_section, blocks_list, loading_section, input_section],
        expand=True,
        scroll="auto",
    )
    view_state.content_column = ft.Ref[ft.Column]()
    view_state.content_column.current = main_column

    # ── Autopilot overlay ───────────────────────────────────────
    autopilot_overlay_card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.ProgressRing(
                            width=20, height=20, stroke_width=3, color=theme.PRIMARY
                        ),
                        ft.Text("Autopilot is running…", weight="bold", size=14),
                    ],
                    spacing=10,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=2),
                ft.Text(
                    "SpanInsight is analyzing your data on Colab. "
                    "Watch insights compile in real-time!",
                    size=11,
                    color=ft.Colors.ON_SURFACE,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(
                    content=ft.Text(
                        "Status: Initializing…",
                        size=10,
                        italic=True,
                        color=theme.PRIMARY,
                    ),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Container(
                    content=ft.FilledTonalButton(
                        "Stop Autopilot",
                        icon=ft.Icons.STOP_ROUNDED,
                        on_click=lambda e: _cancel_autopilot(),
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding(0, 8, 0, 0),
                ),
            ],
            horizontal_alignment="center",
            spacing=4,
        ),
        padding=20,
        border_radius=16,
        bgcolor=ft.Colors.SURFACE,
        border=ft.Border.all(1, ft.Colors.with_opacity(0.12, ft.Colors.ON_SURFACE)),
        alignment=ft.Alignment.CENTER,
        shadow=ft.BoxShadow(
            blur_radius=20,
            color=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
        ),
    )

    autopilot_overlay = ft.Container(
        content=ft.Column(
            [autopilot_overlay_card],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment="center",
        ),
        bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
        visible=False,
        expand=True,
    )

    def _cancel_autopilot():
        state.autopilot_cancelled = True
        state.autopilot_running = False
        autopilot_overlay.visible = False
        page.update()

    # ── Handlers ────────────────────────────────────────────────
    async def on_custom_prompt(view_state_ref, e):
        """Handle user prompt submission — send to AI, execute on Colab."""
        if not view_state_ref.custom_prompt_field.current:
            return
        prompt = view_state_ref.custom_prompt_field.current.value
        if not prompt or not prompt.strip():
            return

        view_state_ref.custom_prompt_field.current.value = ""
        page.update()

        async with view_state_ref.analysis_lock:
            state.is_analyzing = True
            view_state_ref.rebuild()

            try:
                # Deduct credits
                from core.constants import COST_CUSTOM_PROMPT
                from services import ai as ai_service

                await view_state_ref.credit_service.use_credits(COST_CUSTOM_PROMPT)

                # Get AI-generated code
                code_response = await ai_service.generate_code(
                    prompt=prompt.strip(),
                    session_name=state.active_session_name,
                )

                code = code_response.get("code", "")
                description = code_response.get("description", "")

                if not code.strip():
                    utils.show_snack(
                        page, "AI couldn't generate code for that prompt", error=True
                    )
                    return

                # Create new block
                block = {
                    "prompt": prompt.strip(),
                    "code": code,
                    "description": description,
                    "outputs": [],
                    "failed": False,
                    "is_running": True,
                }
                state.notebook_cells.append(block)
                view_state_ref.rebuild()

                # Execute on Colab
                try:
                    outputs = await colab_service.exec_code(
                        code=code,
                        session_name=state.active_session_name,
                    )
                    block["outputs"] = outputs
                    block["failed"] = any(
                        o.get("output_type") == "error" for o in outputs
                    )
                except Exception as exec_err:
                    block["outputs"] = [
                        {
                            "output_type": "error",
                            "traceback": [str(exec_err)],
                            "ename": "ExecutionError",
                            "evalue": str(exec_err),
                        }
                    ]
                    block["failed"] = True
                finally:
                    block["is_running"] = False

            except Exception as ex:
                logger.exception("Custom prompt failed")
                utils.show_snack(page, f"Error: {ex}", error=True)
            finally:
                state.is_analyzing = False
                view_state_ref.rebuild()

    async def on_run_code(view_state_ref, code_str):
        """Handle direct code execution (expert mode) on Colab."""
        if not code_str or not code_str.strip():
            return

        async with view_state_ref.analysis_lock:
            state.is_analyzing = True
            block = {
                "prompt": "Manual Code",
                "code": code_str,
                "description": "",
                "outputs": [],
                "failed": False,
                "is_running": True,
            }
            state.notebook_cells.append(block)
            view_state_ref.rebuild()

            try:
                outputs = await colab_service.execute(
                    code=code_str,
                    session_name=state.active_session_name,
                )
                block["outputs"] = outputs
                block["failed"] = any(o.get("type") == "error" for o in outputs)
            except Exception as ex:
                block["outputs"] = [
                    {
                        "type": "error",
                        "traceback": [str(ex)],
                        "ename": "ExecutionError",
                        "evalue": str(ex),
                    }
                ]
                block["failed"] = True
            finally:
                block["is_running"] = False
                state.is_analyzing = False
                view_state_ref.rebuild()

    async def on_voice_toggle(view_state_ref, e):
        """Handle voice input toggle — same as v1."""
        if not view_state_ref.audio_svc:
            utils.show_snack(
                page, "Voice input not available on this platform", error=True
            )
            return
        # Delegate to audio service (unchanged from v1)

    # ── Upload file to Colab ────────────────────────────────────
    async def on_upload_file(file_path: str, file_name: str):
        """Upload a local file to the Colab runtime."""
        try:
            view_state.loading_file_name["value"] = file_name
            view_state.rebuild()

            await colab_service.upload(
                local_path=file_path,
                remote_path=f"/content/{file_name}",
                session_name=state.active_session_name,
            )

            utils.show_snack(page, f"Uploaded {file_name} to Colab", success=True)

            # Auto-load with pandas on Colab
            ext = file_name.lower().split(".")[-1] if "." in file_name else ""
            if ext in ("csv", "tsv"):
                load_code = f'import pandas as pd\ndf = pd.read_csv("/content/{file_name}")\nprint(f"Loaded {{len(df)}} rows, {{len(df.columns)}} columns")\ndf.head()'
            elif ext in ("xlsx", "xls"):
                load_code = f'import pandas as pd\ndf = pd.read_excel("/content/{file_name}")\nprint(f"Loaded {{len(df)}} rows, {{len(df.columns)}} columns")\ndf.head()'
            elif ext == "json":
                load_code = f'import pandas as pd\ndf = pd.read_json("/content/{file_name}")\nprint(f"Loaded {{len(df)}} rows, {{len(df.columns)}} columns")\ndf.head()'
            elif ext in ("parquet", "pq"):
                load_code = f'import pandas as pd\ndf = pd.read_parquet("/content/{file_name}")\nprint(f"Loaded {{len(df)}} rows, {{len(df.columns)}} columns")\ndf.head()'
            else:
                load_code = f'# File uploaded: /content/{file_name}\nimport os\nprint(f"File size: {{os.path.getsize(\\"/content/{file_name}\\"):,}} bytes")'

            await on_run_code(view_state, load_code)

        except Exception as ex:
            logger.error("File upload failed: %s", ex)
            utils.show_snack(page, f"Upload failed: {ex}", error=True)
        finally:
            view_state.loading_file_name["value"] = ""
            view_state.rebuild()

    # ── Toggle input mode ───────────────────────────────────────
    def _toggle_terminal(e):
        view_state.terminal_expanded = not view_state.terminal_expanded
        input_section.content = None
        _update_bottom_sections()
        page.update()

    def _build_terminal_input():
        if not view_state.terminal_expanded:
            return ft.TextField(
                ref=view_state.custom_prompt_field,
                hint_text="Ask anything about your data…",
                expand=True,
                border_radius=12,
                text_size=13,
                content_padding=ft.Padding(14, 10, 14, 10),
                on_submit=lambda e: page.run_task(on_custom_prompt, view_state, e),
            )

        terminal = build_terminal(
            view_state,
            code="",
            on_run=lambda c: page.run_task(on_run_code, view_state, c),
            filename="manual.py",
        )
        terminal.expand = True
        return ft.Row(
            [
                ft.IconButton(
                    ft.Icons.CHEVRON_LEFT_ROUNDED,
                    icon_color=ft.Colors.ON_SURFACE_VARIANT,
                    tooltip="Back to prompt",
                    on_click=_toggle_terminal,
                ),
                terminal,
            ],
            expand=True,
        )

    # ── Section builders ────────────────────────────────────────
    def _update_top_section():
        if not state.colab_connected:
            # Show connection prompt
            top_section.content = ft.Column(
                [
                    build_brand_header(show_tagline=True, spacing_below=True),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(
                                    ft.Icons.CLOUD_OFF_ROUNDED,
                                    size=48,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                ft.Text(
                                    "Start a Colab Session",
                                    size=16,
                                    weight="bold",
                                    text_align="center",
                                ),
                                ft.Text(
                                    "Run analyses on powerful cloud compute.",
                                    size=12,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                    text_align="center",
                                ),
                                ft.Container(height=8),
                                ft.FilledButton(
                                    "Start Session",
                                    icon=ft.Icons.CLOUD_ROUNDED,
                                    style=ft.ButtonStyle(
                                        shape=ft.RoundedRectangleBorder(radius=12),
                                    ),
                                    on_click=lambda e: page.run_task(_connect_to_colab),
                                ),
                            ],
                            horizontal_alignment="center",
                            spacing=8,
                        ),
                        padding=30,
                        alignment=ft.Alignment.CENTER,
                    ),
                ],
                horizontal_alignment="center",
            )
            top_section.padding = 20
            top_section.expand = True
        elif not state.notebook_cells:
            # Connected but empty — show upload prompt + suggestions
            top_section.content = ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.CLOUD_DONE_ROUNDED,
                                    size=16,
                                    color=theme.SUCCESS,
                                ),
                                ft.Text(
                                    f"Connected — {state.session_hardware}",
                                    size=12,
                                    color=theme.SUCCESS,
                                    weight="w600",
                                ),
                                ft.Container(expand=True),
                                ft.TextButton(
                                    "Files",
                                    icon=ft.Icons.FOLDER_ROUNDED,
                                    style=ft.ButtonStyle(
                                        color=theme.ACCENT,
                                        padding=ft.Padding(8, 0, 8, 0),
                                    ),
                                    on_click=lambda e: page.run_task(
                                        lambda: page.go("/files")
                                    ),
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.Padding(16, 8, 16, 8),
                        border_radius=10,
                        bgcolor=ft.Colors.with_opacity(0.05, theme.SUCCESS),
                    ),
                    ft.Container(height=8),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Start analyzing",
                                    size=16,
                                    weight="bold",
                                ),
                                ft.Text(
                                    "Upload data, ask a question, or write code.",
                                    size=12,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                ft.Container(height=8),
                                ft.OutlinedButton(
                                    "Upload File",
                                    icon=ft.Icons.UPLOAD_FILE_ROUNDED,
                                    style=ft.ButtonStyle(
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                        color=theme.PRIMARY,
                                    ),
                                    on_click=lambda e: _pick_file_for_upload(),
                                ),
                            ],
                            horizontal_alignment="center",
                            spacing=4,
                        ),
                        padding=20,
                        alignment=ft.Alignment.CENTER,
                    ),
                    # Quick suggestion chips
                    build_suggestion_chips(
                        suggestions=state.suggestions or [],
                        on_select=lambda s: page.run_task(
                            on_custom_prompt,
                            view_state,
                            type("E", (), {"control": type("C", (), {"value": s})()}),
                        ),
                    )
                    if state.suggestions
                    else ft.Container(),
                ],
                spacing=4,
            )
            top_section.padding = ft.Padding(12, 8, 12, 8)
            top_section.expand = False
        else:
            # Has cells — show compact session bar
            top_section.content = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.CLOUD_DONE_ROUNDED,
                            size=14,
                            color=theme.SUCCESS,
                        ),
                        ft.Text(
                            f"{state.session_hardware} · {len(state.notebook_cells)} blocks",
                            size=11,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Container(expand=True),
                        ft.IconButton(
                            ft.Icons.FOLDER_ROUNDED,
                            icon_size=16,
                            tooltip="Files",
                            on_click=lambda e: page.go("/files"),
                        ),
                        ft.IconButton(
                            ft.Icons.SAVE_ALT_ROUNDED,
                            icon_size=16,
                            tooltip="Export as .ipynb",
                            on_click=lambda e: page.run_task(_export_notebook),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
                padding=ft.Padding(12, 6, 12, 6),
                border_radius=8,
                bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.ON_SURFACE),
            )
            top_section.padding = ft.Padding(8, 4, 8, 0)
            top_section.expand = False

    def _update_blocks():
        controls = []
        is_mobile = page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
        for i, b in enumerate(state.notebook_cells):
            controls.append(build_block_card(view_state, b, i))
            if is_mobile and (i + 1) % 4 == 0:
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
                        border_radius=10,
                        margin=ft.Margin(12, 4, 12, 4),
                    )
                )
        blocks_list.controls = controls

        if state.is_analyzing:
            blocks_list.controls.append(build_skeleton_loader())

    def _update_bottom_sections():
        if not state.colab_connected:
            input_section.visible = False
            autopilot_overlay.visible = False
            return

        if state.is_analyzing and getattr(state, "autopilot_running", False):
            progress_text = getattr(state, "autopilot_progress", "") or "AI thinking…"
            input_section.visible = False
            autopilot_overlay.visible = True
            step_text = autopilot_overlay_card.content.controls[3]
            step_text.content.value = f"Status: {progress_text}"
        else:
            autopilot_overlay.visible = False
            if not input_section.content:
                expanded = view_state.terminal_expanded
                if expanded:
                    input_section.content = _build_terminal_input()
                else:
                    input_section.content = ft.Row(
                        [
                            ft.IconButton(
                                ft.Icons.CODE_ROUNDED,
                                icon_color=ft.Colors.ON_SURFACE_VARIANT,
                                tooltip="Code Mode",
                                on_click=_toggle_terminal,
                            ),
                            _build_terminal_input(),
                            ft.IconButton(
                                ft.Icons.SEND_ROUNDED,
                                icon_color=theme.PRIMARY,
                                tooltip="Send",
                                on_click=lambda e: page.run_task(
                                    on_custom_prompt, view_state, e
                                ),
                            ),
                        ]
                    )

            input_section.padding = ft.Padding(12, 8, 8, 24)
            input_section.visible = True

    # ── Helpers ──────────────────────────────────────────────────
    async def _connect_to_colab():
        try:
            state.is_loading = True
            page.update()

            is_auth = await colab_service.check_auth()
            if not is_auth:
                utils.show_snack(page, "Please sign in to Google first", error=True)
                return

            result = await colab_service.new_session(
                gpu=state.default_gpu or None,
                tpu=state.default_tpu or None,
                keep_alive=state.keep_alive_enabled,
            )

            state.colab_connected = True
            state.active_session_name = result["name"]

            hardware = result.get("accelerator_label", result.get("accelerator", "CPU"))
            if hardware == "NONE":
                hardware = "CPU"
            state.session_hardware = hardware

            view_state.rebuild()
        except Exception as ex:
            logger.error("Colab connection failed: %s", ex)
            utils.show_snack(page, f"Connection failed: {ex}", error=True)
        finally:
            state.is_loading = False
            page.update()

    async def _export_notebook():
        try:
            from services.ipynb_converter import cells_to_ipynb

            cells_to_ipynb(state.notebook_cells)
            utils.show_snack(page, "Notebook exported!", success=True)
        except Exception as ex:
            utils.show_snack(page, f"Export failed: {ex}", error=True)

    def _pick_file_for_upload():
        # TODO: Wire to file picker service → on_upload_file
        pass

    # ── Rebuild orchestrator ────────────────────────────────────
    def _rebuild():
        try:
            if page.route == "/notebook":
                _update_top_section()
                _update_blocks()
                _update_bottom_sections()
                page.update()

                async def do_scroll():
                    try:
                        if view_state.content_column.current:
                            await view_state.content_column.current.scroll_to(
                                offset=-1, duration=300
                            )
                    except Exception:
                        pass

                page.run_task(do_scroll)
        except Exception:
            logger.exception("Rebuild failed in notebook view")

    view_state.rebuild_fn = _rebuild

    # ── Initial state ───────────────────────────────────────────
    if getattr(state, "trigger_file_picker", False):
        state.trigger_file_picker = False

    _rebuild()

    view = ft.View(
        route="/notebook",
        controls=[
            ft.Stack(
                controls=[main_column, autopilot_overlay],
                expand=True,
            )
        ],
        padding=0,
        appbar=ft.AppBar(
            title=ft.Text("Notebook", size=tokens.FONT_LG, weight=ft.FontWeight.W_700),
            center_title=True,
            bgcolor=ft.Colors.TRANSPARENT,
        ),
    )

    return view
