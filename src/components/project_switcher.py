"""Project Switcher component — premium workspace switching dropdown & dialog."""

from __future__ import annotations

import logging

import flet as ft

from core import theme
from core.state import state

logger = logging.getLogger(__name__)

_seed_visible = False


def _toggle_seed_visibility(e, page):
    """Toggle seed phrase between masked and visible."""
    global _seed_visible
    _seed_visible = not _seed_visible
    phrase = state.active_project.get("phrase", "")
    ctrl = e.control
    try:
        parent_row = ctrl.parent
        for c in parent_row.controls:
            if isinstance(c, ft.Column):
                for t in c.controls:
                    if getattr(t, "key", None) == "seed_display":
                        t.value = (
                            phrase if _seed_visible else "•••• •••• •••• •••• •••• ••••"
                        )
                        break
        ctrl.icon = (
            ft.Icons.VISIBILITY_ROUNDED
            if _seed_visible
            else ft.Icons.VISIBILITY_OFF_ROUNDED
        )
        page.update()
    except Exception:
        pass


def build_project_switcher(page: ft.Page, project_service) -> ft.Container:
    """Build a premium top-right dropdown/button showing active project name."""

    active_title = state.active_project.get("title", "My Workspace")
    is_local = state.active_project_id.startswith("loc_")
    display_id = "Local Only" if is_local else f"ID: {state.active_project_id}"

    # Outer pill wrapper
    is_disabled = getattr(state, "is_analyzing", False)
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.WORKSPACES_ROUNDED, size=16, color=theme.ACCENT),
                ft.Column(
                    [
                        ft.Text(
                            active_title,
                            size=12,
                            weight="bold",
                            max_lines=1,
                            overflow="ellipsis",
                        ),
                        ft.Text(
                            display_id, size=10, color=ft.Colors.ON_SURFACE_VARIANT
                        ),
                    ],
                    spacing=1,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Icon(
                    ft.Icons.ARROW_DROP_DOWN_ROUNDED,
                    size=18,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        padding=ft.Padding(12, 6, 12, 6),
        border_radius=12,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
        on_click=None
        if is_disabled
        else lambda e: _show_switcher_dialog(page, project_service),
        disabled=is_disabled,
        ink=not is_disabled,
        tooltip="Switch Workspace"
        if not is_disabled
        else "Cannot switch workspace while autopilot is running",
    )


def _show_switcher_dialog(page: ft.Page, project_service):
    """Render the master project settings & collaboration dialog."""

    # Dialog refs
    rename_field = ft.Ref[ft.TextField]()
    join_field = ft.Ref[ft.TextField]()
    new_field = ft.Ref[ft.TextField]()

    # Sync state feedback
    sync_status_text = ft.Text("Sync complete", size=11, color=theme.SUCCESS)
    sync_spinner = ft.ProgressRing(width=12, height=12, stroke_width=2, visible=False)

    def _close_dialog():
        page.pop_dialog()

    async def _on_sync(e):
        sync_status_text.value = "Syncing..."
        sync_spinner.visible = True
        page.update()

        success = await project_service.sync_project(state.active_project_id)

        sync_spinner.visible = False
        if success:
            sync_status_text.value = "Sync complete"
            sync_status_text.color = theme.SUCCESS
        else:
            sync_status_text.value = "Sync failed (offline)"
            sync_status_text.color = theme.ERROR
        page.update()

    async def _on_rename(e):
        if not rename_field.current or not rename_field.current.value.strip():
            return
        new_name = rename_field.current.value.strip()

        sync_status_text.value = "Renaming..."
        sync_spinner.visible = True
        page.update()

        await project_service.rename_project(state.active_project_id, new_name)

        _close_dialog()
        await page.push_route(page.route)  # Force full view redraw

    async def _on_register_project(e):
        sync_status_text.value = "Registering on Cloud..."
        sync_spinner.visible = True
        page.update()

        # Pull details of current local project and register it
        active_local = state.user_projects.get(state.active_project_id)
        if active_local:
            await project_service.create_project(
                active_local["title"], active_local["description"]
            )

        _close_dialog()
        await page.push_route(page.route)

    async def _on_create_project(e):
        if not new_field.current or not new_field.current.value.strip():
            return
        title = new_field.current.value.strip()

        sync_status_text.value = "Creating workspace..."
        sync_spinner.visible = True
        page.update()

        await project_service.create_project(title)

        _close_dialog()
        await page.push_route(page.route)

    async def _on_join_project(e):
        if not join_field.current or not join_field.current.value.strip():
            return
        token = join_field.current.value.strip()

        sync_status_text.value = "Joining project..."
        sync_spinner.visible = True
        page.update()

        # ONLY use 12-word recovery phrase for joining now
        res = await project_service.join_project_by_phrase(token)

        sync_spinner.visible = False
        if res:
            _close_dialog()
            await page.push_route(page.route)
        else:
            sync_status_text.value = "Invalid Seed Phrase."
            sync_status_text.color = theme.ERROR
            page.update()

    async def _on_switch_project(pid):
        # 1. Check for updates on switch (automated pull)
        status = await project_service.pull_project(pid)

        if status == "deleted":
            # Show Recovery Dialog
            _close_dialog()

            def _close_recover_dlg(e=None):
                page.pop_dialog()

            async def _on_re_register(e):
                _close_recover_dlg()
                # Promote local details to a new cloud ID
                active_local = state.user_projects.get(pid)
                if active_local:
                    page.snack_bar = ft.SnackBar(
                        ft.Text("Registering workspace under a new Cloud ID...")
                    )
                    page.snack_bar.open = True
                    page.update()

                    # Create new cloud project using local details
                    await project_service.create_project(
                        active_local["title"], active_local["description"]
                    )
                    page.snack_bar = ft.SnackBar(
                        ft.Text("Workspace successfully restored to cloud!"),
                        bgcolor=theme.SUCCESS,
                    )
                    page.snack_bar.open = True
                await page.push_route(page.route)

            async def _on_make_local_only(e):
                _close_recover_dlg()
                active_local = state.user_projects.get(pid)
                if active_local:
                    # Generate local temporary ID and swap keys
                    import uuid

                    new_local_id = "loc_" + str(uuid.uuid4())[:8]
                    active_local["id"] = new_local_id
                    active_local["phrase"] = project_service.uuid_to_phrase(
                        str(uuid.uuid4())
                    )
                    active_local["phrase_hash"] = project_service.phrase_to_hash(
                        active_local["phrase"]
                    )

                    state.user_projects.pop(pid, None)
                    state.user_projects[new_local_id] = active_local
                    state.active_project_id = new_local_id
                    await project_service._storage.set(
                        "spaninsight_active_project_id", new_local_id
                    )
                    await project_service._persist_local_projects()

                    page.snack_bar = ft.SnackBar(
                        ft.Text(
                            "Workspace successfully converted to offline local-only."
                        ),
                        bgcolor=theme.SUCCESS,
                    )
                    page.snack_bar.open = True
                await page.push_route(page.route)

            async def _on_delete_from_recover(e):
                _close_recover_dlg()
                await _on_delete_project(pid)

            recover_dlg = ft.AlertDialog(
                title=ft.Text("Workspace Deleted from Cloud"),
                content=ft.Container(
                    content=ft.Text(
                        "A collaborator has removed this project from the gateway node. "
                        "You still have all your local history and recipes on this device.\n\n"
                        "Would you like to register it under a new ID to restore it, "
                        "convert it to local-only to work offline, or delete it permanently?",
                        size=13,
                    ),
                    width=340,
                ),
                actions=[
                    ft.TextButton(
                        "Delete Locally",
                        style=ft.ButtonStyle(color=theme.ERROR),
                        on_click=_on_delete_from_recover,
                    ),
                    ft.TextButton("Keep Local-Only", on_click=_on_make_local_only),
                    ft.FilledButton(
                        "Register New ID",
                        bgcolor=theme.PRIMARY,
                        color=ft.Colors.WHITE,
                        on_click=_on_re_register,
                    ),
                ],
            )
            page.show_dialog(recover_dlg)
            return

        # 2. Complete Switch Project
        state.active_project_id = pid
        await project_service._storage.set("spaninsight_active_project_id", pid)

        # Auto trigger background DataFrame reload if file path is available
        proj = state.user_projects[pid]
        fpath = proj.get("current_file_path", "")
        if fpath:
            import os

            from services import file_service

            if os.path.exists(fpath):
                try:
                    df = file_service.load_dataframe(fpath)
                    state.set_dataframe(df, proj.get("current_df_name", "Dataset"))
                    state.current_df_summary = file_service.get_data_summary(df)
                except Exception:
                    state.clear_data()
            else:
                state.clear_data()
        else:
            state.clear_data()

        _close_dialog()
        await page.push_route(page.route)

    async def _on_delete_project(pid):
        # Prevent deletion if it's the last workspace
        if len(state.user_projects) <= 1:
            page.snack_bar = ft.SnackBar(
                ft.Text("Cannot delete the only remaining workspace."),
                bgcolor=theme.ERROR,
            )
            page.snack_bar.open = True
            page.update()
            return
        await project_service.delete_project(pid)
        _close_dialog()
        await page.push_route(page.route)

    # ── 1. Render Project Switcher List ──────────────────────────────
    project_items = []
    for pid, proj in state.user_projects.items():
        is_active = pid == state.active_project_id
        block_ct = len(proj.get("analysis_blocks", []))
        report_ct = len(proj.get("user_reports", []))

        # Subtitle details
        details = f"{block_ct} step{'s' if block_ct != 1 else ''} · {report_ct} report{'s' if report_ct != 1 else ''}"
        if pid.startswith("loc_"):
            details += " · ⚠️ Local only"
        else:
            details += f" · ID: {pid[:8]}..."

        project_items.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.IconButton(
                            ft.Icons.RADIO_BUTTON_CHECKED_ROUNDED
                            if is_active
                            else ft.Icons.RADIO_BUTTON_UNCHECKED_ROUNDED,
                            icon_color=theme.PRIMARY
                            if is_active
                            else ft.Colors.ON_SURFACE_VARIANT,
                            on_click=lambda e, p=pid: page.run_task(
                                _on_switch_project, p
                            ),
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    proj.get("title", "Workspace"),
                                    weight="bold",
                                    size=13,
                                ),
                                ft.Text(
                                    details, size=10, color=ft.Colors.ON_SURFACE_VARIANT
                                ),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE_ROUNDED,
                            icon_color=theme.ERROR,
                            icon_size=16,
                            on_click=lambda e, p=pid: page.run_task(
                                _on_delete_project, p
                            ),
                            visible=len(state.user_projects) > 1,
                        ),
                    ],
                    spacing=6,
                ),
                padding=ft.Padding(4, 2, 4, 2),
                border_radius=10,
                bgcolor=ft.Colors.with_opacity(0.04, theme.PRIMARY)
                if is_active
                else ft.Colors.TRANSPARENT,
            )
        )

    # ── 2. Collaboration Cards ───────────────────────────────────────
    is_active_local = state.active_project_id.startswith("loc_")

    if is_active_local:
        collab_panel = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Collab & Backup Offlined",
                        size=12,
                        weight="bold",
                        color=theme.WARNING,
                    ),
                    ft.Text(
                        "This workspace is local only. Register it on our Cloud D1 node to enable real-time collaboration with colleagues.",
                        size=11,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.FilledButton(
                        "Register Workspace",
                        icon=ft.Icons.CLOUD_UPLOAD_ROUNDED,
                        style=ft.ButtonStyle(
                            bgcolor=theme.ACCENT,
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                        on_click=_on_register_project,
                    ),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.05, theme.WARNING),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.15, theme.WARNING)),
        )
    else:
        collab_panel = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.PEOPLE_ROUNDED, color=theme.PRIMARY, size=18
                            ),
                            ft.Text("Collaboration Details", size=13, weight="bold"),
                        ],
                        spacing=6,
                    ),
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        "12-WORD SEED PHRASE (KEEP PRIVATE)",
                                        size=9,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                    ft.Text(
                                        "•••• •••• •••• •••• •••• ••••",
                                        size=11,
                                        italic=True,
                                        weight="w600",
                                        color=theme.PRIMARY,
                                        key="seed_display",
                                    ),
                                ],
                                spacing=4,
                                expand=True,
                            ),
                            ft.IconButton(
                                ft.Icons.VISIBILITY_OFF_ROUNDED,
                                tooltip="Show/Hide Phrase",
                                icon_size=16,
                                key="seed_toggle",
                                on_click=lambda e: _toggle_seed_visibility(e, page),
                            ),
                            ft.IconButton(
                                ft.Icons.COPY_ROUNDED,
                                tooltip="Copy Seed Phrase",
                                on_click=lambda e: page.run_task(
                                    ft.Clipboard().set,
                                    state.active_project.get("phrase", ""),
                                ),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(
                                            "WORKSPACE ID (INTERNAL REFERENCE)",
                                            size=9,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                        ),
                                        ft.Text(
                                            state.active_project_id,
                                            size=11,
                                            weight="bold",
                                            color=ft.Colors.ON_SURFACE,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.IconButton(
                                    ft.Icons.COPY_ROUNDED,
                                    icon_size=16,
                                    tooltip="Copy ID",
                                    on_click=lambda e: page.run_task(
                                        ft.Clipboard().set,
                                        state.active_project_id,
                                    ),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=12,
                        border_radius=10,
                        bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.ON_SURFACE),
                    ),
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.INFO_OUTLINE_ROUNDED,
                                    size=14,
                                    color=theme.WARNING,
                                ),
                                ft.Text(
                                    "Shared Access: Anyone with the Seed Phrase can edit or delete items.",
                                    size=10,
                                    color=theme.WARNING,
                                    weight="w500",
                                ),
                            ],
                            spacing=6,
                        ),
                        padding=8,
                        border_radius=8,
                        bgcolor=ft.Colors.with_opacity(0.04, theme.WARNING),
                    ),
                    ft.Row(
                        [
                            ft.TextButton(
                                "Sync Now",
                                icon=ft.Icons.SYNC_ROUNDED,
                                on_click=_on_sync,
                            ),
                            ft.Row([sync_spinner, sync_status_text], spacing=6),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=10,
            ),
            padding=14,
            border_radius=12,
            bgcolor=theme.GLASS_BG,
            border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
        )

    # ── 3. Combine Dialog UI tabs ────────────────────────────────────
    content_tabs = ft.Tabs(
        length=4,
        selected_index=0,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="Workspaces"),
                        ft.Tab(label="Share"),
                        ft.Tab(label="Join"),
                        ft.Tab(label="New"),
                    ]
                ),
                ft.TabBarView(
                    expand=True,
                    controls=[
                        # Content 1: Workspaces
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Switch Workspace", size=13, weight="bold"),
                                    ft.Container(
                                        content=ft.Column(
                                            project_items, scroll="auto", spacing=4
                                        ),
                                        height=150,
                                    ),
                                    ft.Divider(height=16, thickness=0.5),
                                    ft.Row(
                                        [
                                            ft.TextField(
                                                ref=rename_field,
                                                label="Rename Active Workspace",
                                                value=state.active_project.get(
                                                    "title", ""
                                                ),
                                                text_size=12,
                                                height=44,
                                                content_padding=10,
                                                expand=True,
                                                border_radius=10,
                                            ),
                                            ft.IconButton(
                                                ft.Icons.CHECK_ROUNDED,
                                                icon_color=theme.SUCCESS,
                                                on_click=_on_rename,
                                            ),
                                        ],
                                        spacing=8,
                                    ),
                                ],
                                spacing=8,
                                scroll="auto",
                            ),
                            padding=ft.Padding(0, 10, 0, 10),
                        ),
                        # Content 2: Share
                        ft.Container(
                            content=ft.Column(
                                [collab_panel],
                                spacing=10,
                                scroll="auto",
                            ),
                            padding=ft.Padding(0, 10, 0, 10),
                        ),
                        # Content 3: Join
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        "📥 Join a Shared Workspace",
                                        size=13,
                                        weight="bold",
                                    ),
                                    ft.Text(
                                        "To collaborate on a teammate's project, enter the 12-word recovery seed phrase.",
                                        size=11,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                    ft.Container(height=4),
                                    ft.TextField(
                                        ref=join_field,
                                        label="12-Word Seed Phrase",
                                        hint_text="e.g. apple banana cookie ...",
                                        text_size=12,
                                        height=48,
                                        content_padding=12,
                                        border_radius=10,
                                    ),
                                    ft.Container(height=4),
                                    ft.Row(
                                        [
                                            ft.FilledButton(
                                                "Join Workspace",
                                                icon=ft.Icons.LOGIN_ROUNDED,
                                                style=ft.ButtonStyle(
                                                    bgcolor=theme.PRIMARY,
                                                    shape=ft.RoundedRectangleBorder(
                                                        radius=10
                                                    ),
                                                ),
                                                on_click=_on_join_project,
                                            ),
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER,
                                    ),
                                ],
                                spacing=12,
                                scroll="auto",
                            ),
                            padding=ft.Padding(0, 10, 0, 10),
                        ),
                        # Content 4: New
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        "Create New Workspace", size=13, weight="bold"
                                    ),
                                    ft.Row(
                                        [
                                            ft.TextField(
                                                ref=new_field,
                                                hint_text="e.g. Sales Audit 2026",
                                                text_size=12,
                                                height=44,
                                                content_padding=10,
                                                expand=True,
                                                border_radius=10,
                                            ),
                                            ft.IconButton(
                                                ft.Icons.ADD_ROUNDED,
                                                icon_color=theme.PRIMARY,
                                                on_click=_on_create_project,
                                            ),
                                        ],
                                        spacing=8,
                                    ),
                                ],
                                spacing=10,
                            ),
                            padding=ft.Padding(0, 10, 0, 10),
                        ),
                    ],
                ),
            ],
        ),
    )

    dlg = ft.AlertDialog(
        content=ft.Container(
            content=content_tabs,
            width=360,
            height=340,
        ),
        actions=[ft.TextButton("Close", on_click=lambda e: _close_dialog())],
    )

    page.show_dialog(dlg)
