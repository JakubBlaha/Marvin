import random
import asyncio

from discord.ext.commands import Cog
from discord import Message

from client import Marvin


OK = 'ok'
FACTOR = 5


class OkReply(Cog):
    def __init__(self, bot: Marvin):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, msg: Message):
        if msg.author == self.bot.user:
            return

        if msg.content == OK and not random.randint(0, FACTOR):
            await msg.channel.send(OK)


class OkValidation(Cog):
    def __init__(self, bot: Marvin):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, msg: Message):
        """ Delete all messages in ok channel except messages with the content 'ok'. """

        # Continue only in ok channel
        if msg.channel.id != self.bot.store.ok_channel_id:
            return

        if msg.content != 'ok':
            await msg.add_reaction('❌')

        await asyncio.sleep(3)

        await msg.delete()


def setup(bot: Marvin):
    bot.add_cog(OkReply(bot))
    bot.add_cog(OkValidation(bot))
