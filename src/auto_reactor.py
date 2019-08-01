from discord import Client, Message

from remote_config import RemoteConfig


class AutoReactor(RemoteConfig, Client):
    async def on_ready(self):
        await super().on_ready()

        self._channels = self['auto_reactor_channel_ids'] or []
        self._reactions = self['auto_reactor_reaction_ids'] or []

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
