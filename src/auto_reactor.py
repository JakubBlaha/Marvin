from discord import Client, Message

from remote_config import RemoteConfig


class AutoReactor(Client):
    _channels: list
    _reactions: list

    async def on_ready(self):
        self._channels = RemoteConfig.auto_reactor_channel_ids
        self._reactions = RemoteConfig.auto_reactor_reaction_ids

    async def on_message(self, msg: Message):
        await super().on_message(msg)

        # Skip own messages
        if msg.author == self.user:
            return

        # Skip not configured channels
        if msg.channel.id not in self._channels:
            return

        # Add reactions
        for id_ in self._reactions:
            await msg.add_reaction(self.get_emoji(id_))
