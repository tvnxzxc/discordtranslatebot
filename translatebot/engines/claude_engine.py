"""Optional Claude translation engine (lazy anthropic import, SPEC section 1)."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from ..flags import LANG_NAMES, LANG_NAMES_EN
from .base import Engine, TranslationError, TranslationResult

if TYPE_CHECKING:
    from ..settings import Settings

log = logging.getLogger("translatebot.engine.claude")

_SYSTEM_PROMPT = (
    "You are a translation engine. Translate the user's text into the requested "
    "target language. Reply with ONLY the translation: no explanations, no quotes, "
    "no language names. Preserve emojis, @mentions, URLs, formatting and line breaks."
)


class ClaudeEngine(Engine):
    """Translates with the Claude Messages API. ``supported_targets`` is None
    (every flag is considered supported)."""

    name = "claude"

    def __init__(self, settings: "Settings") -> None:
        if not settings.anthropic_api_key:
            raise TranslationError(
                "ANTHROPIC_API_KEY is missing in .env / .env icinde ANTHROPIC_API_KEY eksik."
            )
        try:
            import anthropic  # lazy: only needed when ENGINE=claude
        except ImportError as exc:
            raise TranslationError(
                "The 'anthropic' package is not installed. Install it with: pip install anthropic"
            ) from exc
        self._client: Any = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.claude_model or "claude-haiku-4-5"

    async def translate(self, text: str, target: str) -> TranslationResult:
        lang_name = LANG_NAMES.get(target) or LANG_NAMES_EN.get(target) or target
        prompt = f"Target language: {lang_name} ({target}).\n\nText to translate:\n{text}"

        def _call() -> Any:
            return self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

        try:
            response = await asyncio.to_thread(_call)
        except Exception as exc:
            raise TranslationError(f"Claude API error: {exc}") from exc
        translated = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()
        if not translated:
            raise TranslationError("Claude returned an empty translation")
        return TranslationResult(text=translated, source=None)

    async def supported_targets(self) -> list[str] | None:
        return None

    def usage(self) -> str:
        return "Claude engine (no monthly character quota)"
