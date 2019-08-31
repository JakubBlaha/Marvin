from discord import Message
from discord.ext.commands import Cog

from client import FreefClient
from remote_config import RemoteConfig


class AutoReactor(Cog):
    bot: FreefClient
    _channels: list
    _reactions: list

    def __init__(self, bot: FreefClient):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        self._channels = RemoteConfig.auto_reactor_channel_ids
        self._reactions = RemoteConfig.auto_reactor_reaction_ids

    @Cog.listener()
    async def on_message(self, msg: Message):
        # Skip own messages
        if msg.author == self.bot.user:
            return

        # Skip not configured channels
        if msg.channel.id not in self._channels:
            return

        # Add reactions
        for id_ in self._reactions:
            await msg.add_reaction(self.bot.get_emoji(id_))


def setup(bot: FreefClient):
    bot.add_cog(AutoReactor(bot))
