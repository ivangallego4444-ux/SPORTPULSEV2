from __future__ import annotations

import time

import pytest

from sp_providers.base import Throttle


@pytest.mark.asyncio
async def test_first_call_never_waits():
    throttle = Throttle(min_interval_seconds=1.0)
    start = time.monotonic()
    await throttle.wait()
    assert time.monotonic() - start < 0.05


@pytest.mark.asyncio
async def test_second_call_waits_out_the_remaining_interval():
    # Regression test: pacing used to live only *inside* get_rounds
    # (between rounds of the same competition), so loading several
    # competitions back-to-back — e.g. the home dashboard — still burst
    # past the free key's limit because nothing paced the handoff
    # *between* them. One Throttle instance shared by the whole provider
    # closes that gap for every call it makes, not just same-method ones.
    throttle = Throttle(min_interval_seconds=0.1)
    await throttle.wait()
    start = time.monotonic()
    await throttle.wait()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.09  # small tolerance for scheduler jitter


@pytest.mark.asyncio
async def test_no_wait_once_enough_real_time_has_passed():
    import asyncio

    throttle = Throttle(min_interval_seconds=0.05)
    await throttle.wait()
    await asyncio.sleep(0.1)
    start = time.monotonic()
    await throttle.wait()
    assert time.monotonic() - start < 0.03
