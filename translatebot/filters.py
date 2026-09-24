"""Pure filter deciding whether a message qualifies for auto flags (SPEC 4.2)."""

from __future__ import annotations

import re

_STRIP_PATTERNS = (
    re.compile(r"<a?:\w+:\d+>"),  # custom emoji
    re.compile(r"<@!?\d+>"),  # user mentions
    re.compile(r"<@&\d+>"),  # role mentions
    re.compile(r"<#\d+>"),  # channel mentions
    re.compile(r"https?://\S+", re.IGNORECASE),  # URLs
)

_COMMAND_PREFIXES = "!.?-$"


def qualifies(content: str, min_chars: int = 5, *, from_bot: bool = False) -> bool:
    """True if ``content`` still has >= ``min_chars`` letters/chars after
    stripping mentions, custom emoji, URLs and whitespace, contains at least
    one alphabetic character, and does not start with a bot command prefix.
    Bot messages never qualify; the caller passes ``from_bot=True`` for them.
    """
    if from_bot:
        return False
    text = content or ""
    for pattern in _STRIP_PATTERNS:
        text = pattern.sub("", text)
    text = "".join(text.split())
    if len(text) < min_chars:
        return False
    if text[0] in _COMMAND_PREFIXES:
        return False
    return any(ch.isalpha() for ch in text)
