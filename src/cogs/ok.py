import random

from discord.ext.commands import Cog
from discord import Message

from client import Marvin


OK = 'ok'
FACTOR = 5


class Ok(Cog):
    def __init__(self, bot: Marvin):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, msg: Message):
        if msg.author == self.bot.user:
            return

        if msg.content == OK and not random.randint(0, FACTOR):
            await msg.channel.send(OK)


def setup(bot: Marvin):
    bot.add_cog(Ok(bot))