import sys
from discord import Game, Status
from discord.ext.commands import Bot, Command

from logger import Logger
from config import Config
from message_fixer import MessageFixer
from embed_excluder import EmbedExcluder
from large_emoji_client import LargeEmojiCLient


class FreefClient(MessageFixer, EmbedExcluder, LargeEmojiCLient, Bot):
    def __init__(self, *args, **kw):
        Logger.info('Client: Initializing client')
        super().__init__(*args, **kw)
        self.load_extension('commands')

    async def on_ready(self):
        Logger.info(f'Client: Logged on as {self.user}')
        await self.change_presence(
            activity=Game(Config.get('presence', 'Hello world!')),
            status=getattr(Status, str(Config.status), Status.online))


# Logger
sys.stderr = Logger
sys.stdout = Logger

# Client
client = FreefClient(command_prefix='!')
Logger.client = client
Logger.log_channel = Config.log_channel
client.run(Config.token)
