import asyncio
import discord
import datetime
import gzip
from xml.etree import ElementTree
import os
import openpyxl.worksheet.worksheet
from discord.ext import commands
from framework.bot import Bloo
from openpyxl import Workbook


class Developer(commands.Cog):
    def __init__(self, bot: Bloo):
        self.bot = bot

    @staticmethod
    def linkify(region: str):
        return f'=HYPERLINK("https://www.nationstates.net/region={region}", "{region}")'

    @staticmethod
    def write(audit_list: list):
        wb = Workbook()
        ws: openpyxl.worksheet.worksheet.Worksheet = wb.active
        ws.append(
            [
                "Discord ID",
                "Nation",
                "Status",
                "Region (link)",
                "Delegate",
                "Delegate Votes",
                "Numnations",
                "WANations",
            ]
        )
        for audit in audit_list:
            ws.append(
                [
                    audit["discord_id"],
                    audit["nation"],
                    audit["status"],
                    audit["region"],
                    audit["delegate"],
                    audit["delegatevotes"],
                    audit["numnations"],
                    audit["wanations"],
                ]
            )
        wb.save("audit.xlsx")
        wb.close()

    @commands.command(name="reload", description="Reload a cog.")
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, *, cog: str):
        if "*" in cog:
            for filename in os.listdir("cogs"):
                if os.path.isfile(os.path.join("cogs", filename)):
                    if filename.endswith(".py"):
                        await self.bot.reload_extension(f"cogs.{filename[:-3]}")
            await ctx.send("Done!", ephemeral=True)
        else:
            for c in cog.split(","):
                await self.bot.reload_extension(f"cogs.{c.lower().replace(' ', '_')}")
            await ctx.send("Done!", ephemeral=True)

    @commands.command(name="load", description="Load a cog.")
    @commands.is_owner()
    async def load(self, ctx: commands.Context, cog: str):
        await self.bot.load_extension(f"cogs.{cog.lower().replace(' ', '_')}")
        await ctx.send("Done!", ephemeral=True)

    @commands.command(name="unload", description="Unload a cog.")
    @commands.is_owner()
    async def unload(self, ctx: commands.Context, cog: str):
        await self.bot.unload_extension(f"cogs.{cog.lower().replace(' ', '_')}")
        await ctx.send("Done!", ephemeral=True)

    @commands.command(name="say", description="Send a message to a channel.")
    @commands.is_owner()
    async def say(
        self, ctx: commands.Context, channel: discord.TextChannel, *, message: str
    ):
        await channel.send(message)
        await ctx.send("Done!", ephemeral=True)

    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx: commands.Context, guild: int = None):
        if guild:
            await self.bot.tree.sync(guild=discord.Object(guild))
        else:
            await self.bot.tree.sync()
        await ctx.send(":arrows_counterclockwise:")

    @staticmethod
    def parse(f):
        return ElementTree.parse(f)

    # noinspection DuplicatedCode
    @commands.command()
    @commands.is_owner()
    async def daily_update(self, ctx: commands.Context):
        now_ts = datetime.datetime.now()
        async with self.bot.session.get(
            "https://www.nationstates.net/pages/nations.xml.gz"
        ) as resp:
            with open("nations.xml.gz", "wb") as f:
                f.write(await resp.read())
        with gzip.open("nations.xml.gz", "rb") as f:
            tree = await asyncio.to_thread(self.parse, f)
            root = tree.getroot()
            for nation in root.findall("NATION"):
                name = nation.find("NAME").text.lower().replace(" ", "_")
                region = nation.find("REGION").text.lower().replace(" ", "_")
                unstatus = nation.find("UNSTATUS").text
                endorsements = (
                    nation.find("ENDORSEMENTS").text
                    if nation.find("ENDORSEMENTS") is not None
                    else 0
                )
                await self.bot.execute(
                    "INSERT INTO nation_dump (nation, region, unstatus, endorsements, last_update) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (nation) DO UPDATE SET region = $2, unstatus = $3, endorsements = $4, last_update = $5",
                    name,
                    region,
                    unstatus,
                    endorsements,
                    now_ts,
                )
        all_guilds = await self.bot.fetch("SELECT guild_id FROM nsv_settings")
        for guild in all_guilds:
            guild_id = guild["guild_id"]
            guild_obj: discord.Guild = self.bot.get_guild(guild_id)
            if guild_obj is None:
                self.bot.logger.info("Could not find guild, skipping...")
                continue
            if not guild_obj.chunked:
                await guild_obj.chunk()
            self.bot.logger.info(f"Now updating {guild_obj.name} | ID: ({guild_id})")
            settings = await self.bot.fetch(
                "SELECT * FROM nsv_settings WHERE guild_id = $1", guild_id
            )
            if settings[0]["region"] is None:
                continue
            for member in guild_obj.members:
                if settings[0]["region"] and len(settings[0]["region"].split(",")) > 1:
                    set_region = settings[0]["region"].split(",")
                    set_region = [x.strip() for x in set_region]
                else:
                    set_region = [settings[0]["region"].strip() if settings[0]["region"] else None]
                discord_id = member.id
                status = "guest"
                vals = await self.bot.fetch(
                    "SELECT * FROM nsv_table WHERE discord_id = $1 AND guild_id = $2",
                    discord_id,
                    guild_id,
                )
                if not vals:
                    self.bot.logger.info("No nations found, skipping...")
                    continue
                else:
                    for val in vals:
                        record = await self.bot.fetch(
                            "SELECT * FROM nation_dump WHERE nation = $1",
                            val["nation"],
                        )
                        if not record:
                            self.bot.logger.info("Nation has CTEd, skipping...")
                            continue
                        else:
                            if record[0]["region"] in set_region:
                                status = "resident"
                                if record[0]["unstatus"] == "WA Member":
                                    status = "wa-resident"
                await self.bot.execute(
                    "UPDATE nsv_table SET status = $1 WHERE discord_id = $2 AND guild_id = $3",
                    status,
                    discord_id,
                    guild_id,
                )
            self.bot.logger.info(f"Updated {guild_obj.name} | ID: ({guild_id})")
        self.bot.logger.info("Finished daily update.")

async def setup(bot):
    await bot.add_cog(Developer(bot))
