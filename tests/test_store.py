"""Tests for translatebot.store (SPEC 4.9)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translatebot.store import (
    DEFAULT_FLAGS,
    DEFAULT_IGN_FORMAT,
    GuildSettings,
    Store,
)


def make_store(tmp_path):
    store = Store(tmp_path)
    store.load()
    return store


def test_default_constants():
    assert DEFAULT_FLAGS == ["🇬🇧", "🇹🇷", "🇸🇦", "🇷🇺", "🇪🇸", "🇧🇷", "🇩🇪", "🇫🇷", "🇻🇳", "🇮🇩", "🇨🇳", "🇰🇷", "🇵🇭", "🇯🇵"]
    assert DEFAULT_IGN_FORMAT == "{ign} | {name}"


def test_fresh_store_gives_defaults(tmp_path):
    store = make_store(tmp_path)
    assert store.path == tmp_path / "store.json"
    g = store.guild(123)
    assert g.auto_channels == []
    assert g.flags == DEFAULT_FLAGS
    assert g.globe is True
    assert g.mode == "reply"
    assert g.delete_after == 0
    assert g.min_chars == 5
    assert g.skip_source is True
    assert g.ign_format == DEFAULT_IGN_FORMAT
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
    g.mode = "dm"
    g.delete_after = 30
    g.min_chars = 3
    g.skip_source = False
    g.ign_format = "{ign} :: {name}"
    g.max_lag = 90
    store.set_user_lang(7, "TR")
    store.ign_set(1000, 7, "ProPlayer")
    store.save()

    store2 = make_store(tmp_path)
    g2 = store2.guild(1000)
    assert g2.auto_channels == [11, 22, 33]
    assert g2.flags == ["🇹🇷", "🇩🇪"]
    assert g2.globe is False
    assert g2.mode == "dm"
    assert g2.delete_after == 30
    assert g2.min_chars == 3
    assert g2.skip_source is False
    assert g2.ign_format == "{ign} :: {name}"
    assert g2.max_lag == 90
    assert store2.user_lang(7) == "TR"
    assert store2.ign_get(1000, 7) == "ProPlayer"


def test_load_fills_missing_guild_fields_with_defaults(tmp_path):
    store = make_store(tmp_path)
    g = store.guild(5)
    g.mode = "dm"
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
    assert g2.mode == "dm"      # saved values are kept
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


def test_ign_set_get_remove(tmp_path):
    store = make_store(tmp_path)
    assert store.ign_get(1, 10) is None
    store.ign_set(1, 10, "Warrior")
    assert store.ign_get(1, 10) == "Warrior"
    store.ign_set(1, 10, "Paladin")  # overwrite
    assert store.ign_get(1, 10) == "Paladin"
    store.ign_set(1, 11, "Mage")
    assert store.ign_get(1, 11) == "Mage"
    assert store.ign_remove(1, 10) is True
    assert store.ign_get(1, 10) is None
    assert store.ign_remove(1, 10) is False


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
    store.ign_set(gid, 99, "Nick")
    store.save()

    raw = json.loads((tmp_path / "store.json").read_text(encoding="utf-8"))
    assert "123456789012345678" in raw["guilds"]
    assert raw["users"]["42"]["lang"] == "TR"
    assert raw["igns"]["123456789012345678"]["99"] == "Nick"

    store2 = make_store(tmp_path)
    assert store2.user_lang(42) == "TR"
    assert store2.ign_get(gid, 99) == "Nick"


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
    assert d["mode"] == "reply"
    assert d["globe"] is True

    g2 = GuildSettings.from_dict({})  # missing keys -> defaults
    assert g2.flags == DEFAULT_FLAGS
    assert g2.mode == "reply"

    g3 = GuildSettings.from_dict({"mode": "dm", "totally_unknown": 123})  # unknown keys ignored
    assert g3.mode == "dm"
    assert g3.globe is True
    assert g3.min_chars == 5


def test_save_leaves_no_temp_files(tmp_path):
    store = make_store(tmp_path)
    store.guild(1)
    store.save()
    assert (tmp_path / "store.json").is_file()
    leftovers = sorted(p.name for p in tmp_path.iterdir() if p.name != "store.json")
    assert leftovers == []  # atomic save: temp file consumed by os.replace
