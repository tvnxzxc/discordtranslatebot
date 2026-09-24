"""Tests for translatebot.store (SPEC 4.9)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translatebot.store import (
    DEFAULT_FLAGS,
    GuildSettings,
    Store,
)


def make_store(tmp_path):
    store = Store(tmp_path)
    store.load()
    return store


def test_default_constants():
    assert DEFAULT_FLAGS == ["🇬🇧", "🇹🇷", "🇸🇦", "🇷🇺", "🇪🇸", "🇧🇷", "🇩🇪", "🇫🇷", "🇻🇳", "🇮🇩", "🇨🇳", "🇰🇷", "🇵🇭", "🇯🇵"]


def test_fresh_store_gives_defaults(tmp_path):
    store = make_store(tmp_path)
    assert store.path == tmp_path / "store.json"
    g = store.guild(123)
    assert g.auto_channels == []
    assert g.flags == DEFAULT_FLAGS
    assert g.globe is True
    assert g.delete_after == 0
    assert g.min_chars == 5
    assert g.skip_source is True
    assert g.max_lag == 45


def test_guild_flags_default_is_a_copy(tmp_path):
    store = make_store(tmp_path)
    g1 = store.guild(1)
    g1.flags.append("🇲🇽")
    g2 = store.guild(2)
    assert g2.flags == DEFAULT_FLAGS
    assert "🇲🇽" not in DEFAULT_FLAGS


def test_guild_marks_store_dirty(tmp_path):
    store = make_store(tmp_path)
    assert store.guild(1) is not None
    assert store.dirty


def test_save_load_roundtrip(tmp_path):
    store = make_store(tmp_path)
    g = store.guild(1000)
    g.auto_channels = [11, 22, 33]
    g.flags = ["🇹🇷", "🇩🇪"]
    g.globe = False
    g.delete_after = 30
    g.min_chars = 3
    g.skip_source = False
    g.max_lag = 90
    store.set_user_lang(7, "TR")
    store.save()

    store2 = make_store(tmp_path)
    g2 = store2.guild(1000)
    assert g2.auto_channels == [11, 22, 33]
    assert g2.flags == ["🇹🇷", "🇩🇪"]
    assert g2.globe is False
    assert g2.delete_after == 30
    assert g2.min_chars == 3
    assert g2.skip_source is False
    assert g2.max_lag == 90
    assert store2.user_lang(7) == "TR"


def test_load_fills_missing_guild_fields_with_defaults(tmp_path):
    store = make_store(tmp_path)
    g = store.guild(5)
    g.min_chars = 9
    store.save()

    path = tmp_path / "store.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    del raw["guilds"]["5"]["globe"]
    del raw["guilds"]["5"]["flags"]
    path.write_text(json.dumps(raw), encoding="utf-8")

    store2 = make_store(tmp_path)
    g2 = store2.guild(5)
    assert g2.globe is True
    assert g2.flags == DEFAULT_FLAGS
    assert g2.min_chars == 9


def test_corrupt_json_recovers_with_bak(tmp_path):
    (tmp_path / "store.json").write_text("not json{{{", encoding="utf-8")
    store = Store(tmp_path)
    store.load()  # must not raise
    assert (tmp_path / "store.json.bak").exists()
    g = store.guild(77)
    assert g.flags == DEFAULT_FLAGS
    store.save()  # store usable afterwards
    raw = json.loads((tmp_path / "store.json").read_text(encoding="utf-8"))
    assert raw["guilds"]["77"]


def test_user_lang_set_get(tmp_path):
    store = make_store(tmp_path)
    assert store.user_lang(42) is None
    store.set_user_lang(42, "TR")
    assert store.user_lang(42) == "TR"
    store.set_user_lang(42, "EN")  # update
    assert store.user_lang(42) == "EN"


def test_int_ids_use_string_keys_in_json(tmp_path):
    store = make_store(tmp_path)
    gid = 123456789012345678
    store.guild(gid)
    store.set_user_lang(42, "TR")
    store.save()

    raw = json.loads((tmp_path / "store.json").read_text(encoding="utf-8"))
    assert "123456789012345678" in raw["guilds"]
    assert raw["users"]["42"]["lang"] == "TR"

    store2 = make_store(tmp_path)
    assert store2.user_lang(42) == "TR"


def test_stats_creates_zeroed_structure(tmp_path):
    store = make_store(tmp_path)
    st = store.stats(3)
    assert st == {
        "detected": {},
        "clicks": {},
        "translations": 0,
        "chars": 0,
        "skipped_stale": 0,
    }
    st["translations"] += 1
    st["detected"]["en"] = 2
    st["clicks"]["🇹🇷"] = 1
    assert store.stats(3)["translations"] == 1
    store.save()
    store2 = make_store(tmp_path)
    assert store2.stats(3)["detected"] == {"en": 2}


def test_guild_settings_to_and_from_dict():
    g = GuildSettings()
    d = g.to_dict()
    assert d["globe"] is True

    g2 = GuildSettings.from_dict({})  # missing keys -> defaults
    assert g2.flags == DEFAULT_FLAGS

    # Removed features ("mode", "ign_format") load as unknown keys and are ignored.
    g3 = GuildSettings.from_dict(
        {"mode": "dm", "ign_format": "{ign} :: {name}", "totally_unknown": 123}
    )
    assert g3.globe is True
    assert g3.min_chars == 5


def test_legacy_mode_and_igns_keys_are_dropped(tmp_path):
    raw = {
        "guilds": {"5": {"mode": "dm", "ign_format": "{ign} :: {name}", "min_chars": 9}},
        "users": {},
        "igns": {"5": {"42": "Nick"}},
        "stats": {},
    }
    (tmp_path / "store.json").write_text(json.dumps(raw), encoding="utf-8")
    store = make_store(tmp_path)
    assert store.guild(5).min_chars == 9  # known fields still load
    store.save()
    saved = json.loads((tmp_path / "store.json").read_text(encoding="utf-8"))
    assert "igns" not in saved
    assert "mode" not in saved["guilds"]["5"]
    assert "ign_format" not in saved["guilds"]["5"]


def test_save_leaves_no_temp_files(tmp_path):
    store = make_store(tmp_path)
    store.guild(1)
    store.save()
    assert (tmp_path / "store.json").is_file()
    leftovers = sorted(p.name for p in tmp_path.iterdir() if p.name != "store.json")
    assert leftovers == []  # atomic save: temp file consumed by os.replace
