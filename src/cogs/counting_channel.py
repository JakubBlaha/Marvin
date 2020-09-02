from discord.ext.commands import Cog
from discord import Message

from client import Marvin


class Counting(Cog):
    def __init__(self, bot: Marvin):
        self._bot = bot

    @Cog.listener()
    async def on_message(self, msg: Message):
        # Continue only in counting channel
        if msg.channel.id != self._bot.store.counting_channel_id:
            return

        # Continue only when the message author is not Marvin
        if msg.author == self._bot.user:
            return

        async def send_broke_chain():
            await msg.add_reaction('❌')
            await msg.channel.send('Oh no! You broke the chain!')

        async def send_continued_chain():
            await msg.add_reaction('✅')

        # Chain is broken when the message content is not a number
        try:
            number = int(msg.content)
        except ValueError:
            await send_broke_chain()
            return

        # Get previous message / current message if this is the first one
        previous_message = None
        async for _msg in msg.channel.history(limit=2):
            previous_message = _msg

        # If we could not get any message for some reason, return
        if previous_message is None:
            return

        # If this is the first message in the channel,
        # its content must be 1
        if previous_message.id == msg.id:
            if msg.content == '1':
                await send_continued_chain()
            else:
                await send_broke_chain()
            return

        # If the previous message is not a number,
        # this message must be 1
        try:
            previous_number = int(previous_message.content)
        except ValueError:
            if number == 1:
                await send_continued_chain()
                return
            
            await send_broke_chain()
            return

        # If the previous message is a number x,
        # this message must be x + 1
        if number != previous_number + 1:
            await send_broke_chain()
            return

        await send_continued_chain()


def setup(bot: Marvin):
    bot.add_cog(Counting(bot))
