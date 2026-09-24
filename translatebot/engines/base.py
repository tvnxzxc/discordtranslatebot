"""Translation engine protocol and shared result/error types (SPEC section 0)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..settings import Settings


class TranslationError(Exception):
    """Base class for engine failures; the bot never crashes on these."""


class QuotaExceededError(TranslationError):
    """Monthly translation quota exhausted (DeepL 456)."""


class TooManyRequestsError(TranslationError):
    """Rate limited by the engine (HTTP 429)."""


@dataclass(frozen=True)
class TranslationResult:
    """Translated text plus the detected source language code (may be None)."""

    text: str
    source: str | None = None


class Engine(ABC):
    """A translation backend. Implementations must never raise raw SDK errors;
    normalize them into TranslationError subclasses."""

    name: str = "base"

    @abstractmethod
    async def translate(self, text: str, target: str) -> TranslationResult:
        """Translate ``text`` into ``target`` (a DeepL target code)."""

    @abstractmethod
    async def supported_targets(self) -> list[str] | None:
        """Target language codes the engine accepts; None = everything."""

    @abstractmethod
    def usage(self) -> str:
        """Human-readable usage line for /stats, e.g. quota consumption."""

    async def close(self) -> None:  # pragma: no cover - default no-op
        """Release resources (no-op by default)."""
