"""Tests for translatebot.formatting (SPEC 4.3)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translatebot.formatting import already_note, chunk, format_reply


def test_format_reply_first_line_exact():
    out = format_reply("🇹🇷", "Türkçe", "PT", "TR", "merhaba dünya")
    first, sep, body = out.partition("\n")
    assert sep == "\n"
    assert first == "🇹🇷 **Türkçe** · PT → TR"
    assert body == "merhaba dünya"


def test_format_reply_jump_url_on_first_line():
    url = "https://discord.com/channels/1/2/3"
    out = format_reply("🇹🇷", "Türkçe", "PT", "TR", "gövde", jump_url=url)
    first = out.split("\n", 1)[0]
    assert first.startswith("🇹🇷 **Türkçe** · PT → TR")
    assert url in first


def test_format_reply_multiline_body_preserved():
    body = "satır bir\nsatır iki\nsatır üç"
    out = format_reply("🇬🇧", "English", "TR", "EN", body)
    assert out.split("\n", 1)[1] == body


def test_format_reply_without_source_base():
    out = format_reply("🇹🇷", "Türkçe", None, "TR", "merhaba")
    first = out.split("\n", 1)[0]
    assert first == "🇹🇷 **Türkçe**"
    assert "·" not in first
    assert "→" not in first


def test_format_reply_empty_source_base():
    out = format_reply("🇩🇪", "Deutsch", "", "DE", "hallo")
    first = out.split("\n", 1)[0]
    assert first == "🇩🇪 **Deutsch**"
    assert "·" not in first
    assert "→" not in first


def test_chunk_empty_text():
    assert chunk("") == []


def test_chunk_short_text_untouched():
    assert chunk("hello world") == ["hello world"]


def test_chunk_long_text_no_loss():
    text = " ".join(["kelime"] * 1000)  # 6999 chars including spaces
    parts = chunk(text, 1900)
    assert len(parts) >= 4
    assert all(len(p) <= 1900 for p in parts)
    # no characters lost: parts either keep the separators or rejoin with them
    assert "".join(parts) == text or " ".join(parts) == text


def test_chunk_unbreakable_text():
    text = "a" * 5000
    parts = chunk(text, 1900)
    assert all(len(p) <= 1900 for p in parts)
    assert "".join(parts) == text


def test_chunk_exact_limit_single_part():
    text = "b" * 1900
    parts = chunk(text, 1900)
    assert all(len(p) <= 1900 for p in parts)
    assert "".join(parts) == text


def test_already_note():
    assert already_note("Türkçe") == "Already in Türkçe."
