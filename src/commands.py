from discord.ext.commands import Bot, command, Cog
from discord import File, Message, Embed, Color, Client, utils, Guild
from time import sleep
from traceback import format_exc
from time import sleep
from asyncio import TimeoutError
from random import random, randint
import yaml
import re

from config import Config
from logger import Logger

# command modules
from command_modules.get_subjects import get_subjects
from command_modules.embed import is_embed_up_to_date
from command_modules.message_split import split as msg_split
from simpleeval import simple_eval
from emojis import Emojis
from command_modules import bag
from utils.get_datetime_from_string import get_datetime_from_string
from utils.embed_to_text import embed_to_text

DEFAULT_EMBED = {
    'title': '\u200b',
    'description': '\u200b',
    'footer': None,
    'fields': {},
    'del_fields': (),
    'color': Embed.Empty
}


async def send_channel_history(ctx,
                               channel_name,
                               no_history,
                               ignore_date=False):
    '''
    Send all channel history to the current context. Embeds with description of
    already outdated date will be skipped.
    '''
    target_channel = utils.get(ctx.guild.channels, name=channel_name)
    if not target_channel:
        await ctx.send(
            f':warning: Channel `{channel_name}` not found :warning:')

    msgs = [msg async for msg in target_channel.history()]

    # Tell if no msgs, return
    if not msgs:
        await ctx.send(no_history)
        return

    # Sort by date
    msgs.sort(key=lambda it: get_datetime_from_string(
        embed_to_text((it.embeds + [Embed()])[0]) + it.content),
              reverse=True)

    # Send them
    for msg in msgs:
        await ctx.send(msg.content,
                       embed=msg.embeds[0] if msg.embeds
                       and is_embed_up_to_date(msg.embeds[0]) else None)


async def request_input(ctx, message, regex='', mention=True, allowed=[]):
    # create regex from allowed
    if allowed and not regex:
        regex = f'({"|".join(allowed)}){{1}}'
    elif allowed and regex:
        Logger.warning(
            f'Input: Given `allowed` {allowed} but also `regex` {regex}')

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
        sleep(1)
        await user_msg.delete()

    await bot_message.delete()
    return user_msg.content


class Break(Exception):
    pass


class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot

    @command()
    async def repeat(self, ctx, string: str, n: int = 10):
        '''
        Repeats the given string.
        
        Repeats the given string\emote n times. Maximum is 50.
        '''

        e = Embed(description=string * min(n, 50))
        e.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        await ctx.send(embed=e)
        await ctx.message.delete()

    @command(aliases=['table', 'rozvrh'])
    async def timetable(self, ctx):
        '''Send an image of our timetable.'''
        e = Embed()
        e.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        e.set_image(url=Config.get('timetable_url', 'https://example.com'))

        await ctx.send(embed=e)
        await ctx.message.delete()

    @command()
    async def subj(self, ctx):
        '''
        Gives the subjects to prepare for.

        Gives the subjects to prepare for dependently on the current time.
        If it's already after the lunch, gives the subjects of the following
        day, otherwise gives the subjects for the current day. The subjects
        are given in an alphabetical order.
        '''

        e = Embed(description=f'```fix\n{get_subjects()}```')
        e.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        await ctx.send(embed=e)
        await ctx.message.delete()

    @command()
    async def eval(self, ctx, *, expression):
        '''
        Evaluates a python expression.

        Evaluates a python expression. If the evaluation fails,
        outputs the error code. It is not possible to access variables
        or functions. Example: 25**(1/2) -> 5.0
        '''

        try:
            ret = f'```{simple_eval(expression)}```'
        except Exception as ex:
            ret = f':warning: **Failed to evaluate** :warning:\n```{ex}```'

        e = Embed(title=ret, description=f'`{expression}`')
        e.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        await ctx.send(embed=e)
        await ctx.message.delete()

    @command(aliases=['testy'])
    async def test(self, ctx):
        ''' Outputs exams from the *testy* channel. '''
        await send_channel_history(ctx, 'testy', '**O žádném testu se neví.**')

    @command(aliases=['ukoly'])
    async def ukol(self, ctx):
        ''' Outputs homeworks from the *úkoly* channel. '''
        await send_channel_history(ctx, 'úkoly', '**O žádném úkolu se neví.**')

    @command()
    async def log(self, ctx):
        '''
        Return the current log.

        Return the current log consisting of sys.stdout and sys.stderr.
        '''

        e = Embed(description=f'```python\n{Logger.get_log()[-1980:]}```')
        e.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        await ctx.send(embed=e)
        await ctx.message.delete()
        Logger.info(f'Command: Sent logs to `{ctx.channel.name}` channel')

    @command()
    async def embed(self, ctx, *, yaml_: str):
        '''
        Produces a discord embed.

        This command takes only one argument. This argument is a string
        formatted as yaml. The yaml can look like the following. The command
        deletes the message afterwards.

        --------------------------------------------------
        title: title
        description: description
        fields: {
            name1: value1,
            name2: value2
        }
        del_fields: [0, 1]
        footer: footer
        color: green
        --------------------------------------------------

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

        try:
            new_data = yaml.load(yaml_)
        except Exception:
            Logger.error(f'Command: Failed to read {yaml_}')
            await ctx.send(f'```python\n{format_exc()[-1980:]}```')
            return

        # search for an embed in the history
        msg = None
        old_data = {}
        async for _msg in ctx.channel.history():
            if not _msg.embeds:
                continue
            embed = _msg.embeds[0]
            if embed.title == new_data.get('title', None):
                Logger.info(
                    f'Command: Found an embed with title {embed.title}')
                old_data = embed.to_dict()
                msg = _msg
                break

        # combine fields
        _fields = old_data.get('fields', [])
        _fields = [
            field for index, field in enumerate(_fields)
            if not index in new_data.get('del_fields', [])
        ]
        _fields += [{
            'inline': False,
            'name': name,
            'value': value
        } for name, value in new_data.get('fields', {}).items()]

        # fix color data
        if isinstance(new_data.get('color', None), str):
            try:
                new_data['color'] = getattr(Color, new_data['color'])()
            except AttributeError:
                new_data['color'] = Color.lighter_grey()
        if 'color' in new_data:
            new_data['color'] = new_data['color'].value

        # Fix footer data
        if 'footer' in new_data and not isinstance(new_data['footer'], dict):
            new_data['footer'] = {'text': str(new_data['footer'])}

        # create an embed
        embed = Embed.from_dict({**old_data, **new_data, 'fields': _fields})

        # send/edit message
        if msg:
            await msg.edit(embed=embed)
        else:
            await ctx.channel.send(embed=embed)

        # delete user message
        await ctx.message.delete()

    @command()
    async def spira_embed(self, ctx):
        '''
        An idiot-proof embed builder...
        '''
        await ctx.message.delete()

        title = await request_input(ctx, 'Please specify the `title`:')
        description = await request_input(ctx,
                                          'Please specify the `description`:')

        color = await request_input(ctx,
                                    f'Please specify the `color`:',
                                    allowed=['red', 'orange', 'green'])

        fields = {}
        TERMINATOR = '👌'
        while True:
            field_name = await request_input(
                ctx, f'Please specify a `field name`.\nType {TERMINATOR}'
                'when finished.')

            if field_name.strip() == TERMINATOR:
                break

            field_value = await request_input(
                ctx, f'Please specify the `{field_name}` value:')

            if field_value.strip() == '...':
                field_value = '\u200b'

            fields[field_name] = field_value

        embed = Embed(title=title,
                      description=description,
                      color=getattr(Color, color)())
        for key, value in fields.items():
            embed.add_field(name=key, value=value)

        # Set the author
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        await ctx.send(embed=embed)

    @command()
    async def emoji(self, ctx):
        ''' List all customly added emojis. '''
        e = Embed(description=''.join(map(str, ctx.guild.emojis)))
        e.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        await ctx.send(embed=e)
        await ctx.message.delete()

    @command(aliases=['anim_squido', 'anime_squido', 'anime_squid'])
    async def anim_squid(self, ctx):
        '''
        Posts an animated squid made of custom emojis.
        '''

        LEN = 8
        msg = await ctx.send('...')
        for i in (*range(LEN + 1), *range(LEN - 1, -1, -1)):
            await msg.edit(
                content=f'{Emojis.Squid1}{Emojis.Squid2 * i}{Emojis.Squid3}'
                f'{Emojis.Squid2 * (LEN - i)}{Emojis.Squid4}')
            sleep(.1)

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

        await ctx.send(f'{ctx.author.mention} {res}')

    @command(hidden=True)
    async def toggle_oos(self, ctx):
        ''' Toggle out of service. '''
        await self.bot.toggle_oos()

    @command()
    async def bag(self, ctx):
        ''' Outputs the subjects to take out and put in your bag. '''
        await ctx.send(bag.build_string(bag.get_out_in(bag.get_data())))


def setup(bot):
    bot.add_cog(Commands(bot))

    async def on_ready():
        Emojis.reload(bot)

    bot.add_listener(on_ready)
