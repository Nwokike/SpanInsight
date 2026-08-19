"""use_debounce - debounce a value across renders.

Ported from ktv-player's proven implementation.
"""

from __future__ import annotations

import asyncio

import flet as ft


def use_debounce(value, delay_ms: int = 300):
    """Return a debounced version of *value*.

    The debounced value updates only after *delay_ms* milliseconds of
    inactivity.  Useful for search fields to avoid spamming backends.
    """
    debounced, set_debounced = ft.use_state(value)
    timer = ft.use_ref(None)

    async def _schedule():
        old = timer.current
        if old is not None and not old.done():
            old.cancel()

        async def _after():
            await asyncio.sleep(delay_ms / 1000.0)
            set_debounced(value)

        timer.current = asyncio.create_task(_after())

    def _cleanup():
        old = timer.current
        if old is not None and not old.done():
            old.cancel()

    ft.use_effect(_schedule, [value], cleanup=_cleanup)

    return debounced
