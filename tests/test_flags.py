"""Tests for translatebot.flags (SPEC 4.1)."""

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translatebot.flags import (
    COUNTRY_TO_LANG,
    LANG_NAMES,
    LANG_NAMES_EN,
    FlagResolver,
    ResolvedLang,
    base_code,
    country_to_emoji,
    emoji_to_country,
    parse_flags,
    preferred_flag,
)

TR_FLAG = "🇹🇷"
GB_FLAG = "🇬🇧"
BR_FLAG = "🇧🇷"
CN_FLAG = "🇨🇳"
MX_FLAG = "🇲🇽"
DE_FLAG = "🇩🇪"


def test_emoji_to_country_basic():
    assert emoji_to_country(TR_FLAG) == "TR"
    assert emoji_to_country(GB_FLAG) == "GB"
    assert emoji_to_country(BR_FLAG) == "BR"
    assert emoji_to_country(CN_FLAG) == "CN"


def test_country_to_emoji_basic():
    assert country_to_emoji("TR") == TR_FLAG


def test_flag_to_language_chain():
    assert COUNTRY_TO_LANG[emoji_to_country(TR_FLAG)] == "TR"
    assert COUNTRY_TO_LANG[emoji_to_country(GB_FLAG)] == "EN-GB"
    assert COUNTRY_TO_LANG[emoji_to_country(BR_FLAG)] == "PT-BR"
    assert COUNTRY_TO_LANG[emoji_to_country(CN_FLAG)] == "ZH-HANS"


def test_roundtrip_over_whole_table():
    for cc in COUNTRY_TO_LANG:
        flag = country_to_emoji(cc)
        assert emoji_to_country(flag) == cc


def test_base_code():
    assert base_code("PT-BR") == "PT"
    assert base_code("ES-419") == "ES"
    assert base_code("ZH-HANT") == "ZH"
    assert base_code("ZH-HANS") == "ZH"
    assert base_code("TR") == "TR"


def test_parse_flags_ordered_and_deduplicated():
    assert parse_flags("hello 🇹🇷 x 🇩🇪🇹🇷") == ["🇹🇷", "🇩🇪"]


def test_parse_flags_ignores_non_flag_emoji():
    assert parse_flags("🌐 🇹🇷") == ["🇹🇷"]
    assert parse_flags("<:x:123> 🇹🇷") == ["🇹🇷"]


def test_parse_flags_empty_text():
    assert parse_flags("") == []


def test_emoji_to_country_rejects_non_flags():
    assert emoji_to_country("<:x:123>") is None
    assert emoji_to_country("🌐") is None
    assert emoji_to_country("🏴󠁧󠁢󠁥󠁮󠁧󠁿") is None  # tag-sequence flag (England), not 2 regional indicators
    assert emoji_to_country("a") is None
    assert emoji_to_country("") is None


def test_country_table_keys_and_values_shape():
    for cc, lang in COUNTRY_TO_LANG.items():
        assert isinstance(cc, str) and len(cc) == 2
        assert cc.isascii() and cc.isalpha() and cc.isupper()
        assert isinstance(lang, str) and lang != ""


def test_country_table_spot_checks():
    assert COUNTRY_TO_LANG["GB"] == "EN-GB"
    assert COUNTRY_TO_LANG["US"] == "EN-US"
    assert COUNTRY_TO_LANG["TR"] == "TR"
    assert COUNTRY_TO_LANG["MX"] == "ES-419"
    assert COUNTRY_TO_LANG["BR"] == "PT-BR"
    assert COUNTRY_TO_LANG["CN"] == "ZH-HANS"
    assert COUNTRY_TO_LANG["TW"] == "ZH-HANT"
    assert COUNTRY_TO_LANG["DE"] == "DE"
    assert COUNTRY_TO_LANG["JP"] == "JA"
    assert COUNTRY_TO_LANG["SA"] == "AR"


def test_lang_names_native():
    assert LANG_NAMES["EN"] == "English"
    assert LANG_NAMES["TR"] == "Türkçe"
    assert LANG_NAMES["AR"] == "العربية"
    assert LANG_NAMES["RU"] == "Русский"
    assert LANG_NAMES["ES"] == "Español"
    assert LANG_NAMES["ZH-HANS"] == "简体中文"
    assert LANG_NAMES["ZH-HANT"] == "繁體中文"
    assert LANG_NAMES["JA"] == "日本語"
    assert LANG_NAMES["KO"] == "한국어"


def test_lang_names_en():
    assert "TR" in LANG_NAMES_EN
    assert LANG_NAMES_EN["EN"] == "English"
    for name in LANG_NAMES_EN.values():
        assert isinstance(name, str) and name != ""


def test_preferred_flag():
    assert preferred_flag("EN") == GB_FLAG
    assert preferred_flag("PT") == BR_FLAG
    assert preferred_flag("ZH") == CN_FLAG
    assert preferred_flag("TR") == TR_FLAG
    assert preferred_flag("AR") == "🇸🇦"
    assert preferred_flag("JA") == "🇯🇵"


def test_resolver_without_targets_supports_everything():
    resolver = FlagResolver(None)
    resolved = resolver.resolve(TR_FLAG)
    assert resolved is not None
    assert resolved.code == "TR"
    assert resolved.flag
    assert resolver.resolve(MX_FLAG).code == "ES-419"
    assert resolver.resolve(CN_FLAG).code == "ZH-HANS"
    assert resolver.is_supported(TR_FLAG)
    assert resolver.disabled == []
    assert resolver.resolve("🌐") is None  # not a flag emoji at all


def test_resolver_falls_back_to_base_code():
    resolver = FlagResolver(["ES"])  # ES-419 not in list, base ES is
    resolved = resolver.resolve(MX_FLAG)
    assert resolved is not None
    assert resolved.code == "ES"
    assert resolver.is_supported(MX_FLAG)


def test_resolver_direct_target_supported():
    resolver = FlagResolver(["ES-419"])
    assert resolver.resolve(MX_FLAG).code == "ES-419"


def test_resolver_disables_flag_without_fallback():
    resolver = FlagResolver(["EN"])
    assert resolver.resolve(MX_FLAG) is None
    assert not resolver.is_supported(MX_FLAG)
    assert MX_FLAG in resolver.disabled


def test_resolver_unknown_emoji_not_disabled():
    resolver = FlagResolver(["EN"])
    assert resolver.resolve("🌐") is None
    assert resolver.resolve("<:x:123>") is None
    assert "🌐" not in resolver.disabled
    assert "<:x:123>" not in resolver.disabled


def test_resolved_lang_is_frozen_dataclass():
    resolved = ResolvedLang(code="TR", flag=TR_FLAG)
    assert resolved.code == "TR"
    assert resolved.flag == TR_FLAG
    assert dataclasses.is_dataclass(resolved)
    try:
        resolved.code = "EN"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("ResolvedLang must be frozen")


def test_variation_selector_stripped():
    """Emoji pickers often append U+FE0F; flags must still resolve."""
    from translatebot.flags import FlagResolver, emoji_to_country, parse_flags

    assert emoji_to_country("🇹🇷️") == "TR"
    assert emoji_to_country("🇬🇧️") == "GB"
    assert parse_flags("️🇬🇧️ x") == ["🇬🇧"]
    assert FlagResolver(None).resolve("🇬🇧️") is not None
