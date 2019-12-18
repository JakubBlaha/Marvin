import sqlite3
from typing import Any, List

from discord.ext.commands import Cog, Context, group, has_role


class GuildConfig:
    conn = sqlite3.connect('sqlite.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create table
    cursor.execute('CREATE TABLE IF NOT EXISTS guild_config('
                   'id INTEGER PRIMARY KEY,'
                   'calendar_id TEXT DEFAULT "primary"'
                   ')')

    @classmethod
    def add_guilds(cls, guild_ids: List[int]):
        """ Call this method in order to make sure a config row for each guild is created in the db."""
        for id_ in guild_ids:
            cls.cursor.execute(f'INSERT OR IGNORE INTO guild_config (id) VALUES ({id_})')
        cls.conn.commit()

    @classmethod
    def get(cls, ctx: Context, key: str):
        """ A shortcut for get_by_guild_id. """
        return cls.get_by_guild_id(ctx.guild.id, key)

    @classmethod
    def get_by_guild_id(cls, guild_id: int, key: str):
        """ Get the value of the key for the server specified by the guild_id. """
        cls.cursor.execute('SELECT * FROM guild_config WHERE id=?', (guild_id,))
        entry = cls.cursor.fetchone()

        if entry is None:
            raise ValueError(f'Config for the guild {guild_id} not found!')

        return entry[key]

    @classmethod
    def set(cls, ctx: Context, key: str, value: Any):
        """ A shortcut for set_by_guild_id. """
        cls.set_by_guild_id(ctx.guild.id, key, value)

    @classmethod
    def set_by_guild_id(cls, guild_id: int, key: str, value: Any):
        """ Set the value of the key for the server specified by the guild_id. """
        with cls.conn:
            cls.cursor.execute(f'UPDATE guild_config SET {key}="{value}" WHERE id={guild_id}')


class ConfigCog(Cog):
    @staticmethod
    async def _confirm_change(ctx: Context):
        await ctx.send(':white_check_mark:  **Successfully changed.**')

    @group()
    @has_role('admin')
    async def conf(self, ctx: Context):
        """ Marvin configurations for your guild. """

    @conf.group()
    async def calendar(self, ctx: Context):
        """ Configurations for the Google Calendar integration. """

    @calendar.command()
    async def id(self, ctx: Context, calendar_id: str = None):
        """
        Set the id of the calendar you want to integrate.

        The id of the calendar can be found in the individual
        calendar settings > Integrate calendar > Calendar ID
        """

        if calendar_id is None:
            await ctx.send(
                f'The value of the key **calendar_id** is `{GuildConfig.get(ctx, "calendar_id")}` '
                f'for your server.')

        else:
            GuildConfig.set(ctx, 'calendar_id', calendar_id)
            await self._confirm_change(ctx)


def setup(bot):
    bot.add_cog(ConfigCog())
