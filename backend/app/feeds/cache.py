"""Tiny time-to-live cache for live feed responses.

In-memory is fine for the single-service MVP (smooths external rate limits like
OpenSky's). Swap for Redis when we scale to multiple instances.
"""

from __future__ import annotations

import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: float) -> None:
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.time() - ts > self.ttl:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.time(), value)
