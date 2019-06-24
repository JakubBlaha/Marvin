import yaml

from discord import Client, TextChannel, Guild, utils

from logger import Logger
from config import Config, GUILD_ID


class RemoteConfig(Client):
    '''
    This class allows to access the config values in a discord channel, which's
    name is `config` by default. This allows multiple instances in different
    environments to all have the same config setup shared together.

    This class should be used as a first base class to any subclass requiring
    this feature. Make sure the method `reload_config` is called before accessing
    any values. It is called in the `on_ready` coroutine by default.
    '''
    data = {}
    guild: Guild

    async def on_ready(self):
        await self.reload_config()

    async def reload_config(self, channel_name='config'):
        Logger.info(
            f'RemoteConfig: Reloading the config from channel {channel_name}')

        # Get the guild
        self.guild = self.get_guild(Config.get(GUILD_ID))

        # Get the config channel
        _channel = utils.get(self.guild.channels, name=channel_name)

        # Load the config
        self.data = await self._get_yaml_from_channel(_channel)

    async def _get_yaml_from_channel(self, ch: TextChannel) -> dict:
        ''' Return a dict taken from the latest message in the yaml format. '''
        # Get the latest message
        _msg = None
        async for _msg in ch.history():
            break

        # Warn if no message was found
        if not _msg:
            Logger.warning(
                f'RemoteConfig: Could not get the last message from channel {ch}'
            )
            return {}

        # Convert the data
        _content = _msg.content
        _content = _content.replace('```yaml\n', '').replace('```', '')
        _data = yaml.safe_load(_content)

        # Ensure the data is valid
        if not isinstance(_data, dict):
            Logger.warning(f'RemoteConfig: Invalid data type: {type(_data)}')
            return {}

        return _data

    def get(self, option_name: str, default=None):
        ''' Return a value from the remote config. '''
        if not self.data:
            Logger.warning(
                f'RemoteConfig: Attempt to get value {option_name} before the '
                'data was loaded!')

        return self.data.get(option_name, default)

    def __getitem__(self, key: str):
        '''
        Similar to the `get` method, but shorter syntax can be used.
        Return the value found for the `key` argument from `self.data`, default `None`.
        '''

        return self.get(key)