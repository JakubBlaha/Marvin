from discord import Client, Message

from config import Config, AUTO_REACTOR_CHANNEL_IDS, AUTO_REACTOR_REACTION_IDS


class AutoReactor(Client):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self._channels = Config.get(AUTO_REACTOR_CHANNEL_IDS, [])
        self._reactions = Config.get(AUTO_REACTOR_REACTION_IDS, [])

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