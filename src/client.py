import io
import locale
import logging
import sys

from discord import Guild
from discord.ext.commands import Bot, Context

from auto_reactor import AutoReactor
from cleverbot_client import CleverbotClient
from config import Config
from control_panel_client import ControlPanelClient
from errors import ErrorHandler
from help import CustomHelpCommand
from message_fixer import MessageFixer
from remote_config import RemoteConfig
from timetable import Timetable

# Logging
log_format = '[%(levelname)-8s] [%(name)-16s] %(message)s'
logging.basicConfig(level=Config.loglevel, format=log_format, stream=sys.stdout)
if not Config.modulelog:
    logging.getLogger('discord.gateway').disabled = True
    logging.getLogger('discord.client').disabled = True
    logging.getLogger('discord.http').disabled = True
    logging.getLogger('websockets.protocol').disabled = True

# !log handler
root = logging.getLogger()
handler = logging.StreamHandler(io.StringIO())
handler.setFormatter(logging.Formatter(log_format))
root.addHandler(handler)

logger = logging.getLogger('Client')


class FreefClient(ControlPanelClient, AutoReactor, CleverbotClient, MessageFixer, Bot):
    guild: Guild
    error_handler = ErrorHandler()

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        # Load extensions
        self.load_extension('remote_config')
        self.load_extension('commands')
        self.load_extension('cogs.table_scraper')
        self.load_extension('embeds')
        self.load_extension('cogs.embed_manager')
        self.load_extension('cogs.emotes')
        self.load_extension('cogs.console_behavior')
        self.load_extension('cogs.presence')
        self.load_extension('secure_config')

    async def on_connect(self):
        # Get guild
        self.guild = self.get_guild(Config.guild_id)

        # Reload timetable
        Timetable.reload(RemoteConfig.timetable)
        pass

    async def on_ready(self):
        locale.setlocale(locale.LC_ALL, RemoteConfig.locale)
        await super().on_ready()
        logger.info(f'Client: Ready!')

    async def on_command_error(self, ctx: Context, exception):
        await self.error_handler.handle(ctx, exception)


if __name__ == '__main__':
    # Client
    client = FreefClient(command_prefix='!', help_command=CustomHelpCommand())
    client.run(Config.token)
