"""DeepL translation engine (default)."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import deepl

from .base import Engine, QuotaExceededError, TooManyRequestsError, TranslationError, TranslationResult

if TYPE_CHECKING:
    from ..settings import Settings

log = logging.getLogger("translatebot.engine.deepl")


class DeepLEngine(Engine):
    """Wraps the synchronous deepl SDK via asyncio.to_thread."""

    name = "deepl"

    def __init__(self, settings: "Settings") -> None:
        if not settings.deepl_api_key:
            raise TranslationError(
                "DEEPL_API_KEY is missing in .env / .env icinde DEEPL_API_KEY eksik."
            )
        self._translator = deepl.Translator(settings.deepl_api_key)

    async def translate(self, text: str, target: str) -> TranslationResult:
        try:
            result = await asyncio.to_thread(
                self._translator.translate_text, text, target_lang=target
            )
        except deepl.QuotaExceededException as exc:
            raise QuotaExceededError(str(exc)) from exc
        except deepl.TooManyRequestsException as exc:
            raise TooManyRequestsError(str(exc)) from exc
        except deepl.DeepLException as exc:
            raise TranslationError(f"DeepL error: {exc}") from exc
        source = getattr(result, "detected_source_lang", None)
        return TranslationResult(
            text=result.text,
            source=source.upper() if source else None,
        )

    async def supported_targets(self) -> list[str] | None:
        try:
            langs = await asyncio.to_thread(self._translator.get_target_languages)
        except deepl.DeepLException as exc:
            raise TranslationError(f"DeepL error: {exc}") from exc
        return [lang.code.upper() for lang in langs]

    def usage(self) -> str:
        try:
            usage = self._translator.get_usage()
        except Exception as exc:  # pragma: no cover - network failure path
            log.warning("DeepL usage lookup failed: %s", exc)
            return "usage unavailable"
        if usage.character is None:  # pragma: no cover - unexpected API shape
            return "usage unavailable"
        return f"{usage.character.count:,} / {usage.character.limit:,} characters this period"
