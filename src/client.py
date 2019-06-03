import sys
from discord import Game, Status
from discord.ext.commands import Bot, Command

from logger import Logger
from config import Config
from message_fixer import MessageFixer
from embed_excluder import EmbedExcluder
from large_emoji_client import LargeEmojiCLient
from events_notifier import EventsNotifier
from cleverbot_client import CleverbotClient


class FreefClient(CleverbotClient, EventsNotifier, MessageFixer, EmbedExcluder,
                  LargeEmojiCLient, Bot):
    _oos = False  # Out of service

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.load_extension('commands')
        self.load_extension('cogs.table_scraper')

    async def on_ready(self):
        await self.reload_presence()
        Logger.info(f'Client: Logged on as {self.user}')

    async def reload_presence(self):
        await self.change_presence(activity=Game(
            Config.get('presence', 'Hello world!')),
                                   status=getattr(Status, str(Config.status),
                                                  Status.online))

    async def toggle_oos(self):
        if self._oos:
            await self.reload_presence()
        else:
            await self.change_presence(activity=Game('❗ Out of service ❗'),
                                       status=Status.do_not_disturb)

        self._oos = not self._oos

        Logger.info(f'Client: Toggled out of service {self._oos}')


# Client
client = FreefClient(command_prefix='!')

# Logger
Logger.client = client

# Run client
client.run(Config.token)
