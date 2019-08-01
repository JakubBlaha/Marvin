import io
import locale
import logging
import sys

from discord import Game, Guild, Status
from discord.ext.commands import Bot

from auto_reactor import AutoReactor
from cleverbot_client import CleverbotClient
from config import GUILD_ID, Config
from control_panel_client import ControlPanelClient
from message_fixer import MessageFixer
from remote_config import LOCALE
from remote_config import RemoteConfig

# Logging
log_format = '[%(levelname)-8s] [%(name)-16s] %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format, stream=sys.stdout)
logging.getLogger('discord.gateway').setLevel(logging.ERROR)
logging.getLogger('discord.client').setLevel(logging.ERROR)

# !log handler
root = logging.getLogger()
handler = logging.StreamHandler(io.StringIO())
handler.setFormatter(logging.Formatter(log_format))
root.addHandler(handler)

logger = logging.getLogger('Client')


class FreefClient(ControlPanelClient, AutoReactor, CleverbotClient, MessageFixer, RemoteConfig, Bot):
    _oos = False  # Out of service
    guild: Guild

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        # Load extensions
        self.load_extension('commands')
        self.load_extension('cogs.table_scraper')
        self.load_extension('embeds')
        self.load_extension('cogs.embed_manager')
        self.load_extension('cogs.emotes')

    async def on_connect(self):
        await super().on_connect()

        self.guild = self.get_guild(Config.get(GUILD_ID))

    async def on_ready(self):
        # Set the locale
        locale.setlocale(locale.LC_ALL, self[LOCALE])

        await super().on_ready()

        # Log
        await self.reload_presence()
        logging.info(f'Client: Ready!')

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

        logging.info(f'Client: Toggled out of service {self._oos}')


if __name__ == '__main__':
    # Client
    client = FreefClient(command_prefix='!')
    client.run(Config.token)
