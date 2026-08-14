"""Tests for CreditService daily allowances and spending."""

from __future__ import annotations

import pytest

from core.constants import DAILY_FREE_CREDITS
from services.credit_service import CreditService
from services.storage_service import StorageService


@pytest.mark.asyncio
async def test_initial_credits(tmp_path):
    storage = StorageService(data_dir=str(tmp_path))
    credit_svc = CreditService(storage=storage)

    balance = await credit_svc.get_balance()
    assert balance == DAILY_FREE_CREDITS


@pytest.mark.asyncio
async def test_spend_credits(tmp_path):
    storage = StorageService(data_dir=str(tmp_path))
    credit_svc = CreditService(storage=storage)

    ok, rem = await credit_svc.spend(5)
    assert ok is True
    assert rem == DAILY_FREE_CREDITS - 5

    balance = await credit_svc.get_balance()
    assert balance == DAILY_FREE_CREDITS - 5


@pytest.mark.asyncio
async def test_spend_insufficient_credits(tmp_path):
    storage = StorageService(data_dir=str(tmp_path))
    credit_svc = CreditService(storage=storage)

    ok, rem = await credit_svc.spend(DAILY_FREE_CREDITS + 10)
    assert ok is False
    assert rem == DAILY_FREE_CREDITS


@pytest.mark.asyncio
async def test_add_credits(tmp_path):
    storage = StorageService(data_dir=str(tmp_path))
    credit_svc = CreditService(storage=storage)

    new_bal = await credit_svc.add_credits(25)
    assert new_bal == DAILY_FREE_CREDITS + 25

    balance = await credit_svc.get_balance()
    assert balance == DAILY_FREE_CREDITS + 25
