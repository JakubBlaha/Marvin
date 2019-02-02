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
from emojis import Emojis
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


class Break(Exception):
    pass


class Commands:
    def __init__(self, bot):
        self.bot = bot

    @command()
    async def repeat(self, ctx, string: str, n: int = 10):
        '''
        Repeats the given string.
        
        Repeats the given string\emote n times. Maximum is 50.
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
        description: description
        fields: {
            name1: value1,
            name2: value2
        }
        footer: footer
        color: green
        --------------------------------------------------

        If channel in omitted, the embed will be sent to the channel the
        command was invoked from.

        If there is an embed with the same title in the given channel, then the
        embed will be edited instead of creating a new one. If fields are
        given, then the fields will be added to the existing ones rather then
        replacing the existing ones. Optionally remove_fields list of indexes
        can be passed in in order to delete fields at the matching indexes.

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

        try:
            data = yaml.load(yaml_)
        except Exception:
            Logger.error(f'Command: Failed to read {yaml_}')
            await ctx.send(f'```python\n{format_exc()[-1980:]}```')
            return

        # get the channel
        channel_name = data.pop('channel', None)
        for channel in self.bot.get_all_channels():
            if channel.name == channel_name:
                break
        else:
            channel = ctx.channel

        # get things from yaml
        title = data.get('title')

        fields = data.pop('fields', {})
        remove_fields = data.pop('remove_fields', ())
        footer_text = data.pop('footer', '')
        color = getattr(Color, data.pop('color', ''), Color.orange)()

        # get embed
        try:
            async for msg in channel.history():
                for embed in msg.embeds:
                    if embed.title == title:
                        Logger.info(
                            f'Command: Found an embed with title {embed.title}'
                        )
                        raise Break
        except Break:
            for key, value in data.items():
                setattr(embed, key, value)

        else:
            msg = None
            embed = Embed(**data)

        # set color
        embed.color = color

        # clear fields
        for index in remove_fields:
            embed.remove_field(index)

        # add fields
        for name, value in fields.items():
            embed.add_field(name=name, value=value)

        # set footer
        if footer_text:
            embed.set_footer(text=footer_text)

        # send/edit message
        if msg:
            await msg.edit(embed=embed)
        else:
            await channel.send(embed=embed)

        # delete user message
        await ctx.message.delete()

    @command()
    async def emoji(self, ctx):
        ''' List all customly added emojis. '''
        names, ids = [], []
        for emoji in ctx.guild.emojis:
            names.append(emoji.name)
            ids.append(emoji.id)
        emojis = [(name, id_) for name, id_ in zip(names, ids)]

        Logger.info('Command: Listing emojis:\n' +
                    '\n'.join([f'{name}: {id_}' for name, id_ in emojis]))

        await ctx.send(''.join([f'<:{name}:{id_}>' for name, id_ in emojis]))

    @command()
    async def squid(self, ctx, n: int = 10):
        '''
        Send sequence of the squid emojis.
        
        Max length of the squid is 70.
        '''

        n = min(n, 70)

        await ctx.send(
            f'{Emojis.Squid1}{Emojis.Squid2 * (n - 3)}{Emojis.Squid3}'
            f'{Emojis.Squid4}')


def setup(bot):
    bot.add_cog(Commands(bot))