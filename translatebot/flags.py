"""Flag emoji <-> language code mapping (SPEC 4.1).

Pure module: no discord/deepl/langdetect imports.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger("translatebot.flags")

REGIONAL_INDICATOR_START = 0x1F1E6
REGIONAL_INDICATOR_END = 0x1F1FF
GLOBE = "\U0001F310"  # 🌐

# Country code -> DeepL target code (SPEC 4.1 table).
COUNTRY_TO_LANG: dict[str, str] = {
    # English
    "GB": "EN-GB", "AU": "EN-GB", "NZ": "EN-GB", "IE": "EN-GB", "ZA": "EN-GB", "NG": "EN-GB", "SG": "EN-GB",
    "US": "EN-US", "CA": "EN-US",
    # Turkish
    "TR": "TR",
    # German
    "DE": "DE", "AT": "DE", "CH": "DE", "LI": "DE",
    # French
    "FR": "FR", "BE": "FR", "LU": "FR", "MC": "FR", "SN": "FR", "CI": "FR",
    "ES": "ES",
    # Latin American Spanish
    "MX": "ES-419", "AR": "ES-419", "CO": "ES-419", "CL": "ES-419", "PE": "ES-419", "VE": "ES-419",
    "EC": "ES-419", "UY": "ES-419", "PY": "ES-419", "BO": "ES-419", "CU": "ES-419", "DO": "ES-419",
    "GT": "ES-419", "HN": "ES-419", "SV": "ES-419", "NI": "ES-419", "CR": "ES-419", "PA": "ES-419",
    "PR": "ES-419",
    # Portuguese
    "PT": "PT-PT", "AO": "PT-PT", "MZ": "PT-PT",
    "BR": "PT-BR",
    "IT": "IT", "SM": "IT", "VA": "IT",
    "NL": "NL",
    "PL": "PL",
    "RU": "RU", "BY": "RU",
    "UA": "UK",
    # Arabic
    "SA": "AR", "AE": "AR", "EG": "AR", "IQ": "AR", "JO": "AR", "KW": "AR", "QA": "AR", "BH": "AR",
    "OM": "AR", "YE": "AR", "SY": "AR", "LB": "AR", "LY": "AR", "SD": "AR", "PS": "AR", "MA": "AR",
    "DZ": "AR", "TN": "AR",
    "IR": "FA", "AF": "FA",
    "IL": "HE",
    "CN": "ZH-HANS",
    "TW": "ZH-HANT", "HK": "ZH-HANT", "MO": "ZH-HANT",
    "JP": "JA",
    "KR": "KO", "KP": "KO",
    "VN": "VI",
    "TH": "TH",
    "ID": "ID",
    "MY": "MS",
    "PH": "TL",
    "IN": "HI",
    "PK": "UR",
    "BD": "BN",
    "GR": "EL", "CY": "EL",
    "SE": "SV",
    "NO": "NB",
    "DK": "DA",
    "FI": "FI",
    "IS": "IS",
    "EE": "ET",
    "LV": "LV",
    "LT": "LT",
    "CZ": "CS",
    "SK": "SK",
    "HU": "HU",
    "RO": "RO", "MD": "RO",
    "BG": "BG",
    "RS": "SR", "ME": "SR",
    "HR": "HR",
    "SI": "SL",
    "BA": "BS",
    "MK": "MK",
    "AL": "SQ", "XK": "SQ",
    "GE": "KA",
    "AM": "HY",
    "AZ": "AZ",
    "KZ": "KK",
    "UZ": "UZ",
    "MN": "MN",
    "KH": "KM",
    "LA": "LO",
    "MM": "MY",
    "ET": "AM",
    "KE": "SW", "TZ": "SW",
}

# Target code -> native name (SPEC 4.1).
LANG_NAMES: dict[str, str] = {
    "EN": "English",
    "EN-GB": "English (UK)",
    "EN-US": "English (US)",
    "TR": "Türkçe",
    "DE": "Deutsch",
    "FR": "Français",
    "ES": "Español",
    "ES-419": "Español (Latinoamérica)",
    "PT": "Português",
    "PT-PT": "Português (Portugal)",
    "PT-BR": "Português (Brasil)",
    "IT": "Italiano",
    "NL": "Nederlands",
    "PL": "Polski",
    "RU": "Русский",
    "UK": "Українська",
    "AR": "العربية",
    "FA": "فارسی",
    "HE": "עברית",
    "ZH": "中文",
    "ZH-HANS": "简体中文",
    "ZH-HANT": "繁體中文",
    "JA": "日本語",
    "KO": "한국어",
    "VI": "Tiếng Việt",
    "TH": "ไทย",
    "ID": "Bahasa Indonesia",
    "MS": "Bahasa Melayu",
    "TL": "Tagalog",
    "HI": "हिन्दी",
    "UR": "اردو",
    "BN": "বাংলা",
    "EL": "Ελληνικά",
    "SV": "Svenska",
    "NB": "Norsk",
    "DA": "Dansk",
    "FI": "Suomi",
    "IS": "Íslenska",
    "ET": "Eesti",
    "LV": "Latviešu",
    "LT": "Lietuvių",
    "CS": "Čeština",
    "SK": "Slovenčina",
    "HU": "Magyar",
    "RO": "Română",
    "BG": "Български",
    "SR": "Српски",
    "HR": "Hrvatski",
    "SL": "Slovenščina",
    "BS": "Bosanski",
    "MK": "Македонски",
    "SQ": "Shqip",
    "KA": "ქართული",
    "HY": "Հայերեն",
    "AZ": "Azərbaycan",
    "KK": "Қазақша",
    "UZ": "Oʻzbekcha",
    "MN": "Монгол",
    "KM": "ភាសាខ្មែរ",
    "LO": "ລາວ",
    "MY": "မြန်မာဘာသာ",
    "AM": "አማርኛ",
    "SW": "Kiswahili",
}

# Target code -> English name (used by autocomplete search).
LANG_NAMES_EN: dict[str, str] = {
    "EN": "English",
    "EN-GB": "English (UK)",
    "EN-US": "English (US)",
    "TR": "Turkish",
    "DE": "German",
    "FR": "French",
    "ES": "Spanish",
    "ES-419": "Spanish (Latin America)",
    "PT": "Portuguese",
    "PT-PT": "Portuguese (Portugal)",
    "PT-BR": "Portuguese (Brazil)",
    "IT": "Italian",
    "NL": "Dutch",
    "PL": "Polish",
    "RU": "Russian",
    "UK": "Ukrainian",
    "AR": "Arabic",
    "FA": "Persian",
    "HE": "Hebrew",
    "ZH": "Chinese",
    "ZH-HANS": "Chinese (Simplified)",
    "ZH-HANT": "Chinese (Traditional)",
    "JA": "Japanese",
    "KO": "Korean",
    "VI": "Vietnamese",
    "TH": "Thai",
    "ID": "Indonesian",
    "MS": "Malay",
    "TL": "Tagalog",
    "HI": "Hindi",
    "UR": "Urdu",
    "BN": "Bengali",
    "EL": "Greek",
    "SV": "Swedish",
    "NB": "Norwegian (Bokmal)",
    "DA": "Danish",
    "FI": "Finnish",
    "IS": "Icelandic",
    "ET": "Estonian",
    "LV": "Latvian",
    "LT": "Lithuanian",
    "CS": "Czech",
    "SK": "Slovak",
    "HU": "Hungarian",
    "RO": "Romanian",
    "BG": "Bulgarian",
    "SR": "Serbian",
    "HR": "Croatian",
    "SL": "Slovenian",
    "BS": "Bosnian",
    "MK": "Macedonian",
    "SQ": "Albanian",
    "KA": "Georgian",
    "HY": "Armenian",
    "AZ": "Azerbaijani",
    "KK": "Kazakh",
    "UZ": "Uzbek",
    "MN": "Mongolian",
    "KM": "Khmer",
    "LO": "Lao",
    "MY": "Burmese",
    "AM": "Amharic",
    "SW": "Swahili",
}

# Display flag for a language code (SPEC 4.1: EN->GB, ES->ES, PT->BR, ZH->CN, AR->SA).
_PREFERRED_CC: dict[str, str] = {"EN": "GB", "ES": "ES", "PT": "BR", "ZH": "CN", "AR": "SA"}


def emoji_to_country(emoji: str) -> str | None:
    """Two regional indicator characters -> two-letter country code, else None."""
    if not emoji:
        return None
    # Emoji pickers often append a variation selector (U+FE0F); ignore it.
    emoji = emoji.replace("️", "")
    if len(emoji) != 2:
        return None
    first, second = ord(emoji[0]), ord(emoji[1])
    if not (
        REGIONAL_INDICATOR_START <= first <= REGIONAL_INDICATOR_END
        and REGIONAL_INDICATOR_START <= second <= REGIONAL_INDICATOR_END
    ):
        return None
    return (
        chr(first - REGIONAL_INDICATOR_START + ord("A"))
        + chr(second - REGIONAL_INDICATOR_START + ord("A"))
    )


def country_to_emoji(cc: str) -> str:
    """Two-letter country code -> flag emoji (assumes valid input)."""
    return "".join(
        chr(ord(ch) - ord("A") + REGIONAL_INDICATOR_START) for ch in cc.upper()[:2]
    )


def base_code(code: str) -> str:
    """Strip a regional/variant suffix: "PT-BR" -> "PT", "ES-419" -> "ES", "ZH-HANT" -> "ZH"."""
    return (code or "").split("-", 1)[0].upper()


def preferred_flag(code: str) -> str:
    """Flag shown for a language code in UI elements."""
    base = base_code(code)
    override = _PREFERRED_CC.get(base)
    if override:
        return country_to_emoji(override)
    for cc, target in COUNTRY_TO_LANG.items():
        if base_code(target) == base:
            return country_to_emoji(cc)
    return GLOBE


def parse_flags(text: str) -> list[str]:
    """Extract flag emojis from text, in order, deduplicated."""
    out: list[str] = []
    if not text:
        return out
    i = 0
    last = len(text) - 1
    while i < last:
        pair = text[i : i + 2]
        if emoji_to_country(pair) is not None:
            if pair not in out:
                out.append(pair)
            i += 2
        else:
            i += 1
    return out


def _normalize_name(text: str) -> str:
    """Lower-case, strip punctuation, collapse whitespace ("English (US)" -> "english us")."""
    return " ".join(
        "".join(ch if ch.isalnum() else " " for ch in text.lower()).split()
    )


def _language_flag_lookup() -> dict[str, str]:
    """Normalized language names/English names/codes -> display flag."""
    lookup: dict[str, str] = {}
    for code in set(LANG_NAMES) | set(LANG_NAMES_EN):
        # Variant names/codes ("English (US)", "en-us") get the flag of a
        # country mapping to that exact code; bare names keep preferred_flag.
        exact = next(
            (country_to_emoji(cc) for cc, target in COUNTRY_TO_LANG.items() if target == code),
            None,
        )
        display = exact or preferred_flag(code)
        for name in (LANG_NAMES.get(code), LANG_NAMES_EN.get(code), code):
            if name:
                key = _normalize_name(name)
                if key and key not in lookup:
                    lookup[key] = display
    return lookup


def resolve_flags_input(text: str) -> tuple[list[str], list[str]]:
    """Parse /flags input containing flag emojis and/or language names.

    Accepts flag emojis mixed with language names in English, in the
    language itself ("turkish", "Türkçe", "arabic", "العربية") or codes
    ("tr", "ja", "en-gb"). Returns ``(flags, unknown_words)``: flags are
    ordered and deduplicated display flags (emojis first, then names);
    unknown_words are fragments that matched nothing (lower-cased).
    """
    flags: list[str] = []
    for emoji in parse_flags(text or ""):
        if emoji not in flags:
            flags.append(emoji)
    remainder = text or ""
    for emoji in parse_flags(remainder):
        remainder = remainder.replace(emoji, " ")
    lookup = _language_flag_lookup()
    words = _normalize_name(remainder).split()
    unknown: list[str] = []
    i = 0
    while i < len(words):
        matched = False
        for size in (4, 3, 2, 1):  # longest name first ("english uk" beats "english")
            if i + size > len(words):
                continue
            flag = lookup.get(" ".join(words[i : i + size]))
            if flag:
                if flag not in flags:
                    flags.append(flag)
                i += size
                matched = True
                break
        if not matched:
            unknown.append(words[i])
            i += 1
    return flags, unknown


@dataclass(frozen=True)
class ResolvedLang:
    """A flag emoji resolved to a concrete translation target code."""

    code: str
    flag: str


@dataclass
class FlagResolver:
    """Resolves flag emojis against the engine's supported target languages.

    ``supported_targets=None`` means "everything supported" (Claude engine).
    Resolution per SPEC 4.1: use the exact target code if supported, else its
    base code if that is supported, else the flag is disabled.
    """

    supported_targets: list[str] | None = None
    _supported: frozenset[str] | None = field(init=False, default=None)
    _disabled: list[str] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        if self.supported_targets is not None:
            self._supported = frozenset(t.upper() for t in self.supported_targets)

    def resolve(self, emoji: str) -> ResolvedLang | None:
        cc = emoji_to_country(emoji)
        if cc is None or cc not in COUNTRY_TO_LANG:
            return None
        code = self._pick(COUNTRY_TO_LANG[cc])
        if code is None:
            if emoji not in self._disabled:
                self._disabled.append(emoji)
                log.warning(
                    "%s %s not supported by engine, disabled", emoji, COUNTRY_TO_LANG[cc]
                )
            return None
        return ResolvedLang(code=code, flag=emoji)

    def is_supported(self, emoji: str) -> bool:
        return self.resolve(emoji) is not None

    @property
    def disabled(self) -> list[str]:
        """Flag emojis disabled because the engine lacks the language."""
        return list(self._disabled)

    def _pick(self, target: str) -> str | None:
        if self._supported is None:
            return target
        if target in self._supported:
            return target
        base = base_code(target)
        if base in self._supported:
            return base
        return None
