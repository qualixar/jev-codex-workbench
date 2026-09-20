"""Isolated demonstration: a TTL boundary defect is intentionally present.
Do not import this demonstration cache into production code.
"""
from collections.abc import Callable
from typing import Any

class TTLCache:
    def __init__(self, clock: Callable[[], float]):
        self.clock = clock
        self.entries: dict[str, tuple[Any, float]] = {}

    def put(self, key: str, value: Any, ttl: float) -> None:
        if ttl < 0:
            raise ValueError("TTL must be nonnegative")
        self.entries[key] = (value, self.clock() + ttl)

    def get(self, key: str) -> Any:
        item = self.entries.get(key)
        if item is None:
            return None
        value, expires_at = item
        # Requirement: a value must be absent at OR after its expiry instant.
        # Codex must diagnose the supplied failing test and make the minimal fix.
        if self.clock() > expires_at:
            del self.entries[key]
            return None
        return value
