from discord.ext.commands import Cog
from discord import Message, Embed
import dateparser

from client import Marvin


class EmbedDatetimeFormatter(Cog):
    def __init__(self, bot: Marvin):
        self._bot = bot

    @Cog.listener()
    async def on_message(self, msg: Message):
        await self._try_format_datetime(msg)

    @Cog.listener()
    async def on_message_edit(self, msg_before: Message, msg_after: Message):
        await self._try_format_datetime(msg_after)

    async def _try_format_datetime(self, msg: Message):
        if msg.author != self._bot.user:
            return

        if not msg.embeds:
            return

        embed: Embed = msg.embeds[0]

        if embed.description == Embed.Empty:
            return

        date = dateparser.parse(embed.description, settings={'PREFER_DATES_FROM': 'future'})

        if date is None:
            return

        formatted_date = date.strftime(r'%A, %d. %B %Y').replace(' 0', ' ')

        if formatted_date == embed.description:
            return

        embed.description = formatted_date
        await msg.edit(embed=embed)


def setup(bot: Marvin):
    bot.add_cog(EmbedDatetimeFormatter(bot))
