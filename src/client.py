import io
import logging
import sys
from traceback import format_exc

import click
from aiohttp import ClientSession
from discord import Guild
from discord.ext.commands import Bot, Context

from config import Config
from cogs.config import GuildConfig
from errors import ErrorHandler
from exceptions import MarvinInitializeException
from store import Store
from data import ensure_data_dir


EXTENSIONS = [
    'remote_config',
    'secure_config',
    'commands',
    'cogs.substits',
    'embeds',
    'cogs.emotes',
    'cogs.console_behavior',
    'cogs.presence',
    'cogs.auto_reactor',
    'cogs.command_panel',
    'cogs.cleverbot',
    'cogs.config',
    'cogs.calendar_integration',
    'cogs.new_config',
    'cogs.ok',
    'cogs.counting_channel',
]


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


class Marvin(Bot):
    guild: Guild
    error_handler = ErrorHandler()
    session: ClientSession

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        ensure_data_dir()

        # Load store
        self.store = Store()
        self.store.load()

        # Load extensions
        for extension in EXTENSIONS:
            try:
                self.load_extension(extension)
            except Exception:
                click.secho(f'Failed to laod the extension [{extension}]!', fg='red')
                logger.error(format_exc())
                raise MarvinInitializeException

    async def on_connect(self):
        # Create an aiohttp session
        self.session = ClientSession()

        # Get guild
        self.guild = self.get_guild(Config.guild_id)

        # Populate config db for each guild
        GuildConfig.add_guilds([guild.id for guild in self.guilds])

    # noinspection PyMethodMayBeStatic
    async def on_ready(self):
        logger.info(f'Client: Ready!')

    async def on_command_error(self, ctx: Context, exception):
        await self.error_handler.handle(ctx, exception)
