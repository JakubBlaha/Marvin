import locale

from discord import Game, Guild, Status
from discord.ext.commands import Bot

from auto_reactor import AutoReactor
from cleverbot_client import CleverbotClient
from config import GUILD_ID, Config
from control_panel_client import ControlPanelClient
from embed_excluder import EmbedExcluder
from events_notifier import EventsNotifier
from logger import Logger
from message_fixer import MessageFixer
from remote_config import LOCALE
from remote_config import RemoteConfig
from twitch_client import TwitchClient


class FreefClient(
    TwitchClient,
    ControlPanelClient,
    AutoReactor,
    CleverbotClient,
    EventsNotifier,
    MessageFixer,
    EmbedExcluder,
    RemoteConfig,
    Bot):
    _oos = False  # Out of service
    guild: Guild

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        # Load extensions
        self.load_extension('commands')
        self.load_extension('cogs.table_scraper')
        self.load_extension('embeds')

    async def on_ready(self):
        self.guild = self.get_guild(Config.get(GUILD_ID))

        # Set the locale
        loc = self[LOCALE]
        locale.setlocale(locale.LC_ALL, self[LOCALE])

        await super().on_ready()

        # Log
        await self.reload_presence()
        Logger.info(f'Client: Ready!')

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


if __name__ == '__main__':
    # Client
    client = FreefClient(command_prefix='!')

    # Logger
    Logger.client = client

    # Run client
    client.run(Config.token)
