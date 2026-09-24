"""Tests for translatebot.dedupe.TTLCache (SPEC 4.3)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translatebot.dedupe import TTLCache


class FakeClock:
    """Deterministic clock injected into TTLCache."""

    def __init__(self, start: float = 1000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_first_true_second_false():
    clock = FakeClock()
    cache = TTLCache(ttl=3600.0, clock=clock)
    key = (111222333, "TR")
    assert cache.check_and_add(key) is True
    assert cache.check_and_add(key) is False


def test_distinct_keys_are_independent():
    clock = FakeClock()
    cache = TTLCache(clock=clock)
    assert cache.check_and_add(("m1", "TR")) is True
    assert cache.check_and_add(("m2", "TR")) is True
    assert cache.check_and_add(("m1", "TR")) is False
    assert cache.check_and_add(("m1", "EN")) is True


def test_key_fresh_again_after_ttl():
    clock = FakeClock()
    cache = TTLCache(ttl=10.0, clock=clock)
    assert cache.check_and_add("k") is True
    clock.advance(5.0)
    assert cache.check_and_add("k") is False
    clock.advance(6.0)  # total 11 s > ttl 10 s
    assert cache.check_and_add("k") is True


def test_maxsize_drops_oldest():
    clock = FakeClock()
    cache = TTLCache(ttl=100.0, maxsize=2, clock=clock)
    assert cache.check_and_add("A") is True
    clock.advance(1.0)
    assert cache.check_and_add("B") is True
    clock.advance(1.0)
    assert cache.check_and_add("C") is True  # cache full -> oldest ("A") dropped
    assert cache.check_and_add("A") is True  # A was evicted, counts as fresh
    assert cache.check_and_add("C") is False  # C is still cached


def test_ttl_zero_always_expired():
    clock = FakeClock()
    cache = TTLCache(ttl=0.0, clock=clock)
    for _ in range(3):
        assert cache.check_and_add("x") is True
        clock.advance(0.001)


def test_default_clock_construction():
    cache = TTLCache()
    assert cache.check_and_add(42) is True
    assert cache.check_and_add(42) is False
    assert cache.check_and_add(43) is True
