"""AoEM Translator entry point (SPEC sections 1, 4.10-4.13).

Usage:
    python bot.py             run the bot
    python bot.py --selftest  offline sanity checks, exit 0/1
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands
from discord.utils import oauth_url

from translatebot.engines import Engine, build_engine
from translatebot.flags import (
    COUNTRY_TO_LANG,
    LANG_NAMES,
    LANG_NAMES_EN,
    FlagResolver,
    country_to_emoji,
    emoji_to_country,
)
from translatebot.reactions import ReactionQueue
from translatebot.settings import MissingConfigError, Settings, load_settings
from translatebot.store import Store

log = logging.getLogger("translatebot.bot")

# SPEC section 3 permissions (no Administrator) minus Manage Nicknames,
# which only the removed /ign feature needed: Add Reactions, Send Messages,
# Send Messages in Threads, Read Message History, View Channel, Embed Links.
# NOTE: the old SPEC integer 274743774272 decodes to a much broader set
# (Manage Roles/Webhooks/Threads) — do not reuse it.
INVITE_PERMISSIONS = 274877992000
COGS = ("translate", "admin")


def _force_utf8_stdio() -> None:
    """Windows consoles default to a legacy codepage (cp1252); flags and
    Turkish text must survive print/log output, so force UTF-8 streams."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except Exception:  # pragma: no cover - non-reconfigurable stream
                pass


def build_lang_choices() -> list[tuple[str, str, str]]:
    """(code, native, english) triples for autocomplete, order-stable."""
    codes: list[str] = []
    for target in COUNTRY_TO_LANG.values():
        if target not in codes:
            codes.append(target)
    return [
        (code, LANG_NAMES.get(code, code), LANG_NAMES_EN.get(code, code)) for code in codes
    ]


class TranslatorBot(commands.Bot):
    """Bot wiring settings, store, engine, resolver and the reaction queue."""

    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.message_content = True  # privileged: required to read message text
        super().__init__(
            command_prefix=commands.when_mentioned, intents=intents, help_command=None
        )
        self.settings = settings
        self.store = Store(Path(settings.data_dir))
        self.store.load()
        self.engine: Engine | None = None  # built in setup_hook
        self.resolver: FlagResolver | None = None
        self.reactions = ReactionQueue(self.store)
        self.lang_choices = build_lang_choices()
        self._autosave_task: asyncio.Task | None = None

    async def setup_hook(self) -> None:
        self.engine = build_engine(self.settings)
        targets: list[str] | None = None
        try:
            targets = await self.engine.supported_targets()
        except Exception:
            log.exception(
                "Could not query engine target languages — treating all flags as supported"
            )
        self.resolver = FlagResolver(targets)
        # Resolve the whole flag table eagerly so the disabled list (and the
        # startup log counts) are accurate (SPEC 4.1 / 4.12).
        for cc in COUNTRY_TO_LANG:
            self.resolver.is_supported(country_to_emoji(cc))

        for cog in COGS:
            await self.load_extension(f"translatebot.cogs.{cog}")

        self._autosave_task = asyncio.create_task(self._autosave_loop())

        # One-time command sync (SPEC 4.10) — never in on_ready. A failed sync
        # must not crash the bot: log it and sync when the guild is joined.
        if self.settings.dev_guild_id is not None:
            guild = discord.Object(id=self.settings.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            try:
                synced = await self.tree.sync(guild=guild)
                log.info(
                    "Synced %d commands to dev guild %s (visible instantly).",
                    len(synced),
                    self.settings.dev_guild_id,
                )
            except Exception as exc:
                log.warning(
                    "Could not sync commands to dev guild %s yet (%s: %s). The bot will "
                    "sync automatically the moment it is added to that server.",
                    self.settings.dev_guild_id,
                    type(exc).__name__,
                    exc,
                )
        else:
            try:
                synced = await self.tree.sync()
                log.info(
                    "Synced %d global commands (Discord may take up to 1 hour to show them).",
                    len(synced),
                )
            except Exception as exc:
                log.error("Global command sync failed: %s: %s", type(exc).__name__, exc)

    async def _autosave_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(20)
                if self.store.dirty:
                    try:
                        self.store.save()
                        log.debug("Store autosaved.")
                    except Exception:
                        log.exception("Store autosave failed")
        except asyncio.CancelledError:
            pass

    async def on_ready(self) -> None:
        try:
            self._startup_log()
            await self._enforce_allowlist()
        except Exception:
            log.exception("on_ready handler failed")

    def _startup_log(self) -> None:
        all_flags = sorted({country_to_emoji(cc) for cc in COUNTRY_TO_LANG})
        disabled = self.resolver.disabled if self.resolver else []
        invite = oauth_url(
            self.user.id,
            permissions=discord.Permissions(INVITE_PERMISSIONS),
            scopes=("bot", "applications.commands"),
        )
        log.info("Logged in as %s (id %s)", self.user, getattr(self.user, "id", "?"))
        log.info("Connected guilds: %d", len(self.guilds))
        log.info(
            "Flags: %d active, %d disabled%s",
            len(all_flags) - len(disabled),
            len(disabled),
            (" (" + " ".join(disabled) + ")") if disabled else "",
        )
        log.info("Engine: %s", self.engine.name if self.engine else "?")
        log.info("Invite link: %s", invite)
        if self.settings.dev_guild_id is None:
            log.info(
                "DEV_GUILD_ID is not set — global command sync can take up to 1 hour to appear."
            )

    async def _enforce_allowlist(self) -> None:
        allowed = self.settings.allowed_guild_ids
        if not allowed:
            return
        for guild in list(self.guilds):
            if guild.id not in allowed:
                log.warning(
                    "Guild %s (%s) is not in ALLOWED_GUILD_IDS — leaving.",
                    guild.id,
                    guild.name,
                )
                try:
                    await guild.leave()
                except Exception:
                    log.exception("Failed to leave guild %s", guild.id)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        try:
            allowed = self.settings.allowed_guild_ids
            if allowed and guild.id not in allowed:
                log.warning(
                    "Joined non-allowed guild %s (%s) — leaving.", guild.id, guild.name
                )
                await guild.leave()
                return
        except Exception:
            log.exception("on_guild_join handler failed")
        # First join of the dev guild: run the guild sync that was deferred in
        # setup_hook because the bot was not a member yet (SPEC 4.10).
        if self.settings.dev_guild_id is not None and guild.id == self.settings.dev_guild_id:
            try:
                guild_obj = discord.Object(id=guild.id)
                self.tree.copy_global_to(guild=guild_obj)
                synced = await self.tree.sync(guild=guild_obj)
                log.info(
                    "Dev guild %s joined — synced %d commands instantly.",
                    guild.id,
                    len(synced),
                )
            except Exception:
                log.exception("Dev-guild sync after join failed")

    async def close(self) -> None:
        log.info("Shutting down: stopping reaction workers, saving store...")
        try:
            await self.reactions.close()
        except Exception:
            log.exception("Reaction queue shutdown failed")
        if self._autosave_task is not None:
            self._autosave_task.cancel()
            try:
                await self._autosave_task
            except asyncio.CancelledError:
                pass
        try:
            self.store.save()
            log.info("Store saved.")
        except Exception:
            log.exception("Final store save failed")
        await super().close()
        # Belt and braces for the NSSM service: guarantee the process exits so
        # "nssm stop/restart" can never hang waiting for it. Everything that
        # matters (the store) is already saved above.
        log.info("Shutdown complete.")
        os._exit(0)


def run_selftest() -> int:
    """Offline checks (SPEC 4.13). Returns 0 on success, 1 on any failure."""
    _force_utf8_stdio()
    print("AoEM Translator self-test")
    print("=" * 60)
    try:
        settings = load_settings(require_token=False, require_engine_keys=False)
    except MissingConfigError as exc:
        print(f"[FAIL] settings: {exc}")
        return 1
    print(
        f"[ok] settings loaded (engine={settings.engine}, data_dir={settings.data_dir}, "
        f"log_level={settings.log_level})"
    )

    for cc in COUNTRY_TO_LANG:
        if emoji_to_country(country_to_emoji(cc)) != cc:
            print(f"[FAIL] flag table roundtrip broken for {cc}")
            return 1
    print(f"[ok] flag table roundtrip verified for {len(COUNTRY_TO_LANG)} country codes")

    bot = TranslatorBot(settings)  # engine stays None; nothing connects anywhere

    async def _load() -> None:
        for cog in COGS:
            await bot.load_extension(f"translatebot.cogs.{cog}")

    try:
        asyncio.run(_load())
    except Exception as exc:
        print(f"[FAIL] cog loading: {exc}")
        return 1
    slash = sorted(
        c.name for c in bot.tree.get_commands(type=discord.AppCommandType.chat_input)
    )
    menus = sorted(
        c.name for c in bot.tree.get_commands(type=discord.AppCommandType.message)
    )
    print(f"[ok] slash commands ({len(slash)}): {', '.join(slash)}")
    if menus:
        print(f"[ok] context menus ({len(menus)}): {', '.join(menus)}")

    if settings.engine == "deepl" and settings.deepl_api_key:
        try:
            engine = build_engine(settings)
        except Exception as exc:
            print(f"[FAIL] engine: {exc}")
            return 1
        try:
            targets = asyncio.run(engine.supported_targets())
        except Exception as exc:
            print(f"[FAIL] DeepL supported_targets: {exc}")
            return 1
        resolver = FlagResolver(targets)
        all_flags = sorted({country_to_emoji(cc) for cc in COUNTRY_TO_LANG})
        disabled = [f for f in all_flags if not resolver.is_supported(f)]
        print(
            f"[ok] DeepL reachable: {len(targets)} target languages, "
            f"{len(all_flags) - len(disabled)}/{len(all_flags)} flags active"
        )
        if disabled:
            print(f"[warn] disabled flags: {' '.join(disabled)}")
    else:
        if settings.engine != "deepl":
            print("[skip] engine target check skipped (ENGINE=claude — all flags supported)")
        else:
            print("[skip] DEEPL_API_KEY not set — engine target check skipped")

    print("Self-test PASSED.")
    return 0


def main() -> None:
    _force_utf8_stdio()
    parser = argparse.ArgumentParser(description="AoEM Translator Discord bot")
    parser.add_argument(
        "--selftest", action="store_true", help="run offline checks and exit"
    )
    args = parser.parse_args()
    if args.selftest:
        sys.exit(run_selftest())

    try:
        settings = load_settings()
    except MissingConfigError as exc:
        print(f"Configuration error:\n{exc}", file=sys.stderr)
        sys.exit(1)

    discord.utils.setup_logging(
        level=getattr(logging, settings.log_level, logging.INFO), root=True
    )
    bot = TranslatorBot(settings)
    try:
        bot.run(settings.discord_token, log_handler=None)
    except discord.LoginFailure:
        print(
            "Discord rejected the token — check DISCORD_TOKEN in .env.", file=sys.stderr
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
