"""Admin slash commands (SPEC 4.8): /autoflag, /settings, /stats."""

import asyncio
import logging
from typing import TYPE_CHECKING, Literal

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot import TranslatorBot

log = logging.getLogger("translatebot.admin")

_MANAGE_GUILD = discord.Permissions(manage_guild=True)


def _admin_group(name: str, description: str) -> app_commands.Group:
    return app_commands.Group(
        name=name,
        description=description,
        default_permissions=_MANAGE_GUILD,
        guild_only=True,
    )


class AdminCog(commands.Cog):
    """Server administration: channels, behavior settings, stats."""

    def __init__(self, bot: "TranslatorBot") -> None:
        self.bot = bot

    autoflag = _admin_group(
        "autoflag", "Automatic flag reactions per channel"
    )
    settings = _admin_group("settings", "Bot behavior settings")

    # ---- /autoflag ----

    @autoflag.command(name="on", description="Enable automatic flag reactions in a channel")
    @app_commands.describe(channel="Channel to enable (default: the current channel)")
    async def autoflag_on(
        self, interaction: discord.Interaction, channel: discord.TextChannel | None = None
    ) -> None:
        target = self._target_channel(interaction, channel)
        guild_settings = self.bot.store.guild(interaction.guild_id)
        if target.id not in guild_settings.auto_channels:
            guild_settings.auto_channels.append(target.id)
            self.bot.store.mark_dirty()
        warning = ""
        me = interaction.guild.me
        if me is not None and not target.permissions_for(me).add_reactions:
            warning = "\n⚠️ I don't have **Add Reactions** permission in that channel yet."
        await interaction.response.send_message(
            f"✅ Automatic flag reactions enabled in {target.mention}.{warning}",
            ephemeral=True,
        )

    @autoflag.command(name="off", description="Disable automatic flag reactions in a channel")
    @app_commands.describe(channel="Channel to disable (default: the current channel)")
    async def autoflag_off(
        self, interaction: discord.Interaction, channel: discord.TextChannel | None = None
    ) -> None:
        target = self._target_channel(interaction, channel)
        guild_settings = self.bot.store.guild(interaction.guild_id)
        if target.id in guild_settings.auto_channels:
            guild_settings.auto_channels.remove(target.id)
            self.bot.store.mark_dirty()
        await interaction.response.send_message(
            f"✅ Automatic flag reactions disabled in {target.mention}.", ephemeral=True
        )

    @autoflag.command(name="list", description="List channels with automatic flag reactions")
    async def autoflag_list(self, interaction: discord.Interaction) -> None:
        guild_settings = self.bot.store.guild(interaction.guild_id)
        if not guild_settings.auto_channels:
            await interaction.response.send_message(
                "No channels enabled yet — use `/autoflag on` in a channel.", ephemeral=True
            )
            return
        lines = []
        for channel_id in guild_settings.auto_channels:
            channel = interaction.guild.get_channel(channel_id) or interaction.guild.get_thread(channel_id)
            lines.append(f"• {channel.mention if channel else f'`{channel_id}` (deleted)'}")
        await interaction.response.send_message(
            "**Channels with automatic flags:**\n" + "\n".join(lines), ephemeral=True
        )

    def _target_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel | None
    ) -> discord.TextChannel:
        resolved = channel or interaction.channel
        if isinstance(resolved, discord.Thread):
            parent = resolved.parent
            if parent is not None:
                return parent
        return resolved

    # ---- /settings ----

    @settings.command(name="show", description="Show all bot settings for this server")
    async def settings_show(self, interaction: discord.Interaction) -> None:
        guild_settings = self.bot.store.guild(interaction.guild_id)
        lines = [
            f"**Delete after:** {guild_settings.delete_after}s" + (" (off)" if not guild_settings.delete_after else ""),
            f"**Min message length:** {guild_settings.min_chars}",
            f"**Globe 🌐:** {'on' if guild_settings.globe else 'off'}",
            f"**Skip source language:** {'on' if guild_settings.skip_source else 'off'}",
            f"**Reaction queue max lag:** {guild_settings.max_lag}s",
            f"**Auto channels ({len(guild_settings.auto_channels)}):** "
            + (", ".join(f"<#{cid}>" for cid in guild_settings.auto_channels[:10]) or "none"),
            f"**Engine:** {self.bot.engine.name if self.bot.engine else '?'}",
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @settings.command(name="delete_after", description="Auto-delete translation replies (0 = keep)")
    @app_commands.describe(seconds="Seconds before a translation reply is deleted (0-3600, 0 = never delete)")
    async def settings_delete_after(
        self, interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 3600]
    ) -> None:
        guild_settings = self.bot.store.guild(interaction.guild_id)
        guild_settings.delete_after = seconds
        self.bot.store.mark_dirty()
        state = "translations are kept" if seconds == 0 else f"translations are deleted after {seconds}s"
        await interaction.response.send_message(f"✅ {state.capitalize()}.", ephemeral=True)

    @settings.command(name="min_chars", description="Minimum message length to get flags")
    @app_commands.describe(n="Minimum meaningful characters (1-50)")
    async def settings_min_chars(
        self, interaction: discord.Interaction, n: app_commands.Range[int, 1, 50]
    ) -> None:
        guild_settings = self.bot.store.guild(interaction.guild_id)
        guild_settings.min_chars = n
        self.bot.store.mark_dirty()
        await interaction.response.send_message(
            f"✅ Messages need at least {n} meaningful characters to get flags.", ephemeral=True
        )

    @settings.command(name="globe", description="Toggle the 🌐 (personal language) reaction")
    @app_commands.describe(on_off="on or off")
    async def settings_globe(
        self, interaction: discord.Interaction, on_off: Literal["on", "off"]
    ) -> None:
        guild_settings = self.bot.store.guild(interaction.guild_id)
        guild_settings.globe = on_off == "on"
        self.bot.store.mark_dirty()
        await interaction.response.send_message(
            f"✅ Globe reaction is **{on_off}**.", ephemeral=True
        )

    @settings.command(name="skip_source", description="Skip flags for the language the message is already in")
    @app_commands.describe(on_off="on or off")
    async def settings_skip_source(
        self, interaction: discord.Interaction, on_off: Literal["on", "off"]
    ) -> None:
        guild_settings = self.bot.store.guild(interaction.guild_id)
        guild_settings.skip_source = on_off == "on"
        self.bot.store.mark_dirty()
        await interaction.response.send_message(
            f"✅ Source-language skipping is **{on_off}**.", ephemeral=True
        )

    @settings.command(name="max_lag", description="Skip flags on messages queued longer than this")
    @app_commands.describe(seconds="Maximum queue delay before a message's flags are skipped (10-300)")
    async def settings_max_lag(
        self, interaction: discord.Interaction, seconds: app_commands.Range[int, 10, 300]
    ) -> None:
        guild_settings = self.bot.store.guild(interaction.guild_id)
        guild_settings.max_lag = seconds
        self.bot.store.mark_dirty()
        await interaction.response.send_message(
            f"✅ Messages queued longer than {seconds}s no longer get flags.", ephemeral=True
        )

    # ---- /stats ----

    @app_commands.command(name="stats", description="Translation usage statistics for this server")
    @app_commands.guild_only()
    @app_commands.default_permissions(_MANAGE_GUILD)
    async def stats(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild_stats = self.bot.store.stats(interaction.guild_id)
        detected = sorted(guild_stats["detected"].items(), key=lambda kv: kv[1], reverse=True)[:10]
        clicks = sorted(guild_stats["clicks"].items(), key=lambda kv: kv[1], reverse=True)[:10]
        lines = ["**Usage statistics**", ""]
        lines.append(
            "**Top detected source languages:** "
            + (", ".join(f"{code} ({count})" for code, count in detected) or "none yet")
        )
        lines.append(
            "**Top clicked flags:** "
            + (", ".join(f"{flag} ({count})" for flag, count in clicks) or "none yet")
        )
        lines.append(
            f"**Translations:** {guild_stats['translations']:,} · "
            f"**Characters:** {guild_stats['chars']:,} · "
            f"**Skipped (stale):** {guild_stats['skipped_stale']:,}"
        )
        try:
            usage = await asyncio.to_thread(self.bot.engine.usage)
        except Exception:
            usage = "unavailable"
        lines.append(f"**Engine:** {self.bot.engine.name if self.bot.engine else '?'} — {usage}")
        await interaction.followup.send("\n".join(lines), ephemeral=True)


async def setup(bot: "TranslatorBot") -> None:
    await bot.add_cog(AdminCog(bot))
