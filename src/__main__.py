import aiohttp
import asyncpg
import discord
import json
import os, sys
from discord.ext import commands
from typing import Optional, List, Literal
from aiolimiter import AsyncLimiter
import logging
import logging.handlers

__version__ = "v0.1.0"

class Overseer(commands.Bot): # bot class
    def __init__(self):
        intents = discord.Intents.all() # we need all Intents except for presences
        intents.presences = False # so we manually disable those
        super().__init__(
            command_prefix="o>",
            intents=intents,
            help_command=None,
        )
        self.pool: Optional[asyncpg.Pool] = None # pool for DB connections
        self.config = {
            "token": os.getenv("BOT_TOKEN"),
            "useragent": os.getenv("NS_USERAGENT"),
            "db_host": os.getenv("POSTGRES_HOST"),
            "db_port": os.getenv("POSTGRES_PORT"),
            "db_name": os.getenv("POSTGRES_DB"),
            "db_user": os.getenv("POSTGRES_USER"),
            "db_pass": os.getenv("POSTGRES_PASSWORD")
        } # fetch config from environment variables
        self.session = None # aiohttp session for NS API requests
        self.limiter = AsyncLimiter(25, 30) # rate limiter for NS API requests

    async def setup_hook(self) -> None:
        self.pool = await asyncpg.create_pool(
            host = self.config["db_host"],
            port = self.config["db_port"],
            user = self.config["db_user"],
            database = self.config["db_name"],
            password = self.config["db_pass"]
        ) # add credentials to the connection pool
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": f"Overseer // {__version__} // Owned by nation={self.config["useragent"]}"
            }
        ) # create a session for connecting to the NS API

        for cog in os.listdir("./src/cogs"):
            try:
                if cog.endswith(".py"):
                    print(f"Loading cog {cog}")
                    await self.load_extension(f"cogs.{cog[:-3]}")
            except discord.ext.commands.errors.NoEntryPointError:
                pass
            except discord.ext.commands.errors.ExtensionFailed as e:
                print(e)
                pass

    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        con: asyncpg.Connection
        async with self.pool.acquire() as con:
            return await con.fetch(query, *args)

    async def execute(self, query: str, *args) -> str:
        con: asyncpg.Connection
        async with self.pool.acquire() as con:
            return await con.execute(query, *args)

    async def close(self) -> None:
        await self.pool.close()
        await self.session.close()
        await super().close()

    async def ns_request(
        self, payload: dict, mode: Literal["GET", "POST"]
    ) -> aiohttp.ClientResponse:
        async with self.limiter:
            if mode.upper() == "GET":
                return await self.session.get(
                    "https://www.nationstates.net/cgi-bin/api.cgi",
                    params=payload,
                )
            elif mode.upper() == "POST":
                return await self.session.post(
                    "https://www.nationstates.net/cgi-bin/api.cgi",
                    data=payload,
                )

    def run(self, *args, **kwargs) -> None:
        super().run(self.config["token"])

handler = logging.StreamHandler(
    stream=sys.stdout
)

if __name__ == "__main__":
    bot = Overseer()
    bot.run(log_handler=handler, log_level=logging.DEBUG)
