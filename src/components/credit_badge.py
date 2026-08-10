"""Credit badge component — color-coded chip for the AppBar and active Credits popup dialog."""

from __future__ import annotations

import flet as ft

from core import theme, tokens


def build_credit_badge(credits: int) -> ft.Container:
    """Build a compact credit badge chip.

    Color-coded: green (>20), amber (5-20), red (<5).
    """
    if credits > 20:
        color = theme.CREDIT_HIGH
    elif credits >= 5:
        color = theme.CREDIT_MEDIUM
    else:
        color = theme.CREDIT_LOW

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.BOLT_ROUNDED,
                    size=tokens.ICON_SM,
                    color=color,
                ),
                ft.Text(
                    str(credits),
                    size=tokens.FONT_SM,
                    weight=ft.FontWeight.W_600,
                    color=color,
                ),
            ],
            spacing=tokens.SPACE_XXS,
            tight=True,
        ),
        padding=ft.Padding(
            left=tokens.SPACE_SM,
            right=tokens.SPACE_MD,
            top=tokens.SPACE_XS,
            bottom=tokens.SPACE_XS,
        ),
        border_radius=tokens.RADIUS_PILL,
        bgcolor=ft.Colors.with_opacity(0.12, color),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.25, color)),
    )


def show_credits_dialog(page: ft.Page, credit_service):
    """Show the premium credits panel, featuring Ad Rewards with a 30s cooldown on mobile and standard balance display on PC."""
    import asyncio
    import time

    from core import theme
    from core.state import state
    from services.ad_service import AdService

    ad_service = AdService(page)

    # Re-use global state to store the cooldown timestamp
    if not hasattr(state, "ad_cooldown_end"):
        state.ad_cooldown_end = 0.0

    is_mobile = page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)

    credits_text = ft.Text(
        f"{state.credits_remaining}",
        size=36,
        weight="bold",
        color=theme.PRIMARY,
    )

    cooldown_label = ft.Text(
        "", size=11, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER
    )

    watch_btn = None
    if is_mobile:
        watch_btn = ft.FilledButton(
            "Watch Ad (+2 Credits)",
            icon=ft.Icons.PLAY_CIRCLE_ROUNDED,
            bgcolor=theme.ACCENT,
            color=ft.Colors.WHITE,
            disabled=False,
        )

    dialog_open = True

    def _close_dialog(e=None):
        nonlocal dialog_open
        dialog_open = False
        page.pop_dialog()

    def _on_dismiss(e):
        nonlocal dialog_open
        dialog_open = False

    async def _update_timer_loop():
        if not is_mobile or watch_btn is None:
            return
        # A loop that updates the countdown in real-time while the dialog is visible
        while dialog_open and dlg.open:
            now = time.time()
            remaining = int(state.ad_cooldown_end - now)
            if remaining > 0:
                watch_btn.disabled = True
                watch_btn.text = f"Cooldown ({remaining}s)"
                cooldown_label.value = (
                    f"Please wait {remaining}s before watching another ad."
                )
                cooldown_label.color = theme.ERROR
                watch_btn.update()
                cooldown_label.update()
            else:
                watch_btn.disabled = False
                watch_btn.text = "Watch Ad (+2 Credits)"
                cooldown_label.value = (
                    "Watch a short ad to receive +2 analysis credits instantly!"
                )
                cooldown_label.color = ft.Colors.ON_SURFACE_VARIANT
                watch_btn.update()
                cooldown_label.update()
                break
            await asyncio.sleep(0.5)

    async def _on_watch_success():
        if not is_mobile:
            return
        # Award credits securely
        new_balance = await credit_service.add_credits(2)
        state.credits_remaining = new_balance
        credits_text.value = str(new_balance)
        credits_text.update()

        # Trigger parent view updates globally
        try:
            await page.push_route(page.route)
        except Exception:
            pass

    async def _on_watch_click(e):
        if not is_mobile or watch_btn is None:
            return
        now = time.time()
        if state.ad_cooldown_end > now:
            return

        # Start cooldown immediately to prevent duplicate clicks
        state.ad_cooldown_end = now + 30.0

        watch_btn.disabled = True
        watch_btn.update()
        page.run_task(_update_timer_loop)

        # Trigger interstitial ad safely
        success = await ad_service.show_rewarded_interstitial(_on_watch_success)
        if not success:
            # If trigger failed, reset cooldown
            state.ad_cooldown_end = 0
            watch_btn.disabled = False
            watch_btn.update()

    if is_mobile and watch_btn is not None:
        watch_btn.on_click = lambda e: page.run_task(_on_watch_click, e)

    content_controls = [
        ft.Row(
            [
                ft.Icon(ft.Icons.BOLT_ROUNDED, size=28, color=theme.ACCENT),
                ft.Text("AI Credit Balance", size=18, weight="bold"),
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        ft.Container(height=10),
        ft.Row(
            [
                credits_text,
                ft.Text("credits", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=6,
        ),
        ft.Container(height=6),
        ft.Text(
            "Spaninsight grants 50 free analysis credits every 24 hours. "
            "Credits are spent when running deep AI insights and automated tasks.",
            size=11,
            color=ft.Colors.ON_SURFACE_VARIANT,
            text_align=ft.TextAlign.CENTER,
        ),
    ]

    if is_mobile:
        content_controls.extend(
            [
                ft.Divider(height=20, thickness=0.5),
                ft.Text(
                    "Need more credits?",
                    size=12,
                    weight="bold",
                    color=theme.PRIMARY,
                ),
                cooldown_label,
                ft.Container(height=4),
                watch_btn,
            ]
        )

    dlg = ft.AlertDialog(
        content=ft.Container(
            content=ft.Column(
                content_controls,
                spacing=8,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=320,
            padding=10,
        ),
        actions=[ft.TextButton("Close", on_click=_close_dialog)],
        on_dismiss=_on_dismiss,
    )

    page.show_dialog(dlg)
    if is_mobile:
        # Start timer loop immediately on load
        page.run_task(_update_timer_loop)
