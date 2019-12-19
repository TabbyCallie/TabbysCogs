import discord
import asyncio
import random
import re

from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import box
from redbot.core.bot import Red

from redbot.core.data_manager import storage_type
from redbot.core.config import Group
from redbot.core.drivers import IdentifierData

class Xp(commands.Cog):
    """
    smaller economy system.
    """
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=23452345, force_registration=True
        )
        self.config.register_guild(
            amount=1,
            enableGuild = True,
            enabledChannels = [],
        )
        self.config.register_member(chars=0)

    @commands.guild_only()
    @commands.group()
    async def xp(self, ctx):
        """Config options for XP."""
        pass

    @xp.command(aliases=["myxp"])
    async def balance(self, ctx, *, user: discord.Member = None):
        """Check how many points you have."""
        if not user:
            chars = int(await self.config.member(ctx.author).chars())
            await ctx.send("You have {0} points".format(chars))
        else:
            chars = int(await self.config.member(user).chars())
            await ctx.send("{0} has {1} points".format(user.display_name, chars))

    @xp.command(aliases=["allxp"])
    async def leaderboard(self, ctx):
        """Display the server's character leaderboard."""
        ids = await self._get_ids(ctx)
        list = []
        pos = 1
        pound_len = len(str(len(ids)))
        header = "{pound:{pound_len}}{score:{bar_len}}{name:2}\n".format(
            pound="#",
            name="Name",
            score="Points",
            pound_len=pound_len + 3,
            bar_len=pound_len + 9,
        )
        temp_msg = header
        for a_id in ids:
            a = ctx.guild.get_member(a_id)
            if a is None:
                continue
            name = a.display_name
            chars = await self.config.member(a).chars()
            if chars == 0:
                continue
            score = "chars"
            if a_id != ctx.author.id:
                temp_msg += (
                    f"{f'{pos}.': <{pound_len+2}} {chars: <{pound_len+8}} {name}\n"
                )
            else:
                temp_msg += (
                    f"{f'{pos}.': <{pound_len+2}} "
                    f"{chars: <{pound_len+8}} "
                    f"<<{name}>>\n"
                )
            if pos % 10 == 0:
                list.append(box(temp_msg, lang="md"))
                temp_msg = header
            pos += 1
        if temp_msg != header:
            list.append(box(temp_msg, lang="md"))
        if list:
            if len(list) > 1:
                await menu(ctx, list, DEFAULT_CONTROLS)
            else:
                await ctx.send(list[0])
        else:
            empty = "Nothing to see here."
            await ctx.send(box(empty, lang="md"))

    @xp.command()
    @checks.admin_or_permissions(manage_guild=True)
    async def set(self, ctx, amount: int, *, user: discord.Member = None):
        """Set someone's amount of points."""
        author = ctx.author
        if not user:
            user = author

        if amount <= 0:
            return await ctx.send("Uh oh, amount has to be more than 0.")
        await self.config.member(user).chars.set(amount)
        await ctx.send(
            "Set {0}'s balance to {1} points".format(user.mention, amount)
        )

    @xp.command()
    @checks.admin_or_permissions(manage_guild=True)
    async def add(self, ctx, amount: int, *, user: discord.Member = None):
        """Add points to someone."""
        author = ctx.author
        if not user:
            user = author


        if amount <= 0:
            return await ctx.send("Uh oh, amount has to be more than 0.")
        user_points = int(await self.config.member(user).chars())
        user_points += amount
        await self.config.member(user).chars.set(user_points)
        await ctx.send(
            "Added {0} points to {1}'s balance.".format(amount, user.mention)
        )

    @xp.command()
    @checks.admin_or_permissions(manage_guild=True)
    async def take(self, ctx, amount: int, *, user: discord.Member = None):
        """Take points away from someone."""
        author = ctx.author
        if not user:
            user = author

        if amount <= 0:
            return await ctx.send("Uh oh, amount has to be more than 0.")
        user_points = int(await self.config.member(user).chars())
        if amount <= user_points:
            user_points -= amount
            await self.config.member(user).chars.set(user_points)
            await ctx.send(
                "Took away {0} points from {1}'s balance.".format(
                    amount, user.mention
                )
            )
        else:
            await ctx.send("{0} doesn't have enough :points:".format(user.mention))

    @commands.guild_only()
    @checks.guildowner()
    @commands.group()
    async def xpset(self, ctx):
        """Config options for XP."""
        pass

    @xpset.command()
    async def channel(self, ctx, value: bool=None):
        """
        Set if XP should record stats for this channel.

        Defaults to False.
        This value is channel specific.
        """
        v = await self.config.guild(ctx.guild).enabledChannels()
        if value is None:
            if ctx.channel.id not in v:
                await ctx.send('Stats are not being recorded in this channel.')
            else:
                await ctx.send('Stats are being recorded in this channel.')
        else:
            if value:
                if ctx.channel.id not in v:
                    await ctx.send('Stats are already not being recorded in this channel.')
                else:
                    v.remove(ctx.channel.id)
                    await self.config.guild(ctx.guild).enabledChannels.set(v)
                    await ctx.send('Stats will not be recorded in this channel.')
            else:
                if ctx.channel.id in v:
                    await ctx.send('Stats are already being recorded in this channel.')
                else:
                    v.append(ctx.channel.id)
                    await self.config.guild(ctx.guild).enabledChannels.set(v)
                    await ctx.send('Stats will be recorded in this channel.')

    @xpset.command()
    async def resetall(self, ctx, confirmation: bool = False):
        """Delete all points from all members."""
        if confirmation is False:
            return await ctx.send(
                "This will delete **all** points from all members. This action **cannot** be undone.\n"
                "If you're sure, type `{0}xpset resetall yes`.".format(
                    ctx.clean_prefix
                )
            )

        for member in ctx.guild.members:
            chars = int(await self.config.member(member).chars())
            if chars != 0:
                await self.config.member(member).chars.set(0)

        await ctx.send("All points have been deleted from all members.")

    @commands.Cog.listener()
    async def on_message_without_command(self, msg):
        """Passively records all message contents."""
        if not msg.author.bot and isinstance(msg.channel, discord.TextChannel):
            cfg = await self.config.guild(msg.guild).all()
            enableGuild = cfg['enableGuild']
            enabledChannels = cfg['enabledChannels']
            if enableGuild and msg.channel.id in enabledChannels:
                chars = len(re.sub(r'[\s]', '', msg.content.lower()))/4
                #Get the latest memdict.
                chartotal = await self.config.member(msg.author).chars()
                #Update the memdict.
                chartotal += chars
                #Save the memdict.
                await self.config.member(msg.author).chars.set(chartotal)

    async def _get_ids(self, ctx):
        data = await self.config.all_members(ctx.guild)
        ids = sorted(data, key=lambda x: data[x]["chars"], reverse=True)
        return ids
