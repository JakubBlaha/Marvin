import validators
from discord.ext.commands.cog import Cog
from discord.ext.commands import group, Context

from client import Marvin
from utils.temporary_message import TemporaryMessage
from utils.error import send_error


HERE = 'here'


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
            await send_error(ctx, 'Not a valid url.')
            return

        self.bot.store.table_url = url
        self.bot.store.save()

        await ctx.send(f'Table image has been set to this:\n{url}')


def setup(bot: Marvin):
    bot.add_cog(Config(bot))