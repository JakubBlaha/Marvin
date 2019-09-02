import logging
from typing import List, Dict, Tuple

import yaml
from discord import TextChannel, utils
from discord.ext.commands import Cog, group, Context

from config import Config, ConfigMeta
from decorators import list_subcommands, del_invoc
from secure_config import EncryptedString
from timeout_message import TimeoutMessage

logger = logging.getLogger('RemoteConfig')


async def config_from_channel(ch: TextChannel) -> dict:
    """ Return a dict built from yaml-formatted messages in the channel. """
    data = {}
    async for msg in ch.history():
        content = msg.clean_content

        # Clean up
        content = content.replace('```yaml', '').replace('```', '')

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


class RemoteConfigMeta(ConfigMeta):
    """
    This class allows to access the config values in a discord channel, which's
    name is `config` by default. This allows multiple instances in different
    environments to all have the same config setup shared together.

    This file has to be added as an extension. Then values can be accessed lie so.

        from remote_config import RemoteConfig\n
        name = RemoteConfig.name
    """

    def __init__(cls, *args):
        # We need to stop the base class from loading the config from `config.yaml`
        type.__init__(cls, *args)

    def from_data(cls, data: dict):
        super().from_data(data)

        # Resolve encrypted strings
        for name, expected_type in cls.__annotations__.items():
            value = getattr(cls, name)
            if expected_type is EncryptedString and value:
                setattr(cls, name, EncryptedString(value))


class RemoteConfig(metaclass=RemoteConfigMeta):
    # Optional entries
    locale: str = 'en-US'
    command_panel_channel_id: int = None
    auto_reactor_channel_ids: List[int] = []
    auto_reactor_reaction_ids: List[int] = []
    timetable_url: str = 'https://example.com'
    substits_col_indexes: List[int] = []
    substits_headers: List[str] = []
    substits_replace_contents: Dict[str, str] = {}
    substits_kwargs: Dict[str, str] = {}
    default_substits_target: str = '.'
    exam_channel_id: int = None
    homework_channel_id: int = None
    timetable: List[List[Tuple[str, str, str]]] = []
    presences: List[Tuple[str, str]] = []
    moodle_username: str = ''
    moodle_password: EncryptedString = ''
    chatbot_memory_seconds: int = 120


class RemoteConfigCog(Cog):
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
        data = await config_from_channel(channel)
        RemoteConfig.from_data(data)

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
