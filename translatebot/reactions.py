"""Per-channel sequential reaction queue, rate-limit friendly (SPEC 4.2)."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from .store import Store

log = logging.getLogger("translatebot.reactions")

QUEUE_MAXSIZE = 200
REACTION_INTERVAL = 0.3  # seconds between add_reaction calls per channel
FORBIDDEN_WARN_INTERVAL = 600.0  # 10 minutes


class ReactionQueue:
    """Adds flag reactions one by one per channel via lazy worker tasks."""

    def __init__(self, store: "Store | None" = None) -> None:
        self._store = store
        self._queues: dict[int, asyncio.Queue] = {}
        self._workers: dict[int, asyncio.Task] = {}
        self._forbidden_warned: dict[int, float] = {}
        self._closed = False

    def enqueue(self, message: discord.Message, emojis: list[str], max_lag: float = 45.0) -> None:
        """Queue a message to receive ``emojis``; drops the oldest item if full."""
        if not emojis or self._closed:
            return
        key = message.channel.id
        queue = self._queues.get(key)
        if queue is None:
            queue = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
            self._queues[key] = queue
        item = (message, list(emojis), time.monotonic(), float(max_lag))
        if queue.full():
            try:
                queue.get_nowait()  # drop oldest
            except asyncio.QueueEmpty:  # pragma: no cover - race guard
                pass
        queue.put_nowait(item)
        worker = self._workers.get(key)
        if worker is None or worker.done():
            self._workers[key] = asyncio.create_task(self._worker(key, queue))

    async def _worker(self, key: int, queue: asyncio.Queue) -> None:
        while True:
            message, emojis, enqueued_at, max_lag = await queue.get()
            try:
                if time.monotonic() - enqueued_at > max_lag:
                    log.debug("Skipping stale message %s (queued too long)", message.id)
                    self._bump_stale(message)
                    continue
                for emoji in emojis:
                    try:
                        await message.add_reaction(emoji)
                    except discord.NotFound:
                        log.debug("Message %s deleted, dropping its remaining flags", message.id)
                        break
                    except discord.Forbidden:
                        self._warn_forbidden(key)
                        break
                    except discord.HTTPException as exc:
                        log.warning("add_reaction failed for message %s: %s", message.id, exc)
                    await asyncio.sleep(REACTION_INTERVAL)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Reaction worker for channel %s crashed on an item", key)
            finally:
                queue.task_done()

    def _bump_stale(self, message: discord.Message) -> None:
        if self._store is None or message.guild is None:
            return
        try:
            self._store.stats(message.guild.id)["skipped_stale"] += 1
            self._store.mark_dirty()
        except Exception:  # pragma: no cover - stats must never break the worker
            log.exception("Failed to record skipped_stale stat")

    def _warn_forbidden(self, key: int) -> None:
        now = time.monotonic()
        if now - self._forbidden_warned.get(key, 0.0) < FORBIDDEN_WARN_INTERVAL:
            return
        self._forbidden_warned[key] = now
        log.warning(
            "Missing Add Reactions permission in channel %s (warned once per 10 minutes).",
            key,
        )

    async def close(self) -> None:
        """Cancel all workers (called from bot.close)."""
        self._closed = True
        for worker in self._workers.values():
            worker.cancel()
        if self._workers:
            await asyncio.gather(*self._workers.values(), return_exceptions=True)
        self._workers.clear()
        self._queues.clear()
