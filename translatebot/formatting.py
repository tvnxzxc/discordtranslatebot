"""Reply formatting and 2000-character-safe chunking (SPEC 4.3)."""

from __future__ import annotations


def format_reply(
    flag: str,
    lang_name: str,
    source_base: str | None,
    target_code: str,
    text: str,
) -> str:
    """Build the reply header + translation body.

    Header: ``🇹🇷 **Türkçe** · PT → TR`` (metadata omitted when the source
    language is unknown).
    """
    head = f"{flag} **{lang_name}**"
    if source_base:
        head += f" · {source_base} → {target_code}"
    body = text or ""
    if not body:
        return head
    return f"{head}\n{body}"


def chunk(text: str, limit: int = 1900) -> list[str]:
    """Split ``text`` into pieces of at most ``limit`` characters.

    Prefers word boundaries and never loses characters (a piece may start
    with the space that separated it from the previous one).
    """
    text = text or ""
    if not text:
        return []
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    remaining = text
    while len(remaining) > limit:
        cut = remaining.rfind(" ", 1, limit + 1)
        if cut <= 0:
            cut = limit
        parts.append(remaining[:cut])
        remaining = remaining[cut:]
    if remaining:
        parts.append(remaining)
    return parts


def already_note(lang_name: str) -> str:
    """Short note used when the message is already in the target language."""
    return f"Already in {lang_name}."
