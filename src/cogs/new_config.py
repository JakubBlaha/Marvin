import validators
from discord.ext.commands.cog import Cog
from discord.ext.commands import group, Context

from client import Marvin
from utils import send_internal_error, send_error, send_success
from utils.temporary_message import TemporaryMessage
from utils.error import send_error
from utils.message import error, success


HERE = 'here'
SET_CHANNEL_AS_KEYS = {
    'counting.channel.id': 'counting_channel_id',
    'ok.channel.id': 'ok_channel_id',
}

USER_FRIENDLY_KEYS = {
    'counting.channel.id': 'counting_channel_id',
    'ok.channel.id': 'ok_channel_id',
}


class Config(Cog, name='Config'):
    def __init__(self, bot: Marvin):
        self.bot = bot

        super().__init__()

    @group()
    async def con(self, ctx: Context):
        """ Bot configuration commands. """

    @con.command()
    async def command_panel(self, ctx: Context, here: str = None):
        if here == HERE:
            self.bot.store.command_panel_channel_id = ctx.channel.id
            self.bot.store.save()

            await TemporaryMessage(ctx).send('This is now the Command Panel channel.')

        else:
            channel = self.bot.get_channel(self.bot.store.command_panel_channel_id)
            await ctx.send(f'The Command Panel channel is: `#{channel}`')

    
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

        **Available keys:**
            `counting.channel.id`
        """
        
        store_key = SET_CHANNEL_AS_KEYS.get(key, None)

        if store_key is None:
            valid_keys_str = ', '.join(SET_CHANNEL_AS_KEYS.keys())
            await ctx.send(error(f'Invalid key. Valid keys are [ `{valid_keys_str}` ].'))
            return

        channel_id: int = ctx.channel.id
        setattr(self.bot.store, store_key, channel_id)
        self.bot.store.save()

        await ctx.send(success(f'Key `{key}` successfully set to `{channel_id}`'))

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
