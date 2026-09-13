import discord
from discord.ext import commands
import sys
sys.path.append('../')
from __main__ import Overseer

class Listeners(commands.Cog):
    def __init__(self, bot: Overseer):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Read in banned nations and guild settings from the database -- we may not need to fetch
        # welcome settings if they're going to be prebanned anyway, so let's save the call.
        # We sort the nations by the first three letters of their name to let us do a search later
        # on in the code.
        guild_settings = await self.bot.fetch(
            "SELECT * FROM guild_settings WHERE guild_id = $1", member.guild.id
        )
        owned = None
        post_join_message = True

        # Send a welcome message if they're not banned.
        if post_join_message:
            settings = await self.bot.fetch(
                "SELECT * FROM welcome_settings WHERE guild_id = $1", member.guild.id
            )
            if not settings:
                return
            if not settings[0]["welcome_channel"]:
                return

            if settings[0]["welcome_channel"] != 0:
                embed = discord.Embed(
                    title=f"Welcome, {member.display_name}!",
                    color=discord.Color.random(),
                    description=settings[0]["embed_message"]
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.add_field(
                    name="Member count",
                    value=member.guild.member_count,
                )
                embed.set_footer(text=f"ID: {member.id}")
                try:
                    await member.guild.get_channel(settings[0]["welcome_channel"]).send(
                        embed=embed,
                        content=member.mention if settings[0]["ping_on_join"] else None
                    )
                except AttributeError:  # Channel was deleted after being set as the welcome channel.
                    await member.guild.get_channel(
                        guild_settings[0]["admin_channel"]
                    ).send("# WARNING\nYour welcome channel was deleted, please set a new one with "
                           "</settings:1073064073459142688>")

async def setup(bot: Overseer):
    await bot.add_cog(Listeners(bot))
