import re
from asyncio import TimeoutError, sleep
from random import randint, random
from traceback import format_exc

import yaml
from discord import Client, Color, Embed, File, Guild, Message, utils
from discord.errors import NotFound
from discord.ext.commands import Bot, Cog, command
from simpleeval import simple_eval

from command_modules import bag
from command_modules.embed import is_embed_up_to_date
from command_modules.get_subjects import get_subjects
from decorators import del_invoc
from emojis import Emojis
from logger import Logger
from utils.channel_embed_summary import channel_embed_summary
from utils.command_embed import send_command_embed
from utils.embed_to_text import embed_to_text
from utils.get_datetime_from_string import get_datetime_from_string

DEFAULT_EMBED = {
    'title': '\u200b',
    'description': '\u200b',
    'footer': None,
    'fields': {},
    'del_fields': (),
    'color': Embed.Empty
}


async def request_input(ctx, message, regex='', mention=True, allowed=[]):
    # create regex from allowed
    if allowed and not regex:
        regex = re.compile(f'({"|".join(allowed)}){{1}}', re.IGNORECASE)
    elif allowed and regex:
        Logger.warning(
            f'Input: Given `allowed` {allowed} but also `regex` {regex}')

    # Send the asking message
    bot_message = (await ctx.send(
        ctx.author.mention * mention + ' ' + message +
        ('\n' + f'*Allowed values: {", ".join(allowed)}*') * bool(regex)))
    await bot_message.add_reaction('\u2b07')

    def check(msg):
        return msg.channel == ctx.channel and msg.author == ctx.author

    msg_ok = False
    while not msg_ok:
        user_msg = await ctx.bot.wait_for('message', check=check)
        msg_ok = re.match(regex, user_msg.content)
        await user_msg.add_reaction('\u2705' if msg_ok else '\u274c')
        await sleep(.5)
        await user_msg.delete()

    await bot_message.delete()
    return user_msg.content


class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot

    @command()
    async def repeat(self, ctx, string: str, n: int = 10):
        '''
        Repeats the given string.
        
        Repeats the given string\emote n times. Maximum is 50.
        '''

        await send_command_embed(ctx,
                                 string * min(n, 50),
                                 show_invocation=False)

    @command(aliases=['table', 'rozvrh'])
    async def timetable(self, ctx):
        '''Send an image of our timetable.'''
        await send_command_embed(ctx, send=False)
        ctx.output_embed.set_image(
            url=self.bot['timetable_url'] or 'https://example.com')
        await ctx.send(embed=ctx.output_embed)

    @command()
    async def subj(self, ctx):
        '''
        Gives the subjects to prepare for.

        Gives the subjects to prepare for dependently on the current time.
        If it's already after the lunch, gives the subjects of the following
        day, otherwise gives the subjects for the current day. The subjects
        are given in an alphabetical order.
        '''

        await send_command_embed(ctx, f'```fix\n{get_subjects()}```')

    @command()
    async def eval(self, ctx, *, expression):
        '''
        Evaluates a python expression.

        Evaluates a python expression. If the evaluation fails,
        outputs the error code. It is not possible to access variables
        or functions. Example: 25**(1/2) -> 5.0
        '''

        try:
            ret = f'```python\n{simple_eval(expression)}```'
        except Exception as ex:
            ret = f':warning: **Failed to evaluate** :warning:\n```{ex}```'

        await send_command_embed(ctx, ret)

    @command(aliases=['testy'])
    @del_invoc
    async def test(self, ctx):
        ''' Embed summary of the *testy* channel. '''
        await ctx.send(embed=await channel_embed_summary(
            utils.get(ctx.guild.channels, name='testy'),
            kw={'footer': {
                'text': ctx.author.display_name
            }}))

    @command(aliases=['ukoly'])
    @del_invoc
    async def ukol(self, ctx):
        ''' Embed summary of the *úkoly* channel. '''
        await ctx.send(embed=await channel_embed_summary(
            utils.get(ctx.guild.channels, name='úkoly'),
            kw={'footer': {
                'text': ctx.author.display_name
            }}))

    @command()
    async def log(self, ctx):
        '''
        Return the current log.

        Return the current log consisting of sys.stdout and sys.stderr.
        '''

        await send_command_embed(ctx, f'```{Logger.get_log()[-1980:]}```')
        Logger.info(f'Command: Sent logs to `{ctx.channel.name}` channel')

    @command()
    async def random(self, ctx, arg1: int = None, arg2: int = None):
        '''
        Gives a random number depending on the arguments.

        Up to two arguments can be passed into this function. If both arguments
        are omitted, the given number will be in a range from 0 to 1. If one
        argument is given, the given number will be in a range from 0 to arg1.
        If both arguments are given, the given number will be in a range from
        arg1 to arg2.
        '''

        if not (arg1 is None or arg2 is None):
            res = randint(arg1, arg2)
        elif arg1 is not None:
            res = randint(0, arg1)
        else:
            res = random()

        await send_command_embed(ctx, f'```python\n{res}```')

    @command(hidden=True)
    @del_invoc
    async def toggle_oos(self, ctx):
        ''' Toggle out of service. '''
        await self.bot.toggle_oos()

    @command()
    async def bag(self, ctx):
        ''' Outputs the subjects to take out and put in your bag. '''
        await send_command_embed(
            ctx, bag.build_string(bag.get_out_in(bag.get_data())))

    @command(hidden=True)
    @del_invoc
    async def reload_config(self, ctx):
        await self.bot.reload_config()


def setup(bot):
    bot.add_cog(Commands(bot))

    async def on_ready():
        Emojis.reload(bot)

    bot.add_listener(on_ready)
