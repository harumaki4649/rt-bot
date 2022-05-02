# Free RT - Free Channel

from discord.ext import commands, tasks
import discord

from aiomysql import Pool, Cursor

from util import RT, DatabaseManager


class DataManager(DatabaseManager):
    def __init__(self, pool: Pool):
        self.pool = pool
        self.pool._loop.create_task(self._prepare_table())

    async def _prepare_table(self, cursor: Cursor = None):
        await cursor.execute(
            """CREATE TABLE IF NOT EXISTS FreeChannel (
                GuildID BIGINT, ChannelID BIGINT PRIMARY KEY NOT NULL,
                Author BIGINT
            );"""
        )

    async def write(
        self, guild_id: int, channel_id: int, author_id: int,
        cursor: Cursor = None
    ) -> None:
        await cursor.execute(
            """INSERT INTO FreeChannel VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE ;"""
        )


class FreeChannel(commands.Cog):
    def __init__(self, bot: RT):
        self.bot = bot

    @commands.group(
        aliases=("fc", "自由チャンネル", "じち"), extras={
            "headding": {
                "ja": "フリーチャンネルです。自分のチャンネルを作ることができるパネルを作ります。",
                "en": "Free Channel. Create a panel where you can create your own channel."
            }, "parent": "ServerPanel"
        }
    )
    async def freechannel(self, ctx: commands.Context):
        await ctx.reply("Ok")


def setup(bot):
    bot.add_cog(FreeChannel(bot))
