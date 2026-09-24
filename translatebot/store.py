"""JSON persistence for guild settings, user languages, IGNs and stats (SPEC 4.9)."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, fields
from pathlib import Path

log = logging.getLogger("translatebot.store")

# Default auto-flag list (SPEC 4.2 + user request: CN/KR/PH/JP added for
# Chinese, Korean, Tagalog and Japanese coverage).
DEFAULT_FLAGS: list[str] = [
    "🇬🇧", "🇹🇷", "🇸🇦", "🇷🇺", "🇪🇸", "🇧🇷", "🇩🇪", "🇫🇷", "🇻🇳", "🇮🇩",
    "🇨🇳", "🇰🇷", "🇵🇭", "🇯🇵",
]
DEFAULT_IGN_FORMAT = "{ign} | {name}"


@dataclass
class GuildSettings:
    """Per-guild configuration; missing JSON fields fall back to defaults."""

    auto_channels: list[int] = field(default_factory=list)
    flags: list[str] = field(default_factory=lambda: list(DEFAULT_FLAGS))
    globe: bool = True
    mode: str = "reply"  # "reply" | "dm"
    delete_after: int = 0
    min_chars: int = 5
    skip_source: bool = True
    ign_format: str = DEFAULT_IGN_FORMAT
    max_lag: int = 45

    def to_dict(self) -> dict:
        return {
            "auto_channels": list(self.auto_channels),
            "flags": list(self.flags),
            "globe": self.globe,
            "mode": self.mode,
            "delete_after": self.delete_after,
            "min_chars": self.min_chars,
            "skip_source": self.skip_source,
            "ign_format": self.ign_format,
            "max_lag": self.max_lag,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "GuildSettings":
        known = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in (data or {}).items() if k in known}
        gs = cls(**kwargs)
        gs.auto_channels = [int(c) for c in gs.auto_channels]
        gs.flags = [str(f) for f in gs.flags]
        return gs


def _empty_stats() -> dict:
    return {"detected": {}, "clicks": {}, "translations": 0, "chars": 0, "skipped_stale": 0}


class Store:
    """data/store.json holder. Writes are atomic; autosave is driven by bot.py."""

    def __init__(self, data_dir: Path) -> None:
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "store.json"
        self.guilds: dict[str, GuildSettings] = {}
        self.users: dict[str, dict] = {}
        self.igns: dict[str, dict[str, str]] = {}
        self.stats_data: dict[str, dict] = {}
        self.dirty = False

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("store.json must contain a JSON object")
            self.guilds = {
                str(k): GuildSettings.from_dict(v) for k, v in raw.get("guilds", {}).items()
            }
            self.users = {str(k): dict(v) for k, v in raw.get("users", {}).items()}
            self.igns = {
                str(g): {str(u): str(n) for u, n in users.items()}
                for g, users in raw.get("igns", {}).items()
            }
            self.stats_data = {
                str(g): {**_empty_stats(), **v} for g, v in raw.get("stats", {}).items()
            }
            self.dirty = False
        except (json.JSONDecodeError, AttributeError, OSError, TypeError, ValueError) as exc:
            backup = self._path.with_name(self._path.name + ".bak")
            try:
                os.replace(self._path, backup)
                log.error("store.json was corrupt (%s); moved to %s and starting fresh", exc, backup)
            except OSError:
                log.error("store.json was corrupt (%s); backup failed, starting fresh", exc)
            self.guilds, self.users, self.igns, self.stats_data = {}, {}, {}, {}
            self.dirty = False

    def save(self) -> None:
        payload = {
            "guilds": {k: gs.to_dict() for k, gs in self.guilds.items()},
            "users": self.users,
            "igns": self.igns,
            "stats": self.stats_data,
        }
        tmp = self._path.with_name(self._path.name + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self._path)
        self.dirty = False

    # ---- guild settings ----

    def guild(self, gid: int) -> GuildSettings:
        key = str(gid)
        gs = self.guilds.get(key)
        if gs is None:
            gs = GuildSettings()
            self.guilds[key] = gs
            self.dirty = True
        return gs

    # ---- user languages ----

    def user_lang(self, uid: int) -> str | None:
        entry = self.users.get(str(uid))
        return entry.get("lang") if entry else None

    def set_user_lang(self, uid: int, code: str) -> None:
        self.users[str(uid)] = {"lang": code}
        self.dirty = True

    # ---- IGNs ----

    def ign_get(self, gid: int, uid: int) -> str | None:
        return self.igns.get(str(gid), {}).get(str(uid))

    def ign_set(self, gid: int, uid: int, nick: str) -> None:
        self.igns.setdefault(str(gid), {})[str(uid)] = nick
        self.dirty = True

    def ign_remove(self, gid: int, uid: int) -> bool:
        bucket = self.igns.get(str(gid))
        if bucket and str(uid) in bucket:
            del bucket[str(uid)]
            self.dirty = True
            return True
        return False

    # ---- stats ----

    def stats(self, gid: int) -> dict:
        key = str(gid)
        st = self.stats_data.get(key)
        if st is None:
            st = _empty_stats()
            self.stats_data[key] = st
            self.dirty = True
        return st

    def mark_dirty(self) -> None:
        self.dirty = True
