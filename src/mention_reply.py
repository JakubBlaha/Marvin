from discord import Message
from discord.ext.commands import Bot

from emojis import Emojis


class MentionReplier(Bot):
    async def on_message(self, msg: Message):
        await super().on_message(msg)

        if self.user in msg.mentions:
            await msg.channel.send(Emojis.HeyGuys*3 + '\n' + msg.author.mention)
