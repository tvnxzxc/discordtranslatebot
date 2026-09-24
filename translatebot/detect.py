"""Source-language detection with langdetect (best-effort, optional)."""

from __future__ import annotations

import logging

log = logging.getLogger("translatebot.detect")

try:  # pragma: no cover - exercised implicitly when langdetect is installed
    from langdetect import DetectorFactory, detect as _detect

    # Make results deterministic across runs (recommended by langdetect docs).
    DetectorFactory.seed = 0
    _AVAILABLE = True
except Exception:  # pragma: no cover - langdetect missing at runtime
    _AVAILABLE = False


def detect_lang(text: str) -> str | None:
    """Return a langdetect code like ``"tr"``/``"zh-cn"``, or None."""
    if not _AVAILABLE:
        return None
    if not text or not text.strip():
        return None
    try:
        return _detect(text)
    except Exception:
        # langdetect raises LangDetectException on empty/no-feature text.
        return None


def detection_base(code: str | None) -> str | None:
    """Normalize a langdetect code to an upper-case base code ("zh-cn" -> "ZH")."""
    if not code:
        return None
    return code.split("-", 1)[0].upper()
