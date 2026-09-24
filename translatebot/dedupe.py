"""TTL cache for (message_id, target) dedupe (SPEC 4.3)."""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Callable, Hashable


class TTLCache:
    """A small TTL + LRU cache used to avoid duplicate translations.

    ``check_and_add`` returns True the first time a key is seen within the
    TTL window and False afterwards. The clock is injectable for tests.
    """

    def __init__(
        self,
        ttl: float = 3600.0,
        maxsize: int = 5000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = float(ttl)
        self._maxsize = maxsize
        self._clock = clock
        self._data: "OrderedDict[Hashable, float]" = OrderedDict()

    def check_and_add(self, key: Hashable) -> bool:
        now = self._clock()
        self._evict_expired(now)
        seen_at = self._data.get(key)
        if seen_at is not None and now - seen_at < self._ttl:
            # Refresh recency so repeated hits keep the entry alive in LRU order.
            self._data.move_to_end(key)
            return False
        self._data[key] = now
        self._data.move_to_end(key)
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)
        return True

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: Hashable) -> bool:
        return key in self._data

    def _evict_expired(self, now: float) -> None:
        while self._data:
            _, seen_at = next(iter(self._data.items()))
            if now - seen_at < self._ttl:
                break
            self._data.popitem(last=False)
