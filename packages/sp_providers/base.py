from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx


class TTLCache:
    """Minimal in-memory cache so we don't hammer free-tier rate limits
    (TheSportsDB's public key starts returning HTTP 429 after a burst of
    requests — confirmed while building this). No external cache service,
    no cost.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._known_good: dict[str, Any] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        self._store[key] = (time.monotonic() + ttl_seconds, value)

    def set_known_good(self, key: str, value: Any) -> None:
        """Remembers the last real, complete fetch for this key, kept
        indefinitely (until overwritten by a newer known-good fetch) —
        independent of the short-lived entry above. A transient rate
        limit must never erase data that was already successfully
        loaded; see get_known_good()."""
        self._known_good[key] = value

    def get_known_good(self, key: str) -> Any | None:
        return self._known_good.get(key)

    def export_known_good(self) -> dict[str, Any]:
        """Raw snapshot of every remembered known-good value, for a
        caller to persist to disk (see TheSportsDBProvider) — kept
        generic here since this cache has no opinion on how its values
        serialize."""
        return dict(self._known_good)

    def import_known_good(self, data: dict[str, Any]) -> None:
        """Restores known-good values from a previous export (e.g. loaded
        from disk at startup). Never touches the short-lived `_store`."""
        self._known_good.update(data)


class Throttle:
    """Enforces a minimum gap between *any* two calls through one
    instance — not just within a single method. Built after discovering
    live that pacing requests only *within* one competition's round fetch
    wasn't enough: loading several competitions back-to-back (e.g. the
    home dashboard scanning 5 football leagues) still bursts past
    TheSportsDB's free-key limit, because nothing paced the handoff
    *between* competitions. One `Throttle` shared by a provider's single
    instance (already a module-level singleton in apps/api) naturally
    serializes every request that provider makes, app-wide.
    """

    def __init__(self, min_interval_seconds: float) -> None:
        self._min_interval = min_interval_seconds
        self._last_call: float | None = None

    async def wait(self) -> None:
        now = time.monotonic()
        if self._last_call is not None:
            elapsed = now - self._last_call
            remaining = self._min_interval - elapsed
            if remaining > 0:
                await asyncio.sleep(remaining)
        self._last_call = time.monotonic()


async def fetch_json(client: httpx.AsyncClient, url: str, params: dict | None = None) -> Any | None:
    """Fetch JSON and return None on any failure (bad status, empty body,
    invalid JSON, rate limit) instead of raising — callers must treat None
    as "no data available right now", never as "show nothing happened".
    """
    try:
        response = await client.get(url, params=params, timeout=10.0)
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    try:
        return response.json()
    except ValueError:
        return None
