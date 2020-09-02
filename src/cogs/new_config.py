import validators
from discord.ext.commands.cog import Cog
from discord.ext.commands import group, Context

from client import Marvin
from utils import send_internal_error, send_error, send_success
from utils.temporary_message import TemporaryMessage
from utils.message import error, success


HERE = 'here'
USER_FRIENDLY_KEYS = {
    'counting.channel.id': 'counting_channel_id',
    'ok.channel.id': 'ok_channel_id',
    'command.panel.channel.id': 'command_panel_channel_id'
}
CHANNEL_ID_KEYS = [
    'counting.channel.id',
    'ok.channel.id',
    'command.panel.channel.id',
]


class Config(Cog, name='Config'):
    def __init__(self, bot: Marvin):
        self.bot = bot

        super().__init__()

    @group()
    async def con(self, ctx: Context):
        """ Bot configuration commands. """
    
    @con.command()
    async def table_img(self, ctx: Context, url: str):
        if not validators.url(url):
            await send_error(ctx.channel, 'Not a valid url.')
            return

        self.bot.store.table_url = url
        self.bot.store.save()

        await ctx.send(f'Table image has been set to this:\n{url}')

    @con.command(name='set.channel.id.as')
    async def set_channel_id_as(self, ctx: Context, key: str):
        """
        Set this channel as something...
        """

        if key not in CHANNEL_ID_KEYS:
            await send_error(ctx.channel, f'Invalid key. Valid keys are `{CHANNEL_ID_KEYS}`.')
            return

        store_key = USER_FRIENDLY_KEYS.get(key)
        
        if store_key is None:
            await send_internal_error(ctx.channel)
            return

        channel_id: int = ctx.channel.id
        setattr(self.bot.store, store_key, channel_id)
        self.bot.store.save()

        await send_success(ctx.channel, f'Key `{key}` successfully set to `{channel_id}`')

    @con.command(name='set.default.for.key')
    async def set_default_for_key(self, ctx: Context, key: str):
        if key not in USER_FRIENDLY_KEYS:
            valid_keys_str = ', '.join(USER_FRIENDLY_KEYS)
            await send_error(ctx.channel, f'Invalid key. Valid keys are: `[{valid_keys_str}]`')
            return

        actual_key = USER_FRIENDLY_KEYS[key]
        setattr(self.bot.store, actual_key, None)
        self.bot.store.save()

        await send_success(ctx.channel, f'Key `{key}` was reset.')


def setup(bot: Marvin):
    bot.add_cog(Config(bot))
