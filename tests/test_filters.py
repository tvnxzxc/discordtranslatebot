"""Tests for translatebot.filters.qualifies (SPEC 4.2)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translatebot.filters import qualifies


def test_empty_message_false():
    assert not qualifies("")


def test_short_message_false():
    assert not qualifies("hey")
    assert not qualifies("ok!")


def test_normal_sentence_true():
    assert qualifies("hello world, how are you today?")
    assert qualifies("good morning everyone")


def test_only_unicode_emoji_false():
    assert not qualifies("🎉🎉🎉🎉🎉")
    assert not qualifies("😀 😀 😀 😀 😀")


def test_only_custom_emoji_false():
    assert not qualifies("<:fire:123456789012345678> <:fire:123456789012345678>")


def test_only_url_false():
    assert not qualifies("https://example.com")
    assert not qualifies("http://example.com/a/very/long/path?with=query&and=more")


def test_only_mentions_false():
    assert not qualifies("<@123456789012345678>")
    assert not qualifies("<@!123456789012345678> <@&987654321098765432> <#555666777888999000>")


def test_bot_prefix_commands_false():
    assert not qualifies("!rank")
    assert not qualifies(".help")
    assert not qualifies("?q")
    assert not qualifies("$bet")
    assert not qualifies("-afk")


def test_prefix_rule_on_long_text():
    assert not qualifies("!rank top players of the week")
    assert not qualifies(".help me with role setup please")
    assert not qualifies("?what is this channel for anyway")
    assert not qualifies("$bet five hundred chips on red")
    assert not qualifies("-afk gone to lunch back soon")


def test_min_chars_boundary_default_is_5():
    assert qualifies("abcde")           # exactly 5 -> True
    assert not qualifies("abcd")        # 4 < 5 -> False
    assert qualifies("abcd", 4)
    assert qualifies("abcd", min_chars=4)
    assert not qualifies("abc", min_chars=4)


def test_min_chars_counts_after_stripping():
    # mention is stripped, so only "abcd" / "abcde" remain
    assert not qualifies("<@123456789012345678> abcd")
    assert qualifies("<@123456789012345678> abcde")


def test_digits_only_false():
    assert not qualifies("123456")
    assert not qualifies("12345", 5)  # exactly min_chars but no alphabetic char


def test_url_plus_real_text_true():
    assert qualifies("check this out https://example.com/path right now")
    assert qualifies("https://example.com hello there friends")


def test_mention_plus_real_text_true():
    assert qualifies("<@123456789012345678> hello there friends")


def test_bot_messages_never_qualify():
    """SPEC 5: bot messages never qualify (bot gate exposed as from_bot keyword)."""
    assert qualifies("a perfectly normal sentence", min_chars=5, from_bot=True) is False
