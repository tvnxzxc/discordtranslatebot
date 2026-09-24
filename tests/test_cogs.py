"""Regression: every cog must expose ``self.bot`` set from its constructor.

This mirrors the real bug where AdminCog/IgnCog loaded fine but every
command crashed at runtime with AttributeError: no attribute 'bot'.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import discord
from discord.ext import commands


def _make_bot() -> commands.Bot:
    intents = discord.Intents.default()
    return commands.Bot(command_prefix="!", intents=intents)


def test_all_cogs_expose_bot():
    from translatebot.cogs.admin import AdminCog
    from translatebot.cogs.ign import IgnCog
    from translatebot.cogs.translate import TranslateCog

    bot = _make_bot()
    for cog_cls in (TranslateCog, AdminCog, IgnCog):
        cog = cog_cls(bot)
        assert cog.bot is bot, f"{cog_cls.__name__} does not expose self.bot"
