import asyncio
import discord
import datetime
import gzip
import json
from discord.ext import commands
from discord.ext import tasks
from xml.etree import ElementTree
import sys
sys.path.append('../')
from __main__ import Overseer



class DailyUpdate(commands.Cog):
    def __init__(self, bot: Overseer):
        self.bot = bot
        self.daily_update.start()

    def cog_unload(self):
        self.daily_update.cancel()

    @staticmethod
    def parse(f):
        return ElementTree.parse(f)

    # noinspection DuplicatedCode
    # this code will be left as is because it looks awful to change
    @tasks.loop(time=datetime.time(7, 0, 0, 0, tzinfo=datetime.timezone.utc))
    async def daily_update(self):
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

    @daily_update.before_loop
    async def before_daily_update(self):
        await self.bot.wait_until_ready()

async def setup(bot: Overseer):
    await bot.add_cog(DailyUpdate(bot))
