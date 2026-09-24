"""Engine factory (SPEC section 1 tree: engines/__init__.py -> build_engine)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import (
    Engine,
    QuotaExceededError,
    TooManyRequestsError,
    TranslationError,
    TranslationResult,
)

if TYPE_CHECKING:
    from ..settings import Settings

__all__ = [
    "Engine",
    "QuotaExceededError",
    "TooManyRequestsError",
    "TranslationError",
    "TranslationResult",
    "build_engine",
]


def build_engine(settings: "Settings") -> Engine:
    """Create the engine selected by ``ENGINE`` (deepl | claude)."""
    if settings.engine == "claude":
        from .claude_engine import ClaudeEngine

        return ClaudeEngine(settings)
    from .deepl_engine import DeepLEngine

    return DeepLEngine(settings)
