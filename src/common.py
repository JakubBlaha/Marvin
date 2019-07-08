import discord


class Re:
    INDEX = '^[0-9]+$'


class Embed:
    INVALID_INDEX = discord.Embed(
        title='⚠ Invalid index',
        description=
        'All indexes are counted from *0*, the most recent for message and the most top for embed fields!'
    )
