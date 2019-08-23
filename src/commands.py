import logging
from calendar import day_abbr
from random import randint, random
from typing import Optional

from discord import NotFound
from discord.ext.commands import Context, Cog, command, has_role
from simpleeval import simple_eval

import common
import utils
from client import FreefClient
from command_output import CommandOutput
from decorators import del_invoc
from remote_config import EXAM_CHANNEL_ID, HOMEWORK_CHANNEL_ID, TIMETABLE_URL
from timeout_message import TimeoutMessage
from timetable import Timetable

logger = logging.getLogger('Commands')


class Commands(Cog, name='General'):
    bot: FreefClient

    def __init__(self, bot):
        self.bot = bot

    @command()
    @del_invoc
    async def repeat(self, ctx, string: str, n: int = 10):
        """
        Repeat the given message `n` times.

        The output will be stripped down to `2000` characters. The last string repeated
        will never be broken up. You can think of it as an integer division.
        """

        n_fit = min(2000 // len(string), n)
        await CommandOutput(ctx, invoc=False, description=string * n_fit).send(register=False)

    @command(aliases=['table', 'rozvrh'])
    @del_invoc
    async def timetable(self, ctx):
        """ Send an image of our timetable. """
        await CommandOutput(ctx, image={'url': ctx.bot[TIMETABLE_URL] or 'https://example.com'}).send()

    @command()
    @del_invoc
    async def subj(self, ctx, day_index: int = None):
        """
        Gives the subjects to prepare for.

        If it's already after the lunch, gives the subjects of the following
        day, otherwise gives the subjects for the current day. The subjects
        are given in an alphabetical order.

        If `day_index` is given (`0` for monday), the output will be given for
        that day.
        """

        if day_index is None:
            day_index = utils.Datetime.shifted_weekday()

        day = Timetable[day_index]
        subjs = set(day.without_dupes)
        names = list(map(lambda x: x.name, subjs))

        prefix = day_abbr[day_index]

        string = f'**{prefix}:**' + '\n'.join([''] + names)

        await CommandOutput(ctx, description=string).send()

    @command()
    @del_invoc
    async def bag(self, ctx, day_index: int = None):
        """
        Tell me which subjects to put in my bag and take out of my bag
        for the next school day.

        If `day_index` is given (`0` for monday), the output will be given for
        that day.
        """

        if day_index is None:
            day_index = utils.Datetime.shifted_weekday()
        day_index = min(day_index, 5) % 5  # Omit weekend

        days = Timetable.days[:5]  # Omit weekend

        passed_day = days[day_index - 1].without_dupes
        pending_day = days[day_index].without_dupes

        # Subtract
        out_subjs = [i for i in passed_day.subjs if i not in pending_day.subjs]
        in_subjs = [i for i in pending_day.subjs if i not in passed_day.subjs]

        # Build string
        string = '**Out:**\n'
        string += '\n'.join(map(lambda x: x.name, out_subjs))
        string += '\n\n**In:**\n'
        string += '\n'.join(map(lambda x: x.name, in_subjs))

        await CommandOutput(ctx, description=string).send()

    @command()
    @del_invoc
    async def eval(self, ctx, *, expression):
        """
        Evaluates a python expression.

        Evaluates a python expression. If the evaluation fails,
        output the exception traceback. Uses safe eval. Example: `25**(1/2)` -> `5.0`
        """

        try:
            ret = f'```python\n{simple_eval(expression)}```'
        except Exception as ex:
            ret = f':warning: **Failed to evaluate** :warning:\n```{ex}```'

        await CommandOutput(ctx, description=ret).send()

    @command(aliases=['ex', 'test', 'testy'])
    @del_invoc
    async def exam(self, ctx):
        """ Output pending exams. """
        channel = ctx.bot.get_channel(ctx.bot[EXAM_CHANNEL_ID])
        embed = await utils.EmbedUtils.channel_summary(channel)
        await CommandOutput(ctx, **embed.to_dict()).send()

    # noinspection SpellCheckingInspection
    @command(aliases=['hw', 'ukol', 'ukoly'])
    @del_invoc
    async def homework(self, ctx):
        """ Output pending homeworks. """
        channel = ctx.bot.get_channel(ctx.bot[HOMEWORK_CHANNEL_ID])
        embed = await utils.EmbedUtils.channel_summary(channel)
        await CommandOutput(ctx, **embed.to_dict()).send()

    @command(hidden=True)
    @del_invoc
    async def log(self, ctx):
        """
        Return the current log.
        """

        log = logging.getLogger().handlers[1].stream.getvalue()
        log = log[-2000:]
        log = f'```{log}```'

        await CommandOutput(ctx, description=log).send()
        logger.info(f'Sent logs to `{ctx.channel.name}` channel')

    @command()
    @del_invoc
    async def random(self, ctx, arg1: Optional[int] = None, arg2: Optional[int] = None):
        """
        Gives a random number depending on the arguments.

        Up to two arguments can be passed into this function. If both arguments
        are omitted, the given number will be in range `0` to `1`. If one
        argument is given, the given number will be in range `0` to `arg1`.
        If both arguments are given, the given number will be in range `arg1` to `arg2`.
        """

        if arg1 and arg2:
            res = randint(*sorted((arg1, arg2)))
        elif arg1:
            res = randint(0, arg1)
        else:
            res = random()

        await CommandOutput(ctx, description=f'```python\n{res}```').send()

    # noinspection PyUnusedLocal
    @command(hidden=True)
    @del_invoc
    async def reload_config(self, ctx):
        await self.bot.reload_config()

    @command(hidden=True, aliases=['del'])
    @has_role('moderator')
    async def delete(self, ctx: Context, n: int = 1):
        """ Delete the last `n` messages. `1` by default. """
        # We need to delete the number of messages + the invocation message.
        n += 1
        deleted = []
        try:
            deleted = await ctx.channel.purge(limit=n)
        except NotFound:
            await TimeoutMessage(ctx).send(common.Embed.COMMAND_ERROR)

        # Tell the user if some messages could not be deleted
        if len(deleted) < n:
            await TimeoutMessage(ctx).send(embed=common.Embed.DELETE_MESSAGES_ERROR)


def setup(bot):
    bot.add_cog(Commands(bot))
