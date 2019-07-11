from calendar import day_abbr
from random import randint, random

from discord import Embed
from discord.ext.commands import Context, Cog, command
from simpleeval import simple_eval

import utils
from client import FreefClient
from decorators import del_invoc
from emojis import Emojis
from logger import Logger
from remote_config import EXAM_CHANNEL_ID, HOMEWORK_CHANNEL_ID, TIMETABLE_URL, TIMETABLE


async def reply_command(ctx: Context, send=True, include_invoc=True, include_author=True, **kw) -> Embed:
    """
    Send the command output in the context channel, include the invocation
    message and the author. Return the built embed.

    :param ctx: The command context.
    :param send: Whether to send the command or return the embed only.
    :param include_invoc: Whether to include the invocation message in the
        embed description.
    :param include_author: Whether to include the author name in the embed.
    :param kw: The additional kwargs to build the embed from.
    :return: An embed representing a command reply.
    """

    embed = Embed.from_dict(kw)

    # Add the invocation message
    if include_invoc:
        embed.description = embed.description or ''  # Ensure string
        embed.description += '\n' if embed.description.endswith('```') else '\n\n'  # Somewhat nicer formatting
        embed.description += f'`{ctx.message.clean_content}`'  # Append the invoc message

    # Add the author
    if include_author:
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)

    # Send the embed
    if send:
        await ctx.send(embed=embed)

    return embed


class Commands(Cog):
    bot: FreefClient

    def __init__(self, bot):
        self.bot = bot

    @command()
    @del_invoc
    async def repeat(self, ctx, string: str, n: int = 10):
        """ Repeat the given message n times. Maximum is 50. """
        await reply_command(ctx, include_invoc=False, description=string * min(n, 50))

    @command(aliases=['table', 'rozvrh'])
    @del_invoc
    async def timetable(self, ctx):
        """ Send an image of our timetable. """
        await reply_command(ctx, image={'url': ctx.bot[TIMETABLE_URL] or 'https://example.com'})

    @command()
    @del_invoc
    async def subj(self, ctx):
        """
        Gives the subjects to prepare for.

        If it's already after the lunch, gives the subjects of the following
        day, otherwise gives the subjects for the current day. The subjects
        are given in an alphabetical order.
        """

        day_index = utils.Datetime.shifted_weekday()

        subjs = self.bot[TIMETABLE][day_index]  # Get day subjs
        subjs = set(subjs) - set('-')  # Remove spare time
        subjs = sorted(list(subjs))  # Sort alphabetically

        prefix = day_abbr[day_index]

        string = f'**{prefix}:** {", ".join(subjs)}'

        await reply_command(ctx, description=string)

    @command()
    @del_invoc
    async def bag(self, ctx, day_index=None):
        """
        Tell me which subjects to put in my bag and take out of my bag
        for the next school day.

        If `day_index` is given (0 for monday), the output will be given for
        that day.
        """

        omit = set('-')

        day_index = day_index or utils.Datetime.shifted_weekday()
        day_index = min(int(day_index), 5) % 5  # do not include weekend

        timetable = self.bot[TIMETABLE][:5]  # do not include weekend

        passed_subjs = set(timetable[day_index - 1]) - omit
        pending_subjs = set(timetable[day_index]) - omit

        out_subjs = passed_subjs - pending_subjs  # take out of the bag
        in_subjs = pending_subjs - passed_subjs  # put in the bag

        out_subjs = sorted(list(out_subjs))  # sort alphabetically
        in_subjs = sorted(list(in_subjs))

        string = f'**Out:** {", ".join(out_subjs)}\n**In:** {", ".join(in_subjs)}'

        await reply_command(ctx, description=string)

    @command()
    @del_invoc
    async def eval(self, ctx, *, expression):
        """
        Evaluates a python expression.

        Evaluates a python expression. If the evaluation fails,
        outputs the error code. It is not possible to access variables
        or functions. Example: 25**(1/2) -> 5.0
        """

        try:
            ret = f'```python\n{simple_eval(expression)}```'
        except Exception as ex:
            ret = f':warning: **Failed to evaluate** :warning:\n```{ex}```'

        await reply_command(ctx, description=ret)

    @command(aliases=['ex', 'test', 'testy'])
    @del_invoc
    async def exam(self, ctx):
        """ Output pending exams. """
        await reply_command(ctx,
                            **(await utils.EmbedUtils.channel_summary(
                                ctx.bot.get_channel(ctx.bot[EXAM_CHANNEL_ID]))).to_dict())

    # noinspection SpellCheckingInspection
    @command(aliases=['hw', 'ukol', 'ukoly'])
    @del_invoc
    async def homework(self, ctx):
        """ Output pending homeworks. """
        await reply_command(ctx,
                            **(await utils.EmbedUtils.channel_summary(
                                ctx.bot.get_channel(ctx.bot[HOMEWORK_CHANNEL_ID]))).to_dict())

    @command()
    @del_invoc
    async def log(self, ctx):
        """
        Return the current log.

        Return the current log consisting of sys.stdout and sys.stderr.
        """

        await reply_command(ctx, description=f'```{Logger.get_log()[-1980:]}```')
        Logger.info(f'Command: Sent logs to `{ctx.channel.name}` channel')

    @command()
    @del_invoc
    async def random(self, ctx, arg1: int = None, arg2: int = None):
        """
        Gives a random number depending on the arguments.

        Up to two arguments can be passed into this function. If both arguments
        are omitted, the given number will be in a range from 0 to 1. If one
        argument is given, the given number will be in a range from 0 to arg1.
        If both arguments are given, the given number will be in a range from
        arg1 to arg2.
        """

        if arg1 and arg2:
            res = randint(*sorted((arg1, arg2)))
        elif arg1:
            res = randint(0, arg1)
        else:
            res = random()

        await reply_command(ctx, description=f'```python\n{res}```')

    # noinspection PyUnusedLocal
    @command(hidden=True)
    @del_invoc
    async def toggle_oos(self, ctx):
        """ Toggle out of service. """
        await self.bot.toggle_oos()

    # noinspection PyUnusedLocal
    @command(hidden=True)
    @del_invoc
    async def reload_config(self, ctx):
        await self.bot.reload_config()


def setup(bot):
    bot.add_cog(Commands(bot))

    async def on_ready():
        Emojis.reload(bot)

    bot.add_listener(on_ready)
