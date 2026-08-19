"""Local credit economy service.

All tracking is local. 50 free credits daily, reset on date change.

FIX: Replaced global cumulative _reserved integer with transaction-keyed
dictionary to prevent reservation corruption from overlapping commits/rollbacks.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

import flet as ft

from core.constants import (
    DAILY_FREE_CREDITS,
    STORAGE_CREDITS,
    STORAGE_LAST_RESET,
)

logger = logging.getLogger(__name__)


class CreditService:
    """Manages the local credit economy."""

    def __init__(self, page: ft.Page | None = None, storage=None):
        if storage is None and page is not None and not isinstance(page, ft.Page):
            storage = page
            page = None
        self._page = page
        self._storage = storage
        self._reservations: dict[str, int] = {}  # tx_id -> amount
        self._rollback_tasks: dict[
            str, asyncio.Task
        ] = {}  # tx_id -> auto-rollback task

    async def initialize(self) -> int:
        """Load credits from storage, reset if new day. Returns current balance."""
        await self._check_daily_reset()
        return await self._get_credits()

    async def reserve(self, amount: int) -> str | None:
        """Optimistically reserve credits. Returns transaction ID or None if insufficient.

        Use this before expensive operations to prevent race conditions.
        Call commit(tx_id) to finalize or rollback(tx_id) to release.
        Auto-rollback after 60 seconds if not committed.
        """
        current = await self._get_credits()
        total_reserved = sum(self._reservations.values())
        if current - total_reserved < amount:
            return None

        tx_id = str(uuid.uuid4())
        self._reservations[tx_id] = amount

        async def _auto_rollback():
            await asyncio.sleep(60)
            if tx_id in self._reservations:
                del self._reservations[tx_id]
                self._rollback_tasks.pop(tx_id, None)
                logger.warning(
                    "Auto-rolled back %d reserved credits (tx: %s).", amount, tx_id
                )

        self._rollback_tasks[tx_id] = asyncio.create_task(_auto_rollback())
        return tx_id

    async def commit(self, tx_id: str) -> int:
        """Finalize a reservation - deduct from actual balance."""
        from core.state import state

        task = self._rollback_tasks.pop(tx_id, None)
        if task:
            task.cancel()
        amount = self._reservations.pop(tx_id, 0)
        if amount == 0:
            return await self._get_credits()

        current = await self._get_credits()
        new_balance = max(0, current - amount)
        await self._storage.set(STORAGE_CREDITS, str(new_balance))
        state.credits_remaining = new_balance
        logger.info(
            "Committed %d credits (tx: %s). Remaining: %d", amount, tx_id, new_balance
        )
        return new_balance

    async def rollback(self, tx_id: str) -> None:
        """Release a reservation without deducting credits."""
        task = self._rollback_tasks.pop(tx_id, None)
        if task:
            task.cancel()
        self._reservations.pop(tx_id, None)

    async def spend(self, amount: int) -> tuple[bool, int]:
        """Deduct credits directly (no reservation). Returns (success, remaining)."""
        from core.state import state

        current = await self._get_credits()
        total_reserved = sum(self._reservations.values())
        if current - total_reserved < amount:
            return False, current
        new_balance = current - amount
        await self._storage.set(STORAGE_CREDITS, str(new_balance))
        state.credits_remaining = new_balance
        logger.info("Spent %d credits. Remaining: %d", amount, new_balance)
        return True, new_balance

    async def add_credits(self, amount: int) -> int:
        """Add credits to the user's balance. Returns the new balance."""
        from core.state import state

        current = await self._get_credits()
        new_balance = current + amount
        await self._storage.set(STORAGE_CREDITS, str(new_balance))
        state.credits_remaining = new_balance
        logger.info("Added %d credits. New Balance: %d", amount, new_balance)
        return new_balance

    async def get_balance(self) -> int:
        """Return current credit balance."""
        return await self._get_credits()

    async def check_balance(self, amount: int) -> tuple[bool, int]:
        """Check if user has enough credits without spending. Returns (has_enough, balance)."""
        balance = await self._get_credits()
        return balance >= amount, balance

    async def get_daily_cap(self) -> int:
        """Return the daily credit cap."""
        return DAILY_FREE_CREDITS

    async def _check_daily_reset(self) -> None:
        """Reset credits if the date has changed, topping up to the daily cap while preserving higher balances."""
        from core.state import state

        today = datetime.now(tz=UTC).date().isoformat()
        last_reset = await self._storage.get(STORAGE_LAST_RESET)
        if last_reset != today:
            current = await self._get_credits()
            daily_cap = await self.get_daily_cap()
            new_balance = max(current, daily_cap)
            await self._storage.set(STORAGE_CREDITS, str(new_balance))
            await self._storage.set(STORAGE_LAST_RESET, today)
            state.credits_remaining = new_balance
            self._reservations.clear()
            logger.info(
                "Daily credit reset check: balance topped up/preserved at %d.",
                new_balance,
            )

    async def _get_credits(self) -> int:
        val = await self._storage.get(STORAGE_CREDITS)
        try:
            return int(val) if val else DAILY_FREE_CREDITS
        except TypeError, ValueError:
            return DAILY_FREE_CREDITS
