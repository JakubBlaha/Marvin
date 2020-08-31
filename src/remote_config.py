import logging
from typing import Dict, List, Tuple

import yaml
from discord import TextChannel, utils
from discord.ext.commands import Cog, Context, group

from config import Config, ConfigBase
from decorators import del_invoc, list_subcommands
from secure_config import EncryptedString
from timeout_message import TimeoutMessage
from timetable import Timetable

logger = logging.getLogger('RemoteConfig')


async def config_from_channel(ch: TextChannel, load_dev: bool = False) -> dict:
    """ Return a dict built from yaml-formatted messages in the channel.
    :param ch: The text channel the config should be taken from.
    :param load_dev: Whether dev config should be loaded. These are messages
        starting with `dev`.
    :return:
    """

    data = {}
    async for msg in ch.history(oldest_first=True):
        content = msg.clean_content

        _is_dev = content.startswith('dev')
        if _is_dev and not load_dev:
            continue
        elif _is_dev:
            logger.debug('Loaded message ' + msg.content.replace('\n', '\\n'))

        # Clean up
        content = content.replace('```yaml', '').replace('```', '').replace('dev', '', 1)

        # Convert
        # noinspection PyBroadException
        try:
            partial_data = yaml.safe_load(content)
        except Exception:
            logger.warning(f'Converting message {msg.id} to yaml failed!')
            continue

        # Update the real data
        try:
            data.update(partial_data)
        except ValueError:
            logger.warning(f'Converting message {msg.id} to dict failed!')

    # Warn if content could not be loaded
    if not data:
        logger.warning(f'No config content found in the channel {ch}')

    return data


# noinspection PyPep8Naming
class RemoteConfig_(ConfigBase):
    # Optional entries
    command_panel_timeout: int = 3600
    auto_reactor_channel_ids: List[int] = []
    auto_reactor_reaction_ids: List[int] = []
    timetable_url: str = 'https://example.com'
    substits_kwargs: Dict[str, str] = {}
    substits_pdf_bbox: Tuple[float, float, float, float] = (0, 0, 1, 1)  # left, top, right, bottom
    exam_channel_id: int = None
    homework_channel_id: int = None
    timetable: Timetable = None
    presences: List[Tuple[str, str]] = []
    chatbot_memory_seconds: int = 120


# TEMPORARY
RemoteConfig = RemoteConfig_({})


class RemoteConfigCog(Cog):
    config = RemoteConfig

    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_connect(self):
        logger.info(f'Reloading the config from channel `{Config.remote_config_channel_name}`')

        # Get the config channel
        await self.bot.fetch_guild(Config.guild_id)
        guild = self.bot.get_guild(Config.guild_id)
        channel = await self.bot.fetch_channel(utils.get(guild.channels, name=Config.remote_config_channel_name).id)

        # Load the config
        data = await config_from_channel(channel, load_dev=Config.load_dev_config)

        RemoteConfig.__init__(data)

    @group(hidden=True)
    @list_subcommands
    async def config(self, ctx: Context):
        pass

    # noinspection PyUnusedLocal
    @config.command(hidden=True)
    @del_invoc
    async def reload(self, ctx: Context):
        """ Reload the remote config. """
        await self.on_connect()
        await TimeoutMessage(ctx).send('✅ The config has been reloaded!')


def setup(bot):
    bot.add_cog(RemoteConfigCog(bot))
