"""Member-facing features (SPEC 4.2-4.6): auto flags, reaction translation,
/translate, /mylang, /help and the "Translate to my language" context menu."""

import asyncio
import logging
import time
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from translatebot.detect import detect_lang, detection_base
from translatebot.dedupe import TTLCache
from translatebot.engines.base import (
    QuotaExceededError,
    TooManyRequestsError,
    TranslationError,
)
from translatebot.filters import qualifies
from translatebot.flags import GLOBE, LANG_NAMES, LANG_NAMES_EN, base_code, preferred_flag
from translatebot.formatting import already_note, chunk, format_reply

if TYPE_CHECKING:
    from bot import TranslatorBot

log = logging.getLogger("translatebot.translate")

_AUTO_TYPES = (discord.MessageType.default, discord.MessageType.reply)
_CHUNK_LIMIT = 1900

# Languages shown in the click-to-pick menu of bare /mylang (most common first).
FEATURED_LANGUAGES = [
    "EN-GB", "TR", "AR", "RU", "ES", "PT-BR", "DE", "FR", "VI", "ID",
    "ZH-HANS", "KO", "TL", "JA", "IT", "NL", "PL", "UK", "EL", "SV",
    "ZH-HANT", "TH", "HI", "PT-PT", "EN-US",
]


class LanguageSelect(discord.ui.Select):
    """Dropdown for bare /mylang: pick a language without typing."""

    def __init__(self, cog: "TranslateCog", current: str | None) -> None:
        self._cog = cog
        options: list[discord.SelectOption] = []
        for code in FEATURED_LANGUAGES:
            native = LANG_NAMES.get(code, code)
            english = LANG_NAMES_EN.get(code, code)
            options.append(
                discord.SelectOption(
                    label=f"{preferred_flag(code)} {native}"[:100],
                    value=code,
                    description=f"{code} · {english}"[:100],
                    default=(code == current),
                )
            )
        super().__init__(
            placeholder="Pick your language…",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        code = self.values[0]
        self._cog.bot.store.set_user_lang(interaction.user.id, code)
        await interaction.response.edit_message(
            content=(
                f"✅ Personal language set to {preferred_flag(code)} "
                f"**{self._cog._display(code)}** (`{code}`). "
                "Click 🌐 under any message to use it."
            ),
            view=None,
        )


class LanguageSelectView(discord.ui.View):
    def __init__(self, cog: "TranslateCog", current: str | None) -> None:
        super().__init__(timeout=300)
        self.add_item(LanguageSelect(cog, current))


async def language_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    """Up to 25 language choices filtered by code, native or English name."""
    client = interaction.client
    choices: list[app_commands.Choice[str]] = []
    needle = (current or "").strip().lower()
    for code, native, english in getattr(client, "lang_choices", []):
        if needle and needle not in code.lower() and needle not in native.lower() and needle not in english.lower():
            continue
        label = f"{preferred_flag(code)} {code} · {native} ({english})"[:100]
        choices.append(app_commands.Choice(name=label, value=code))
        if len(choices) >= 25:
            break
    return choices


class TranslateCog(commands.Cog):
    """Auto-flagging, reaction translation and member commands."""

    def __init__(self, bot: "TranslatorBot") -> None:
        self.bot = bot
        # Dedupe keys: (message_id, target) for flags, (message_id, target, user_id) for 🌐.
        self.dedupe = TTLCache(ttl=3600.0, maxsize=5000)
        self._perm_warned: dict[int, float] = {}
        self._empty_content_warned = False
        self.ctx_menu = app_commands.ContextMenu(
            name="Translate to my language", callback=self._ctx_translate
        )

    async def cog_load(self) -> None:
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    # ------------------------------------------------------------------
    # Auto flags (SPEC 4.2)
    # ------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        try:
            await self._auto_flags(message)
        except Exception:
            log.exception("on_message handler failed")

    async def _auto_flags(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot or message.webhook_id:
            return
        if message.type not in _AUTO_TYPES:
            return
        guild_settings = self.bot.store.guild(message.guild.id)
        channel = message.channel
        channel_id = channel.parent_id if isinstance(channel, discord.Thread) and channel.parent_id else channel.id
        if channel_id not in guild_settings.auto_channels:
            return
        if not (message.content or "").strip():
            return
        if not qualifies(message.content, guild_settings.min_chars):
            return
        me = message.guild.me
        if me is None:
            return
        if not channel.permissions_for(me).add_reactions:
            self._warn_missing_reactions(channel_id)
            return
        assert self.bot.resolver is not None
        flags: list[str] = []
        for flag in guild_settings.flags:
            resolved = self.bot.resolver.resolve(flag)
            if resolved is not None:
                flags.append(resolved.flag)
        if guild_settings.skip_source:
            detected = await asyncio.to_thread(detect_lang, message.content)
            base = detection_base(detected)
            if base:
                stats = self.bot.store.stats(message.guild.id)
                stats["detected"][base] = stats["detected"].get(base, 0) + 1
                self.bot.store.mark_dirty()
                kept: list[str] = []
                for flag in flags:
                    resolved = self.bot.resolver.resolve(flag)
                    if resolved is not None and base_code(resolved.code) != base:
                        kept.append(flag)
                flags = kept
        emojis: list[str] = []
        if guild_settings.globe:
            emojis.append(GLOBE)
        emojis.extend(flag for flag in flags if flag not in emojis)
        if not emojis:
            return
        self.bot.reactions.enqueue(message, emojis, max_lag=guild_settings.max_lag)

    def _warn_missing_reactions(self, channel_id: int) -> None:
        now = time.monotonic()
        if now - self._perm_warned.get(channel_id, 0.0) < 600.0:
            return
        self._perm_warned[channel_id] = now
        log.warning(
            "I lack Add Reactions permission in channel %s — auto flags skipped there "
            "(warned once per 10 minutes).",
            channel_id,
        )

    # ------------------------------------------------------------------
    # Reaction translation (SPEC 4.3, 4.4)
    # ------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        try:
            await self._on_reaction(payload)
        except Exception:
            log.exception("on_raw_reaction_add handler failed")

    async def _on_reaction(self, payload: discord.RawReactionActionEvent) -> None:
        if self.bot.user is not None and payload.user_id == self.bot.user.id:
            return
        if payload.guild_id is None:
            return
        member = payload.member
        if member is not None and member.bot:
            return
        emoji = payload.emoji
        if not emoji.is_unicode_emoji():
            return
        name = emoji.name or ""
        if name == GLOBE:
            await self._globe(payload)
            return
        assert self.bot.resolver is not None
        resolved = self.bot.resolver.resolve(name)
        if resolved is None:
            return  # unknown or engine-unsupported flag: silently ignore
        if not self.dedupe.check_and_add((payload.message_id, resolved.code)):
            return
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        member = member or guild.get_member(payload.user_id)
        if member is not None and member.bot:
            return  # bots never trigger translations
        fetched = await self._fetch(payload.channel_id, payload.message_id)
        if fetched is None:
            return
        _channel, message = fetched
        text = self._extract_text(message)
        if text is None:
            await self._warn_empty_content(message)
            return
        await self._flag_translation(message, resolved, text, name)

    async def _flag_translation(
        self,
        message: discord.Message,
        resolved,
        text: str,
        emoji: str,
    ) -> None:
        guild_settings = self.bot.store.guild(message.guild.id)
        try:
            result = await self._translate(text, resolved.code)
        except QuotaExceededError:
            await self._note(message, "⚠️ Monthly translation quota exceeded.", 20)
            log.error("DeepL monthly quota exceeded (guild %s).", message.guild.id)
            return
        except TooManyRequestsError as exc:
            await self._note(message, "⚠️ Translation failed, try again later.", 15)
            log.warning(
                "Translation rate limited twice for message %s.", message.id, exc_info=exc
            )
            return
        except TranslationError as exc:
            await self._note(message, "⚠️ Translation failed, try again later.", 15)
            log.error("Translation failed for message %s: %s", message.id, exc, exc_info=exc)
            return
        display = self._display(resolved.code)
        if result.source and base_code(result.source) == base_code(resolved.code):
            await self._note(message, already_note(display), 10)
            return
        delete_after = float(guild_settings.delete_after) if guild_settings.delete_after else None
        first, rest = self._header_and_rest(resolved.flag, display, result, resolved.code)
        try:
            await message.reply(
                first,
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
                delete_after=delete_after,
            )
            for part in rest:
                await message.channel.send(
                    part,
                    allowed_mentions=discord.AllowedMentions.none(),
                    delete_after=delete_after,
                )
        except discord.Forbidden:
            log.warning("Missing Send Messages permission in channel %s.", message.channel.id)
            return
        except discord.HTTPException as exc:
            log.warning("Failed to send translation for message %s: %s", message.id, exc)
            return
        stats = self.bot.store.stats(message.guild.id)
        stats["clicks"][emoji] = stats["clicks"].get(emoji, 0) + 1
        stats["translations"] += 1
        stats["chars"] += len(text)
        self.bot.store.mark_dirty()

    async def _globe(self, payload: discord.RawReactionActionEvent) -> None:
        user_id = payload.user_id
        target = self.bot.store.user_lang(user_id)
        guild = self.bot.get_guild(payload.guild_id)
        member = payload.member or (guild.get_member(user_id) if guild else None)
        if member is not None and member.bot:
            return
        fetched = await self._fetch(payload.channel_id, payload.message_id)
        if fetched is None:
            return
        _channel, message = fetched
        if not target:
            await self._note(message, "Set your language first with `/mylang`.", 15)
            return
        if not self.dedupe.check_and_add((payload.message_id, target, user_id)):
            return
        text = self._extract_text(message)
        if text is None:
            await self._warn_empty_content(message)
            return
        try:
            result = await self._translate(text, target)
        except QuotaExceededError:
            await self._note(message, "⚠️ Monthly translation quota exceeded.", 20)
            log.error("DeepL monthly quota exceeded (guild %s).", payload.guild_id)
            return
        except TooManyRequestsError as exc:
            await self._note(message, "⚠️ Translation failed, try again later.", 15)
            log.warning(
                "Rate limited twice on globe translation of message %s.",
                message.id,
                exc_info=exc,
            )
            return
        except TranslationError as exc:
            await self._note(message, "⚠️ Translation failed, try again later.", 15)
            log.error("Globe translation failed for message %s: %s", message.id, exc, exc_info=exc)
            return
        display = self._display(target)
        if result.source and base_code(result.source) == base_code(target):
            await self._note(message, already_note(display), 10)
            return
        # The globe always answers publicly under the message (user request):
        # no DMs are ever sent for 🌐.
        guild_settings = self.bot.store.guild(payload.guild_id)
        delete_after = float(guild_settings.delete_after) if guild_settings.delete_after else None
        first, rest = self._header_and_rest(preferred_flag(target), display, result, target)
        try:
            await message.reply(
                first,
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
                delete_after=delete_after,
            )
            for part in rest:
                await message.channel.send(
                    part, allowed_mentions=discord.AllowedMentions.none(), delete_after=delete_after
                )
        except discord.Forbidden:
            log.warning("Missing Send Messages permission in channel %s.", message.channel.id)
            return
        except discord.HTTPException as exc:
            log.warning("Failed to send globe translation: %s", exc)
            return
        stats = self.bot.store.stats(payload.guild_id)
        stats["clicks"][GLOBE] = stats["clicks"].get(GLOBE, 0) + 1
        stats["translations"] += 1
        stats["chars"] += len(text)
        self.bot.store.mark_dirty()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _translate(self, text: str, target: str):
        try:
            return await self.bot.engine.translate(text, target)
        except TooManyRequestsError:
            await asyncio.sleep(2)
            return await self.bot.engine.translate(text, target)

    async def _fetch(self, channel_id: int, message_id: int):
        try:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                channel = await self.bot.fetch_channel(channel_id)
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            log.debug("Channel/message %s/%s not found (deleted?).", channel_id, message_id)
            return None
        except discord.Forbidden:
            log.warning("Missing access to channel %s.", channel_id)
            return None
        return channel, message

    @staticmethod
    def _extract_text(message: discord.Message) -> str | None:
        if message.content and message.content.strip():
            return message.content
        for embed in message.embeds:
            joined = "\n".join(p for p in (embed.title, embed.description) if p).strip()
            if joined:
                return joined
        return None

    async def _warn_empty_content(self, message: discord.Message) -> None:
        if self._empty_content_warned:
            return
        if message.content or message.embeds or message.attachments:
            return
        self._empty_content_warned = True
        log.warning(
            "Message %s has no readable content — Message Content Intent may be disabled "
            "in the Developer Portal (Bot -> Privileged Gateway Intents).",
            message.id,
        )

    async def _note(self, message: discord.Message, text: str, delete_after: float) -> None:
        try:
            await message.reply(
                text,
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
                delete_after=delete_after,
            )
        except discord.HTTPException as exc:
            log.debug("Could not deliver note for message %s: %s", message.id, exc)

    def _header_and_rest(self, flag: str, display: str, result, code: str):
        source_base = base_code(result.source) if result.source else None
        parts = chunk(result.text, _CHUNK_LIMIT)
        first = format_reply(flag, display, source_base, code, parts[0] if parts else "")
        return first, parts[1:]

    def _display(self, code: str) -> str:
        return LANG_NAMES.get(code) or LANG_NAMES_EN.get(code) or code

    # ------------------------------------------------------------------
    # Slash commands (SPEC 4.4-4.6)
    # ------------------------------------------------------------------

    @app_commands.command(name="translate", description="Translate a text into another language")
    @app_commands.describe(text="Text to translate (up to 2000 characters)", to="Target language")
    @app_commands.autocomplete(to=language_autocomplete)
    async def translate_command(
        self,
        interaction: discord.Interaction,
        text: app_commands.Range[str, 1, 2000],
        to: str,
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            result = await self._translate(text, to)
        except QuotaExceededError:
            await interaction.followup.send("⚠️ Monthly translation quota exceeded.", ephemeral=True)
            return
        except TranslationError:
            log.exception("/translate failed")
            await interaction.followup.send("⚠️ Translation failed, try again later.", ephemeral=True)
            return
        display = self._display(to)
        if result.source and base_code(result.source) == base_code(to):
            await interaction.followup.send(already_note(display), ephemeral=True)
            return
        source_base = base_code(result.source) if result.source else None
        parts = chunk(result.text, _CHUNK_LIMIT)
        out = format_reply(preferred_flag(to), display, source_base, to, parts[0] if parts else "")
        await interaction.followup.send(out[:2000], ephemeral=True)

    @app_commands.command(
        name="mylang",
        description="Set your personal language for 🌐 reactions and right-click translation",
    )
    @app_commands.describe(language="Target language — leave empty to see your current setting")
    @app_commands.autocomplete(language=language_autocomplete)
    async def mylang(self, interaction: discord.Interaction, language: str | None = None) -> None:
        user_id = interaction.user.id
        if language is None:
            current = self.bot.store.user_lang(user_id)
            if current:
                content = (
                    f"Your language: {preferred_flag(current)} **{self._display(current)}** (`{current}`). "
                    "Pick a new one below, or type `/mylang language:` to search all languages."
                )
            else:
                content = (
                    "Pick your language below (the most common ones). For any other language, "
                    "type `/mylang language:` and search — e.g. `ja`, `日本語` or `Japanese`."
                )
            await interaction.response.send_message(
                content, ephemeral=True, view=LanguageSelectView(self, current)
            )
            return
        if not any(code == language for code, _native, _english in self.bot.lang_choices):
            await interaction.response.send_message(
                "Unknown language — please pick one from the autocomplete list.", ephemeral=True
            )
            return
        self.bot.store.set_user_lang(user_id, language)
        await interaction.response.send_message(
            f"✅ Personal language set to {preferred_flag(language)} **{self._display(language)}** (`{language}`). "
            "Click 🌐 under any message to use it.",
            ephemeral=True,
        )

    @app_commands.command(name="help", description="How to use AoEM Translator")
    async def help_command(self, interaction: discord.Interaction) -> None:
        text = (
            "**AoEM Translator — how it works**\n"
            "• In configured channels I add flag reactions under messages — click a flag and I reply "
            "with that language.\n"
            "• Click 🌐 and I reply under the message in *your* language (set it once with `/mylang`).\n"
            "• Right-click any message → **Apps → Translate to my language** for an ephemeral translation.\n"
            "• `/translate` — translate any text on demand (private to you).\n"
            "\n**Admins:** `/autoflag` toggles per-channel auto flags, `/flags` picks the flags, "
            "`/settings` tunes behavior, `/stats` shows usage."
        )
        await interaction.response.send_message(text, ephemeral=True)

    # Context menu (SPEC 4.4, 10) — wired in cog_load/cog_unload.
    async def _ctx_translate(self, interaction: discord.Interaction, message: discord.Message) -> None:
        target = self.bot.store.user_lang(interaction.user.id)
        if not target:
            await interaction.response.send_message(
                "Set your language first with `/mylang`.", ephemeral=True
            )
            return
        text = self._extract_text(message)
        if text is None:
            await interaction.response.send_message(
                "Nothing translatable in that message (no text).", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            result = await self._translate(text, target)
        except QuotaExceededError:
            await interaction.followup.send("⚠️ Monthly translation quota exceeded.", ephemeral=True)
            return
        except TranslationError:
            log.exception("Context menu translation failed")
            await interaction.followup.send("⚠️ Translation failed, try again later.", ephemeral=True)
            return
        display = self._display(target)
        if result.source and base_code(result.source) == base_code(target):
            await interaction.followup.send(already_note(display), ephemeral=True)
            return
        source_base = base_code(result.source) if result.source else None
        parts = chunk(result.text, _CHUNK_LIMIT)
        out = format_reply(preferred_flag(target), display, source_base, target, parts[0] if parts else "")
        await interaction.followup.send(out[:2000], ephemeral=True)


async def setup(bot: "TranslatorBot") -> None:
    await bot.add_cog(TranslateCog(bot))
