from discord.ext.commands import Bot, command
from discord import File, Message, Embed, Color
from time import sleep
from traceback import format_exc

from config import Config
from logger import Logger

# command modules
from command_modules.get_subjects import get_subjects
from command_modules.suplovani import suplovani
from simpleeval import simple_eval
import yaml


async def send_channel_history(ctx, channel_name, no_history):
    ''' Send all channel history to the current context. '''
    for channel in ctx.bot.get_all_channels():
        if channel.name == channel_name:
            target_channel = channel
            break
    else:
        await ctx.send(f':warning: Channel `{ch_name}` not found :warning:')

    msgs = [msg async for msg in target_channel.history()]
    if msgs:
        for msg in msgs:
            if msg.content:
                await ctx.send(msg.content)
            for embed in msg.embeds:
                await ctx.send(embed=embed)
    else:
        await ctx.send(no_history)


class Commands:
    def __init__(self, bot):
        self.bot = bot

    @command()
    async def repeat(self, ctx, string: str, n: int = 10):
        '''
        Repeats the given string.
        
        Repeats the given string \ emote n times.:
        '''

        n = min(n, 50)
        await ctx.send(string * n)

    @command()
    async def rozvrh(self, ctx):
        '''
        Send an image of our timetable.
        '''

        await ctx.send(file=File('res/rozvrh.png'))

    @command()
    async def subj(self, ctx):
        '''
        Gives the subjects to prepare for.

        Gives the subjects to prepare for dependently on the current time.
        If it's already after the lunch, gives the subjects of the following
        day, otherwise gives the subjects for the current day. The subjects
        are given in an alphabetical order.
        '''

        await ctx.send(f'```fix\n{get_subjects()}```')

    @command()
    async def eval(self, ctx, *, expression):
        '''
        Evaluates a python expression.

        Evaluates a python expression. If the evaluation fails,
        outputs the error code. It is not possible to access variables
        or functions. Example: 25**(1/2) -> 5.0
        '''

        try:
            ret = simple_eval(expression)
        except Exception:
            ret = (':warning: Failed to evaluate :warning:'
                   f'```python\n{format_exc()}```')
        await ctx.send(f'<@{ctx.author.id}> {ret}')

    @command()
    async def test(self, ctx):
        ''' Outputs exams from the *testy* channel. '''
        await send_channel_history(ctx, 'testy', '**O žádném testu se neví.**')

    @command()
    async def ukol(self, ctx):
        ''' Outputs homeworks from the *úkoly* channel. '''
        await send_channel_history(ctx, 'úkoly', '**O žádném úkolu se neví.**')

    @command()
    async def supl(self, ctx, target='3.F'):
        '''
        Outputs the substitutions.
        
        The substitutions are pulled from moodle3.gvid.cz using selenium,
        logging in with username and password from the config file and clicking
        the last pdf link. Then transformed to text using tabula-py. If you
        want to output all substitutions instead of only the targetted ones,
        type 'all' as the target argument.
        '''

        # TODO expire downloaded pdf
        await ctx.trigger_typing()
        await ctx.send(
            suplovani(target, Config.username, Config.password,
                      Config.chromedriver))

    @command()
    async def log(self, ctx):
        '''
        Return the current log.

        Return the current log consisting of sys.stdout and sys.stderr.
        '''

        await ctx.send(f'```python\n{Logger.get_log()[-1980:]}```')

    @command()
    async def embed(self, ctx, *, yaml_: str):
        '''
        Produces a discord embed.

        This command takes only one argument. This argument is a string
        formatted as yaml. The yaml can look like the following. The command
        deletes the message afterwards.

        --------------------------------------------------
        channel: bot-testing
        title: title
        url: https://example.com
        description: description
        fields: [
        {name: 'field 1 name', value: 'field 1 value'},
        {name: 'field 2 name', value: 'field 2 value'}
        ]
        footer: footer
        color: green
        --------------------------------------------------

        If channel in omitted, the embed will be sent to the channel the
        command was invoked from.

        The supported colors are:
         - default
         - teal
         - dark_teal
         - green
         - dark_green
         - blue
         - dark_blue
         - purple
         - dark_purple
         - magenta
         - dark_magenta
         - gold
         - dark_gold
         - orange
         - dark_orange
         - red
         - dark_red
         - lighter_grey
         - dark_grey
         - light_grey
         - darker_grey
         - blurple
         - greyple
        '''

        # fix string
        yaml_ = yaml_.replace('`yaml', '')
        yaml_ = yaml_.replace('`', '')

        data = yaml.load(yaml_)
        channel_name = data.pop('channel', None)

        for channel in self.bot.get_all_channels():
            if channel.name == channel_name:
                break
        else:
            channel = ctx

        # get things from yaml
        fields = data.pop('fields', ())
        footer_text = data.pop('footer', '')
        color = data.pop('color', '')
        color = getattr(Color, color, Color.orange)()

        # create embed
        embed = Embed(**data)

        # set color
        embed.color = color

        # add fields
        for field in fields:
            embed.add_field(
                name=field.get('name', '...'), value=field.get('value', '...'))

        # set footer
        if footer_text:
            embed.set_footer(text=footer_text)

        await channel.send(embed=embed)
        await ctx.message.delete()

    @command()
    async def emoji(self, ctx):
        ''' List all customly added emojis. '''
        s = ''
        for emoji in ctx.guild.emojis:
            s += f'<:{emoji.name}:{emoji.id}>'
        await ctx.send(s)


def setup(bot):
    bot.add_cog(Commands(bot))