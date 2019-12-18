import io
import logging
import sys

from aiohttp import ClientSession
from discord import Guild
from discord.ext.commands import Bot, Context

from config import Config
from cogs.config import GuildConfig
from errors import ErrorHandler
from help import CustomHelpCommand

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

        # Load extensions
        self.load_extension('remote_config')
        self.load_extension('secure_config')
        self.load_extension('commands')
        self.load_extension('cogs.substits')
        self.load_extension('embeds')
        self.load_extension('cogs.emotes')
        self.load_extension('cogs.console_behavior')
        self.load_extension('cogs.presence')
        self.load_extension('cogs.auto_reactor')
        self.load_extension('cogs.command_panel')
        self.load_extension('cogs.message_fixer')
        self.load_extension('cogs.cleverbot')
        self.load_extension('cogs.config')
        self.load_extension('cogs.calendar_integration')

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


if __name__ == '__main__':
    # Client
    client = Marvin(command_prefix=Config.command_prefix, help_command=CustomHelpCommand())
    client.run(Config.token)
