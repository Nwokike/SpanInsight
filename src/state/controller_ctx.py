"""Controller context — exposes AppController callbacks to the component tree.

Components read controller methods via ``ft.use_context(ControllerMethodsCtx)``
to trigger navigation, analysis, theme toggles, etc.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import flet as ft


async def _noop_async() -> None:
    """No-op default."""


def _noop_sync(*_args, **_kwargs) -> None:
    """No-op sync default."""


@dataclass
class ControllerMethods:
    """Callbacks from AppController exposed to the component tree."""

    start_analysis: Callable[..., None] = _noop_sync
    toggle_theme: Callable[[], None] = _noop_sync
    check_update: Callable[[], Awaitable[None]] = _noop_async
    open_url: Callable[[str], Awaitable[None]] = _noop_async


ControllerMethodsCtx = ft.create_context(ControllerMethods())

__all__ = ["ControllerMethods", "ControllerMethodsCtx"]
