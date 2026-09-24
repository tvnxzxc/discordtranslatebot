"""In-game name registration (SPEC 4.7): /ign set|remove|show|setfor."""

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot import TranslatorBot

log = logging.getLogger("translatebot.ign")

MAX_NICKNAME = 32  # Discord nickname limit


class IgnCog(commands.Cog):
    """Members save their in-game name; the bot maintains `IGN | Name` nicknames."""

    ign = app_commands.Group(
        name="ign",
        description="In-game name registration",
        guild_only=True,
    )

    @ign.command(name="set", description="Save your in-game name and update your server nickname")
    @app_commands.describe(nick="Your in-game name (1-24 characters)")
    async def ign_set(self, interaction: discord.Interaction, nick: app_commands.Range[str, 1, 24]) -> None:
        clean = nick.strip()
        if not clean:
            await interaction.response.send_message("The nick cannot be empty.", ephemeral=True)
            return
        self.bot.store.ign_set(interaction.guild_id, interaction.user.id, clean)
        await self._apply_nick(interaction, interaction.user, clean)

    @ign.command(name="remove", description="Remove your in-game name and reset your nickname")
    async def ign_remove(self, interaction: discord.Interaction) -> None:
        removed = self.bot.store.ign_remove(interaction.guild_id, interaction.user.id)
        if not removed:
            await interaction.response.send_message("You don't have an IGN saved.", ephemeral=True)
            return
        await self._reset_nick(interaction, interaction.user)

    @ign.command(name="show", description="Show the saved in-game name of a member")
    @app_commands.describe(user="Member to look up (default: yourself)")
    async def ign_show(
        self, interaction: discord.Interaction, user: discord.Member | None = None
    ) -> None:
        target = user or interaction.user
        saved = self.bot.store.ign_get(interaction.guild_id, target.id)
        if saved:
            await interaction.response.send_message(
                f"In-game name of {target.mention}: **{saved}**", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"{target.mention} has no in-game name saved — they can set one with `/ign set`.",
                ephemeral=True,
            )

    @ign.command(name="setfor", description="Set the in-game name of another member (needs Manage Nicknames)")
    @app_commands.describe(user="Member to update", nick="Their in-game name (1-24 characters)")
    @app_commands.checks.has_permissions(manage_nicknames=True)
    async def ign_setfor(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        nick: app_commands.Range[str, 1, 24],
    ) -> None:
        clean = nick.strip()
        if not clean:
            await interaction.response.send_message("The nick cannot be empty.", ephemeral=True)
            return
        self.bot.store.ign_set(interaction.guild_id, user.id, clean)
        await self._apply_nick(interaction, user, clean)

    # ---- nickname application ----

    async def _apply_nick(
        self, interaction: discord.Interaction, member: discord.Member, nick: str
    ) -> None:
        # Defer first: member.edit is an HTTP call and may exceed the 3s window.
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild_settings = self.bot.store.guild(interaction.guild_id)
        base = member.global_name or member.name
        formatted = guild_settings.ign_format.format(ign=nick, name=base)[:MAX_NICKNAME]
        me = interaction.guild.me
        if me is None or not me.guild_permissions.manage_nicknames:
            await interaction.followup.send(
                "Saved, but I don't have **Manage Nicknames** permission — ask an admin to grant it.",
                ephemeral=True,
            )
            return
        try:
            await member.edit(nick=formatted, reason="IGN set via /ign")
        except discord.Forbidden:
            await interaction.followup.send(
                "Saved. I can't change your nickname (server owner or a role above mine) — "
                "set it manually: `IGN | Name`.",
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            log.warning("Nickname edit failed for %s: %s", member.id, exc)
            await interaction.followup.send(
                "Saved, but the nickname update failed — try again in a moment.", ephemeral=True
            )
            return
        whom = "your" if member.id == interaction.user.id else f"{member.mention}'s"
        await interaction.followup.send(
            f"✅ Saved — {whom} nickname is now **{formatted}**.", ephemeral=True
        )

    async def _reset_nick(self, interaction: discord.Interaction, member: discord.Member) -> None:
        # Defer first: member.edit is an HTTP call and may exceed the 3s window.
        await interaction.response.defer(ephemeral=True, thinking=True)
        me = interaction.guild.me
        if me is None or not me.guild_permissions.manage_nicknames:
            await interaction.followup.send(
                "Removed, but I don't have **Manage Nicknames** permission to reset your nickname.",
                ephemeral=True,
            )
            return
        try:
            await member.edit(nick=None, reason="IGN removed via /ign")
        except discord.Forbidden:
            await interaction.followup.send(
                "Removed. I can't reset your nickname (server owner or a role above mine) — "
                "please reset it manually.",
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            log.warning("Nickname reset failed for %s: %s", member.id, exc)
            await interaction.followup.send(
                "Removed, but the nickname reset failed — try again in a moment.", ephemeral=True
            )
            return
        whom = "your" if member.id == interaction.user.id else f"{member.mention}'s"
        await interaction.followup.send(
            f"✅ IGN removed — {whom} nickname was reset.", ephemeral=True
        )

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            message = "You need the **Manage Nicknames** permission to use this."
        else:
            log.exception("IGN command failed")
            message = "Something went wrong — try again later."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except discord.HTTPException:  # pragma: no cover - interaction expired
            log.debug("Could not deliver error response for /ign")


async def setup(bot: "TranslatorBot") -> None:
    await bot.add_cog(IgnCog(bot))
